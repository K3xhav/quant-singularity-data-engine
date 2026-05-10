from __future__ import annotations

from statistics import fmean
from time import perf_counter
from typing import Callable

from pydantic import BaseModel


class BenchmarkResult(BaseModel):
    benchmark_name: str
    iterations: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float


def measure_query(
    benchmark_name: str,
    iterations: int,
    query_fn: Callable[[], object],
) -> BenchmarkResult:
    measurements_ms: list[float] = []
    for _ in range(iterations):
        start_time = perf_counter()
        query_fn()
        elapsed_ms = (perf_counter() - start_time) * 1000.0
        measurements_ms.append(elapsed_ms)

    return BenchmarkResult(
        benchmark_name=benchmark_name,
        iterations=iterations,
        avg_ms=fmean(measurements_ms),
        p50_ms=percentile(measurements_ms, 50.0),
        p95_ms=percentile(measurements_ms, 95.0),
        p99_ms=percentile(measurements_ms, 99.0),
        min_ms=min(measurements_ms),
        max_ms=max(measurements_ms),
    )


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        raise ValueError("Cannot compute percentile for empty values.")

    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (percentile_value / 100.0) * (len(sorted_values) - 1)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = rank - lower_index
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    return lower_value + (upper_value - lower_value) * weight
