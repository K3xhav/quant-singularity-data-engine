from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from src.profiling.runner import infer_dataset_name
from src.utils.mlflow_utils import log_json_artifact, log_metric_if_present
from src.validation.policies import (
    apply_ohlc_validation_policy,
    apply_options_duplicate_policy,
    apply_timestamp_reordering,
)
from src.validation.quarantine import (
    reset_output_root,
    summarize_quarantine_rows,
    write_curated_parquet,
    write_quarantine_parquet,
)

RAW_DATA_ROOT = Path("data/raw")
CURATED_ROOT = Path("data/warehouse/curated")
QUARANTINE_ROOT = Path("data/quarantine")
PROFILING_FINDINGS_PATH = Path("data/validation_reports/profiling_findings.json")
VALIDATION_SUMMARY_PATH = Path("data/validation_reports/validation_summary.json")
VALIDATION_STATUS_COLUMN = "validation_status"


def run_validation() -> dict[str, Any]:
    reset_output_root(CURATED_ROOT)
    reset_output_root(QUARANTINE_ROOT)
    VALIDATION_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    profiling_findings = _load_profiling_findings(PROFILING_FINDINGS_PATH)
    csv_files = sorted(RAW_DATA_ROOT.rglob("*.csv"), key=lambda path: str(path))

    rows_processed = 0
    rows_preserved = 0
    rows_annotated = 0
    rows_quarantined = 0
    dataset_summary: dict[str, dict[str, int]] = {}
    quarantine_frames: list[pl.DataFrame] = []
    preopen_indicative_rows = 0
    reordered_rows = 0
    ohlc_anomaly_rows = 0

    for csv_file in csv_files:
        dataset = infer_dataset_name(csv_file, RAW_DATA_ROOT)
        frame = pl.read_csv(csv_file)
        frame = _attach_lineage(df=frame, dataset=dataset, file_name=csv_file.name)

        rows_processed += frame.height
        curated_df, reordered_quarantine_df = apply_timestamp_reordering(frame, dataset)

        curated_df, duplicate_quarantine_df = apply_options_duplicate_policy(curated_df, dataset)
        curated_df, ohlc_quarantine_df = apply_ohlc_validation_policy(curated_df, dataset)

        quarantine_df = _concat_frames(
            [
                reordered_quarantine_df,
                duplicate_quarantine_df,
                ohlc_quarantine_df,
            ]
        )
        curated_df = _sort_curated_columns(curated_df)
        quarantine_df = _sort_curated_columns(quarantine_df)

        write_curated_parquet(
            df=curated_df,
            output_root=CURATED_ROOT,
            dataset=dataset,
            file_stem=csv_file.stem,
        )
        write_quarantine_parquet(
            df=quarantine_df,
            output_root=QUARANTINE_ROOT,
            dataset=dataset,
            file_stem=csv_file.stem,
        )

        rows_preserved += curated_df.height
        rows_annotated += _count_annotated_rows(curated_df)
        rows_quarantined += quarantine_df.height
        quarantine_frames.append(quarantine_df)
        preopen_indicative_rows += _count_rows_with_status(curated_df, "PREOPEN_INDICATIVE")
        reordered_rows += _count_rows_with_status(curated_df, "REORDERED_TIMESTAMPS")
        ohlc_anomaly_rows += _count_rows_with_status(curated_df, "OHLC_ANOMALY")
        dataset_summary[dataset] = {
            "rows_processed": dataset_summary.get(dataset, {}).get("rows_processed", 0) + frame.height,
            "rows_preserved": dataset_summary.get(dataset, {}).get("rows_preserved", 0) + curated_df.height,
            "rows_annotated": dataset_summary.get(dataset, {}).get("rows_annotated", 0)
            + _count_annotated_rows(curated_df),
            "rows_quarantined": dataset_summary.get(dataset, {}).get("rows_quarantined", 0) + quarantine_df.height,
        }

    quarantine_policy_counts = summarize_quarantine_rows(quarantine_frames)
    policy_counts = {
        "OHLC_ANOMALY": ohlc_anomaly_rows,
        "PREOPEN_INDICATIVE": preopen_indicative_rows,
        "REORDERED_TIMESTAMPS": reordered_rows,
        "DUPLICATE_OPTIONS_SNAPSHOT": quarantine_policy_counts.get("DUPLICATE_OPTIONS_SNAPSHOT", 0),
    }

    summary = {
        "annotated_rows": rows_annotated,
        "rows_processed": rows_processed,
        "rows_preserved": rows_preserved,
        "rows_quarantined": rows_quarantined,
        "policy_counts": policy_counts,
        "datasets": dict(sorted(dataset_summary.items())),
        "engineering_notes": [
            "Option-chain OHLC irregularities are treated as vendor-feed trust annotations rather than destructive corruption signals.",
            "Low-ambiguity structural duplicates remain quarantined while curated outputs preserve lineage and reproducibility.",
            "Deterministic curation preserves raw-file ordering intent through explicit reordering annotations and stable parquet outputs.",
        ],
        "profiling_rules_consumed": _summarize_profiling_rules(profiling_findings),
    }
    VALIDATION_SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _log_validation_mlflow_metrics(summary)

    print(f"Processed CSV files: {len(csv_files)}")
    print(f"Rows processed: {rows_processed}")
    print(f"Rows preserved: {rows_preserved}")
    print(f"Rows annotated: {rows_annotated}")
    print(f"Rows quarantined: {rows_quarantined}")
    print(f"Validation summary: {VALIDATION_SUMMARY_PATH}")
    return summary


