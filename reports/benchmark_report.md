# Benchmark Report

| Benchmark | Iterations | Avg (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Min (ms) | Max (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| spot_point_lookup | 50 | 14.310 | 14.006 | 17.014 | 18.698 | 12.293 | 19.519 |
| options_snapshot_lookup | 50 | 16.550 | 16.413 | 18.798 | 19.865 | 14.070 | 20.793 |
| futures_point_lookup | 50 | 14.990 | 14.551 | 17.035 | 18.017 | 12.959 | 18.077 |
| vix_range_query | 50 | 14.919 | 14.674 | 16.661 | 20.032 | 12.741 | 22.250 |

## Interpretation
- Fixed DuckDB/parquet startup and scan overhead dominates at this assignment dataset scale, so benchmark latencies remain relatively close across query patterns.
- Options snapshots, point lookups, and VIX range reads all behave within a similar local warm-process latency band on the curated parquet warehouse.
- These measurements characterize deterministic local analytics behavior only; they do not imply broader scalability claims.

## Operational Observations
- Benchmarks reflect warm-process local access patterns rather than external-service, concurrency, or distributed execution scenarios.
- DuckDB over parquet remains suitable for reproducible interview-scale analytics workloads where inspectability matters more than orchestration complexity.
- Stable query ordering, fixed iterations, and CSV/JSON/markdown outputs make the benchmark suite useful for deterministic regression tracking.
