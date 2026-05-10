from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

CURATED_ROOT = Path("data/warehouse/curated")
QUARANTINE_ROOT = Path("data/quarantine")
MANIFEST_PATH = Path("data/warehouse/manifest.json")
VALIDATION_SUMMARY_PATH = Path("data/validation_reports/validation_summary.json")
BENCHMARK_SUMMARY_PATH = Path("data/validation_reports/benchmark_summary.json")
BENCHMARK_CSV_PATH = Path("data/validation_reports/benchmark.csv")


def build_manifest() -> dict[str, Any]:
    curated_dataset_paths = _collect_dataset_paths(CURATED_ROOT)
    quarantine_dataset_paths = _collect_dataset_paths(QUARANTINE_ROOT)
    dataset_row_counts = _collect_row_counts(curated_dataset_paths)

    version_payload = {
        "dataset_names": sorted(dataset_row_counts),
        "dataset_row_counts": dataset_row_counts,
        "curated_dataset_paths": curated_dataset_paths,
        "quarantine_dataset_paths": quarantine_dataset_paths,
    }
    warehouse_version = hashlib.sha256(
        json.dumps(version_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    manifest = {
        "warehouse_version": warehouse_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_row_counts": dataset_row_counts,
        "curated_dataset_paths": curated_dataset_paths,
        "quarantine_dataset_paths": quarantine_dataset_paths,
        "validation_summary_path": str(VALIDATION_SUMMARY_PATH),
        "benchmark_summary_path": str(BENCHMARK_SUMMARY_PATH),
        "benchmark_csv_path": str(BENCHMARK_CSV_PATH),
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _collect_dataset_paths(root: Path) -> dict[str, list[str]]:
    dataset_paths: dict[str, list[str]] = {}
    if not root.exists():
        return dataset_paths

    for file_path in sorted(root.rglob("*.parquet"), key=lambda path: str(path)):
        relative_parts = file_path.relative_to(root).parts
        if not relative_parts:
            continue
        dataset = relative_parts[0]
        dataset_paths.setdefault(dataset, []).append(str(file_path))
    return dict(sorted(dataset_paths.items()))


def _collect_row_counts(dataset_paths: dict[str, list[str]]) -> dict[str, int]:
    row_counts: dict[str, int] = {}
    for dataset, paths in dataset_paths.items():
        row_counts[dataset] = sum(pl.read_parquet(path).height for path in paths)
    return dict(sorted(row_counts.items()))
