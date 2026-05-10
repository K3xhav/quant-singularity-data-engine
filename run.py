import typer

from src.access.runner import run_access_demo
from src.benchmarks.runner import run_benchmarks
from src.profiling.runner import run_profiling
from src.utils.mlflow_utils import log_json_artifact, setup_mlflow, start_pipeline_run
from src.validation.runner import run_validation
from src.warehouse.manifest import MANIFEST_PATH, build_manifest

app = typer.Typer()
setup_mlflow()


@app.command()
def profile():
    """Profiling pipeline"""
    with start_pipeline_run("profiling"):
        run_profiling()


@app.command()
def validate():
    """Validation pipeline"""
    with start_pipeline_run("validation"):
        run_validation()


@app.command()
def access():
    """Warehouse access demo"""
    with start_pipeline_run("access"):
        run_access_demo()


@app.command()
def build():
    """Sequential pipeline build"""
    with start_pipeline_run("profiling"):
        run_profiling()
    with start_pipeline_run("validation"):
        run_validation()
    with start_pipeline_run("benchmark"):
        run_benchmarks()
    with start_pipeline_run("access"):
        run_access_demo()
        build_manifest()
        log_json_artifact(MANIFEST_PATH)


@app.command()
def build_warehouse():
    """Warehouse build pipeline"""
    print("Warehouse build pipeline")


@app.command()
def benchmark():
    with start_pipeline_run("benchmark"):
        run_benchmarks()


if __name__ == "__main__":
    app()
