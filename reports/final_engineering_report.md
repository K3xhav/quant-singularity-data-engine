# Final Engineering Report: Deterministic Market-Data Warehouse

## Project Overview
This report details the architectural and semantic engineering of the deterministic market-data warehouse. The system is designed to ingest, validate, and serve historical options and equities data. The primary objective is to construct an operationally realistic repository that prioritizes data lineage, reproducibility, and the deterministic interpretation of vendor feeds over naive sanitization.

## Architecture Overview
The warehouse relies on deterministic local analytics workflows utilizing DuckDB-backed parquet access. Raw data is treated as an immutable raw zone. Transformed and validated layers are deterministically generated from this log to ensure stable query ordering. Compute is embedded to provide inspectable local execution and reproducible query behavior, reflecting an operationally cautious design.

## Profiling & Data Characterization
System engineering prioritized rigorous empirical profiling before validation-policy design. We operated on the principle that the validation logic must map to the empirical reality of the vendor feed, rather than idealized market mechanics. Aggressive validation initially quarantined a large percentage of option-chain rows, revealing that assumed OHLC invariants were incompatible with observed vendor-feed semantics.

Profiling revealed significant vendor-feed ambiguity. Many irregularities initially classified as syntactic errors were, upon deeper characterization, semantic anomalies reflecting upstream market state representations. The data exhibited behaviors indicative of vendor snapshot semantics rather than strict trade-bar semantics, demanding an operationally cautious interpretation of market-feed behavior.

## Validation Philosophy
The validation architecture implements deterministic curation semantics. 

Our initial assumption was that OHLC violations (e.g., Low > High, Close outside High/Low range) strictly implied data corruption. However, observed reality invalidated this premise:
- The system encountered widespread systematic violations of OHLC invariants.
- Strict enforcement of these invariants resulted in unrealistic quarantine rates.
- Profiling identified pre-open indicative vendor behavior and snapshotting artifacts that naturally produce these conditions.

Final decision: Preserve uncertain rows with annotations. 
Instead of destructive filtering, the system utilizes trust annotations. We apply a selective quarantine strategy, isolating only low-ambiguity structural anomalies. Ultimately, only 6 rows were quarantined, while 24k+ rows were preserved with annotations. This approach preserves lineage visibility and defers the decision of filtering to the query layer, empowering downstream consumers to specify their own tolerance for semantic ambiguity.

Systematic annotations include:
- `PREOPEN_INDICATIVE`
- `OHLC_ANOMALY`
- `DUPLICATE_OPTIONS_SNAPSHOT`
- `REORDERED_TIMESTAMPS`

## Warehouse & Access Design
The warehouse exposes data through curated parquet representations that explicitly include validation annotations. Curated outputs preserve deterministic ordering semantics to ensure stable downstream retrieval behavior across repeated pipeline executions. Consumers access the data via embedded DuckDB queries, filtering on annotation columns (e.g., `WHERE NOT OHLC_ANOMALY`) as their operational constraints dictate. This decouples the validation pipeline from access-pattern enforcement, maintaining deterministic outputs and reproducible query behavior.

## Benchmarking
Benchmarking focused on query latency against the local Parquet storage layer.
- Benchmark differences remained small across query classes.
- Fixed local DuckDB/parquet overhead dominated at assignment scale.
- Benchmarks characterize warm-process local analytics behavior only.

Observed latency distributions suggest that fixed local execution overhead dominated query cost more than dataset selectivity at the provided assignment scale. Scaling strategies are explicitly out of scope for the current design iteration, maintaining our focus on deterministic local execution.

## MLflow & Reproducibility
Reproducibility-first engineering is enforced via MLflow. MLflow is utilized to ensure deterministic run tracking, validation artifact logging, and reproducible warehouse metadata. This benchmark traceability guarantees that any analytical output can be reproducibly reconstructed from the immutable raw zone given the historical pipeline parameters.

## Limitations & Future Improvements
- **Storage Constraints**: The architecture characterizes deterministic local analytics workflows; distributed execution is unsupported.
- **Semantic Coverage**: While the current annotation taxonomy captures major structural anomalies, further profiling is required to categorize sparse, asset-specific vendor artifacts.
- **Future Improvements**: Enhancing the granularity of trust annotations and further stabilizing reproducible query behavior across edge cases.

## Conclusion
The engineering of this warehouse demonstrates that operationally realistic market-data systems must prioritize observation over assumption. By shifting from destructive filtering to trust annotations, the architecture accommodates vendor-feed ambiguity and widespread systematic violations without sacrificing deterministic outputs or lineage preservation. The resulting system provides a verifiable, reproducibility-first foundation for deterministic local analytics.
