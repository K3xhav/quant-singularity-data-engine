from __future__ import annotations

from collections import Counter
from pathlib import Path

import polars as pl

from src.profiling.checks import run_all_checks
from src.profiling.models import ProfilingFinding, Severity
from src.profiling.reporting import write_findings_json, write_markdown_summary
from src.utils.mlflow_utils import (
    log_json_artifact,
    log_markdown_artifact,
    log_metric_if_present,
)

RAW_DATA_ROOT = Path("data/raw")
JSON_REPORT_PATH = Path("data/validation_reports/profiling_findings.json")
MARKDOWN_REPORT_PATH = Path("reports/profiling_summary.md")


def run_profiling() -> list[ProfilingFinding]:
    files = sorted(RAW_DATA_ROOT.rglob("*.csv"), key=lambda path: str(path))
    findings: list[ProfilingFinding] = []

    for csv_file in files:
        dataset = infer_dataset_name(csv_file, RAW_DATA_ROOT)
        try:
            frame = pl.read_csv(csv_file)
        except Exception as exc:
            findings.append(
                ProfilingFinding(
                    dataset=dataset,
                    file_name=csv_file.name,
                    severity=Severity.CRITICAL,
                    rule="file_read_error",
                    message=f"Failed to read CSV: {exc}",
                    affected_rows=0,
                    sample_rows=[],
                    timestamp=None,
                )
            )
            continue

        findings.extend(
            run_all_checks(
                df=frame,
                dataset=dataset,
                file_name=csv_file.name,
            )
        )

    sorted_findings = sort_findings(findings)
    write_findings_json(sorted_findings, JSON_REPORT_PATH)
    write_markdown_summary(sorted_findings, MARKDOWN_REPORT_PATH)
    _log_profiling_mlflow_metrics(sorted_findings)
    _print_console_summary(file_count=len(files), findings=sorted_findings)
    return sorted_findings


def infer_dataset_name(file_path: Path, raw_root: Path) -> str:
    relative_parts = file_path.relative_to(raw_root).parts
    if len(relative_parts) >= 2:
        parent_dataset = relative_parts[0]
        if parent_dataset == "aux":
            return file_path.stem
        return parent_dataset
    return file_path.parent.name or "unknown"


def sort_findings(findings: list[ProfilingFinding]) -> list[ProfilingFinding]:
    severity_rank = {
        Severity.CRITICAL: 0,
        Severity.WARNING: 1,
        Severity.INFO: 2,
    }
    return sorted(
        findings,
        key=lambda finding: (
            severity_rank[finding.severity],
            finding.dataset,
            finding.file_name,
            finding.rule,
            finding.timestamp or "",
            finding.message,
            finding.affected_rows,
        ),
    )


def _print_console_summary(file_count: int, findings: list[ProfilingFinding]) -> None:
    severity_counts = Counter(finding.severity.value for finding in findings)
    print(f"Processed CSV files: {file_count}")
    print(f"Total findings: {len(findings)}")
    for severity in Severity:
        print(f"{severity.value}: {severity_counts.get(severity.value, 0)}")
    print(f"JSON report: {JSON_REPORT_PATH}")
    print(f"Markdown report: {MARKDOWN_REPORT_PATH}")


def _log_profiling_mlflow_metrics(findings: list[ProfilingFinding]) -> None:
    severity_counts = Counter(finding.severity.value for finding in findings)
    log_metric_if_present("total_findings", len(findings))
    log_metric_if_present("critical_findings", severity_counts.get(Severity.CRITICAL.value, 0))
    log_metric_if_present("warning_findings", severity_counts.get(Severity.WARNING.value, 0))
    log_metric_if_present("info_findings", severity_counts.get(Severity.INFO.value, 0))
    log_json_artifact(JSON_REPORT_PATH)
    log_markdown_artifact(MARKDOWN_REPORT_PATH)
