# Deterministic Market-Data Warehouse: Engineering Walkthrough

## Elevator Summary
This project implements a reproducible, single-node market-data warehouse. We transitioned from destructive data filtering to a deterministic trust-annotation strategy, processing raw vendor feeds into queryable parquet datasets using DuckDB and tracking pipeline execution via MLflow. The core engineering outcome was learning to preserve operational state through annotation rather than aggressively dropping data that violated naive assumptions.

## End-to-End Pipeline Walkthrough
1. **Ingestion**: Raw vendor feeds are loaded into memory.
2. **Deterministic Ordering**: Data is sorted by canonical timestamps and symbols to ensure idempotency.
3. **Profiling & Validation**: Rows are evaluated against expected invariants. We annotate semantically ambiguous records and quarantine strict structural corruption.
4. **Storage**: Validated and annotated records are written to a partitioned DuckDB/parquet layer.
5. **Observation**: Run metadata, parameters, and benchmark latencies are tracked via MLflow.

## Why Profiling Happened Before Validation
We initially assumed we could write validation rules based on standard financial engineering definitions. Profiling showed widespread systematic anomalies that contradicted these definitions. Therefore we changed policy to build a profiler first, preventing us from writing destructive validation rules based on incorrect assumptions.

## Validation Philosophy Evolution
*This is the central narrative of the engineering approach.*

**Initial assumption:** 
We initially assumed OHLC (Open, High, Low, Close) violations implied structural data corruption that must be discarded.

**Observed reality:** 
Profiling showed widespread systematic anomalies, unrealistic quarantine rates, vendor snapshot semantics, and pre-open indicative behavior that frequently violated these strict theoretical rules.

**Engineering reassessment:** 
We recognized that strict invariants were incompatible with observed feed behavior. Dropping these rows would destroy valuable market microstructure signal.

**Final decision:** 
We changed policy to preserve semantically uncertain rows. We annotate ambiguity and quarantine only low-ambiguity structural corruption.

### Selective Quarantine Strategy
Instead of destructive filtering, the pipeline employs a specific annotation taxonomy:
- `PREOPEN_INDICATIVE`: Captures valid pre-market auction data that lacks volume.
- `OHLC_ANOMALY`: Flags logical pricing violations without destroying the row.
- `DUPLICATE_OPTIONS_SNAPSHOT`: Identifies redundant snapshot records inherent to the vendor feed.
- `REORDERED_TIMESTAMPS`: Flags out-of-sequence delivery from the vendor.

By adopting this strategy, we quarantined **only 6 quarantined rows** of actual structural corruption, while successfully preserving **24k+ annotated rows** for downstream quantitative analysis.

## Deterministic Warehouse Design

### Why DuckDB + Parquet
DuckDB over parquet provides an ergonomic, high-performance local SQL engine. It remains suitable for reproducible interview-scale analytics workloads where inspectability matters more than orchestration complexity. It avoids the overhead of managing a persistent database daemon.

### Access Layer & Consumer Contracts
Consumers interface with the data through a deterministic Python query layer, rather than raw SQL. This ensures consistent read patterns and isolates the underlying storage schema from downstream access.

### MLflow & Reproducibility
MLflow binds pipeline executions to benchmark artifacts. It provides deterministic regression tracking without introducing distributed logging overhead, making the entire build process observable.

## Benchmark Interpretation
- Benchmark latencies clustered tightly across all query patterns.
- Fixed local DuckDB/parquet overhead dominated execution time.
- The dataset scale was too small for selectivity differences to dominate.
- Higher p99 spikes likely reflect transient filesystem caching variance, Python runtime overhead, and broader parquet scan initialization rather than materially different dataset-selectivity characteristics.
- These benchmarks characterize warm-process local analytics behavior only.

## Limitations & Failure Modes

### What Would Break At Larger Scale
The current single-node, in-memory pipeline works for this dataset but will hit out-of-memory errors on larger histories. The monolithic sequential sorting step becomes a primary bottleneck if data exceeds available RAM.

### Future Improvements
- Move validation logic down into DuckDB SQL or dbt for out-of-core processing.
- Implement incremental ingestion rather than full-dataset rebuilds.
- Expand the annotation taxonomy to capture deeper cross-asset pricing invariants.

