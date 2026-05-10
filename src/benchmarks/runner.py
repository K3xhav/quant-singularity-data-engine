from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable

from src.access.contracts import FuturesQuery, OptionsSnapshotQuery, SpotQuery, TimeRangeQuery
from src.access.queries import (
    get_futures_data,
    get_options_snapshot,
    get_range_bounds,
    get_spot_data,
    get_time_range,
)
from src.benchmarks.metrics import BenchmarkResult, measure_query
from src.utils.mlflow_utils import (
    log_json_artifact,
    log_markdown_artifact,
    log_metric_if_present,
)

BENCHMARK_ITERATIONS = 50
BENCHMARK_SUMMARY_PATH = Path("data/validation_reports/benchmark_summary.json")
BENCHMARK_CSV_PATH = Path("data/validation_reports/benchmark.csv")
BENCHMARK_REPORT_PATH = Path("reports/benchmark_report.md")


def run_benchmarks() -> list[BenchmarkResult]:
    benchmark_specs = _build_benchmark_specs()
    results: list[BenchmarkResult] = []

    for benchmark_name, query_fn in benchmark_specs:
        query_fn()
        result = measure_query(
            benchmark_name=benchmark_name,
            iterations=BENCHMARK_ITERATIONS,
            query_fn=query_fn,
        )
        results.append(result)

    write_benchmark_summary(results, BENCHMARK_SUMMARY_PATH)
    write_benchmark_csv(results, BENCHMARK_CSV_PATH)
    write_benchmark_report(results, BENCHMARK_REPORT_PATH)
    _log_benchmark_mlflow_metrics(results)

    for result in results:
        print(
            f"{result.benchmark_name}: "
            f"avg={result.avg_ms:.3f} ms, "
            f"p95={result.p95_ms:.3f} ms"
        )

    return results


def write_benchmark_summary(results: list[BenchmarkResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [result.model_dump(mode="json") for result in results]
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_benchmark_csv(results: list[BenchmarkResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "benchmark_name",
                "iterations",
                "avg_ms",
                "p50_ms",
                "p95_ms",
                "p99_ms",
                "min_ms",
                "max_ms",
            ]
        )
        for result in results:
            writer.writerow(
                [
                    result.benchmark_name,
                    result.iterations,
                    f"{result.avg_ms:.6f}",
                    f"{result.p50_ms:.6f}",
                    f"{result.p95_ms:.6f}",
                    f"{result.p99_ms:.6f}",
                    f"{result.min_ms:.6f}",
                    f"{result.max_ms:.6f}",
                ]
            )


def write_benchmark_report(results: list[BenchmarkResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Benchmark Report",
        "",
        "| Benchmark | Iterations | Avg (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Min (ms) | Max (ms) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for result in results:
        lines.append(
            "| "
            f"{result.benchmark_name} | "
            f"{result.iterations} | "
            f"{result.avg_ms:.3f} | "
            f"{result.p50_ms:.3f} | "
            f"{result.p95_ms:.3f} | "
            f"{result.p99_ms:.3f} | "
            f"{result.min_ms:.3f} | "
            f"{result.max_ms:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "- Fixed DuckDB/parquet startup and scan overhead dominates at this assignment dataset scale, so benchmark latencies remain relatively close across query patterns.",
            "- Options snapshots, point lookups, and VIX range reads all behave within a similar local warm-process latency band on the curated parquet warehouse.",
            "- These measurements characterize deterministic local analytics behavior only; they do not imply broader scalability claims.",
            "",
            "## Operational Observations",
            "- Benchmarks reflect warm-process local access patterns rather than external-service, concurrency, or distributed execution scenarios.",
            "- DuckDB over parquet remains suitable for reproducible interview-scale analytics workloads where inspectability matters more than orchestration complexity.",
            "- Stable query ordering, fixed iterations, and CSV/JSON/markdown outputs make the benchmark suite useful for deterministic regression tracking.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_benchmark_specs() -> list[tuple[str, Callable[[], object]]]:
    spot_query = SpotQuery(timestamp="2025-08-22 09:15:00")
    options_query = OptionsSnapshotQuery(
        timestamp="2025-08-27 09:00:00",
        strike=23500,
        side="CE",
    )
    futures_query = FuturesQuery(timestamp="2025-08-22 09:15:00")
    vix_start, vix_end = get_range_bounds("india_vix")
    range_query = TimeRangeQuery(
        start_timestamp=vix_start or "",
        end_timestamp=vix_end or "",
    )

    return [
        ("spot_point_lookup", lambda: get_spot_data(spot_query)),
        ("options_snapshot_lookup", lambda: get_options_snapshot(options_query)),
        ("futures_point_lookup", lambda: get_futures_data(futures_query)),
        ("vix_range_query", lambda: get_time_range("india_vix", range_query)),
    ]


def _log_benchmark_mlflow_metrics(results: list[BenchmarkResult]) -> None:
    for result in results:
        log_metric_if_present(f"{result.benchmark_name}_avg_ms", result.avg_ms)
        log_metric_if_present(f"{result.benchmark_name}_p95_ms", result.p95_ms)
        log_metric_if_present(f"{result.benchmark_name}_p99_ms", result.p99_ms)
    log_json_artifact(BENCHMARK_SUMMARY_PATH)
    log_markdown_artifact(BENCHMARK_REPORT_PATH)
