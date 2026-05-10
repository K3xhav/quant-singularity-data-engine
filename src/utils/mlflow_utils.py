from __future__ import annotations

from pathlib import Path
from typing import Any

import mlflow

TRACKING_ROOT = Path("mlruns")
EXPERIMENT_NAME = "quant_singularity_data_engine"


def setup_mlflow() -> None:
    TRACKING_ROOT.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(TRACKING_ROOT.resolve().as_uri())
    mlflow.set_experiment(EXPERIMENT_NAME)


def start_pipeline_run(run_name: str) -> Any:
    return mlflow.start_run(run_name=run_name)


def log_json_artifact(path: Path) -> None:
    if not path.exists():
        return
    try:
        mlflow.log_artifact(str(path))
    except Exception:
        return


def log_markdown_artifact(path: Path) -> None:
    if not path.exists():
        return
    try:
        mlflow.log_artifact(str(path))
    except Exception:
        return


def log_metric_if_present(name: str, value: Any) -> None:
    if not isinstance(value, (int, float)):
        return
    try:
        mlflow.log_metric(name, float(value))
    except Exception:
        return
