# Quant Singularity Data Engine

Deterministic market-data warehouse for reproducible quantitative analytics. Processes raw NSE data through profiling-first ingestion, semantic validation, curated parquet outputs, benchmark characterization, and deterministic DuckDB-backed analytical access.

## Repository Structure

```text
.
├── data/
│   ├── raw/                  # Vendor CSV feeds
│   ├── staging/              # Intermediate processing + quarantine
│   ├── warehouse/            # Curated parquet outputs + manifest
│   └── validation_reports/   # JSON validation summaries
├── reports/                  # Engineering and benchmark reports
├── src/                      # Source code
├── run.py                    # CLI entry point
└── pyproject.toml            # Project dependencies
```

## Setup Instructions

Requires Python 3.12+.

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

Optional uv workflow:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Running the Pipeline

Primary workflow:

```bash
python run.py build
```

This executes the end-to-end deterministic workflow:

* profiling
* validation
* warehouse generation
* benchmarking
* manifest creation
* access verification

Additional commands:

```bash
python run.py profile
python run.py validate
python run.py benchmark
python run.py access
```

## Generated Outputs

| Output                              | Location                       |
| ----------------------------------- | ------------------------------ |
| Profiling reports                   | `reports/`                     |
| Validation summaries                | `data/validation_reports/`     |
| Curated parquet warehouse           | `data/warehouse/`              |
| Quarantine outputs                  | `data/staging/quarantine/`     |
| Benchmark reports                   | `reports/benchmark_report.md`  |
| Warehouse manifest/version metadata | `data/warehouse/manifest.json` |

## Key Engineering Decisions

* Profiling-first ingestion before validation-policy enforcement.
* Trust annotations instead of destructive filtering for semantically ambiguous vendor-feed behavior.
* Deterministic ordering semantics for stable downstream retrieval behavior.
* Selective quarantine strategy for low-ambiguity structural anomalies.
* DuckDB + parquet for inspectable local analytical workflows.
* Typed access contracts for deterministic consumer-facing retrieval semantics.
* Local MLflow traceability for reproducible run tracking and artifact logging.

## Reports

| Report                                | Purpose                                         |
| ------------------------------------- | ----------------------------------------------- |
| `reports/final_engineering_report.md` | Architecture and engineering decisions          |
| `reports/interview_walkthrough.md`    | Technical walkthrough and interview preparation |
| `reports/benchmark_report.md`         | Benchmark characterization                      |
| `reports/profiling_summary.md`        | Profiling and anomaly findings                  |

## Limitations

* Local-only execution model.
* No partition-aware pruning or distributed execution strategy.
* Simplified query semantics.
* Warm-process benchmark characterization only.
* Vendor-feed semantic ambiguity requires annotation-based interpretation rather than strict invariant enforcement.

## Example Commands

```bash
python run.py build
python run.py benchmark
python run.py access
```
