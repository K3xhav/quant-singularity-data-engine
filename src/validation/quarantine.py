from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl

VALIDATION_STATUS_COLUMN = "validation_status"


def reset_output_root(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def write_curated_parquet(
    df: pl.DataFrame,
    output_root: Path,
    dataset: str,
    file_stem: str,
) -> Path:
    dataset_root = output_root / dataset
    dataset_root.mkdir(parents=True, exist_ok=True)
    output_path = dataset_root / f"{file_stem}.parquet"
    _write_parquet(df=df, output_path=output_path)
    return output_path


def write_quarantine_parquet(
    df: pl.DataFrame,
    output_root: Path,
    dataset: str,
    file_stem: str,
) -> list[Path]:
    if df.is_empty():
        return []

    output_paths: list[Path] = []
    statuses = sorted(
        status
        for status in df.get_column(VALIDATION_STATUS_COLUMN).drop_nulls().unique().to_list()
    )
    for status in statuses:
        partition_root = output_root / dataset / status
        partition_root.mkdir(parents=True, exist_ok=True)
        output_path = partition_root / f"{file_stem}.parquet"
        _write_parquet(
            df=df.filter(pl.col(VALIDATION_STATUS_COLUMN) == status),
            output_path=output_path,
        )
        output_paths.append(output_path)
    return output_paths


def summarize_quarantine_rows(frames: list[pl.DataFrame]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for frame in frames:
        if frame.is_empty():
            continue
        grouped = (
            frame.group_by(VALIDATION_STATUS_COLUMN)
            .len()
            .sort(VALIDATION_STATUS_COLUMN)
            .iter_rows(named=True)
        )
        for row in grouped:
            status = str(row[VALIDATION_STATUS_COLUMN])
            summary[status] = summary.get(status, 0) + int(row["len"])
    return dict(sorted(summary.items()))


def _write_parquet(df: pl.DataFrame, output_path: Path) -> None:
    sorted_df = _sort_for_output(df)
    sorted_df.write_parquet(output_path)


def _sort_for_output(df: pl.DataFrame) -> pl.DataFrame:
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