def _attach_lineage(df: pl.DataFrame, dataset: str, file_name: str) -> pl.DataFrame:
    return (
        df.with_row_index("source_row_number")
        .with_columns(
            pl.lit(dataset).alias("source_dataset"),
            pl.lit(file_name).alias("source_file"),
            pl.lit(None, dtype=pl.Utf8).alias(VALIDATION_STATUS_COLUMN),
        )
    )


def _concat_frames(frames: list[pl.DataFrame]) -> pl.DataFrame:
    non_empty_frames = [frame for frame in frames if not frame.is_empty()]
    if not non_empty_frames:
        return frames[0].head(0)
    return pl.concat(non_empty_frames, how="vertical_relaxed")


def _sort_curated_columns(df: pl.DataFrame) -> pl.DataFrame:
    if df.is_empty():
        return df
    sort_columns = [
        column_name
        for column_name in (
            "timestamp",
            "date",
            "strike",
            "side",
            "source_row_number",
        )
        if column_name in df.columns
    ]
    if not sort_columns:
        return df
    return df.sort(sort_columns)


def _frame_contains_status(df: pl.DataFrame, status: str) -> bool:
    if df.is_empty() or VALIDATION_STATUS_COLUMN not in df.columns:
        return False
    return df.filter(
        pl.col(VALIDATION_STATUS_COLUMN).fill_null("").str.contains(status, literal=True)
    ).height > 0


def _count_annotated_rows(df: pl.DataFrame) -> int:
    if df.is_empty() or VALIDATION_STATUS_COLUMN not in df.columns:
        return 0
    return df.filter(pl.col(VALIDATION_STATUS_COLUMN).is_not_null()).height


def _count_rows_with_status(df: pl.DataFrame, status: str) -> int:
    if df.is_empty() or VALIDATION_STATUS_COLUMN not in df.columns:
        return 0
    return df.filter(
        pl.col(VALIDATION_STATUS_COLUMN).fill_null("").str.contains(status, literal=True)
    ).height


def _load_profiling_findings(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _count_profiling_rule(findings: list[dict[str, Any]], rule: str) -> int:
    return sum(1 for finding in findings if finding.get("rule") == rule)


def _summarize_profiling_rules(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        rule = str(finding.get("rule"))
        counts[rule] = counts.get(rule, 0) + 1
    return dict(sorted(counts.items()))


def _log_validation_mlflow_metrics(summary: dict[str, Any]) -> None:
    log_metric_if_present("rows_processed", summary.get("rows_processed"))
    log_metric_if_present("rows_preserved", summary.get("rows_preserved"))
    log_metric_if_present("rows_annotated", summary.get("annotated_rows"))
    log_metric_if_present("rows_quarantined", summary.get("rows_quarantined"))
    log_json_artifact(VALIDATION_SUMMARY_PATH)
