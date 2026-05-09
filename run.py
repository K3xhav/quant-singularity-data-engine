import typer

app = typer.Typer()

@app.command()
def profile():
    print("Profiling pipeline")

@app.command()
def validate():
    print("Validation pipeline")

@app.command()
def build_warehouse():
    print("Warehouse build pipeline")

@app.command()
def benchmark():
    print("Benchmark pipeline")

if __name__ == "__main__":
    app()
