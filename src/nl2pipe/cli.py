"""nl2pipe command line interface.

Flow (the whole point of the tool):
    request ──► generate dlt code ──► run in sandbox ──► show plan/diff
             ──► human approves ──► write pipeline.py ──► generate DQ checks
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape
from rich.prompt import Confirm
from rich.syntax import Syntax

from . import __version__
from . import quality as q
from .plan import inspect_dataset, render_plan
from .sandbox import run_pipeline_code

app = typer.Typer(
    add_completion=False,
    help="Describe a data pipeline in plain English; get a working dlt pipeline, "
    "sandbox-run on DuckDB, with a plan/diff you approve before it writes anything.",
)
console = Console()


def _load_code(request: str | None, code_file: Path | None, model: str | None) -> str:
    if code_file:
        return Path(code_file).read_text(encoding="utf-8")
    if not request:
        console.print("[red]Provide a REQUEST, or pass --code-file with an existing script.[/]")
        raise typer.Exit(2)
    from .generate import generate_pipeline
    from .llm import LLMNotConfigured

    try:
        with console.status("[cyan]Generating pipeline...[/]"):
            return generate_pipeline(request, model=model)
    except LLMNotConfigured as exc:
        console.print(f"[red]{escape(str(exc))}[/]")
        raise typer.Exit(3) from exc


@app.command()
def build(
    request: str | None = typer.Argument(None, help="What you want, in plain English."),
    code_file: Path | None = typer.Option(
        None, "--code-file", help="Use an existing dlt script instead of generating one."
    ),
    db: Path = typer.Option("sandbox.duckdb", "--db", help="Where to write the sandbox DuckDB."),
    out: Path = typer.Option("pipeline.py", "--out", help="Where to save the approved pipeline."),
    model: str | None = typer.Option(None, "--model", help="Override NL2PIPE_MODEL."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the approval prompt (CI use)."),
    quality: bool = typer.Option(True, "--quality/--no-quality", help="Generate DQ checks."),
    emit_checks: Path | None = typer.Option(
        None, "--emit-checks", help="Also write the checks to a .sql file."
    ),
):
    """Generate (or load) a pipeline, sandbox it, show the plan, and apply on approval."""
    code = _load_code(request, code_file, model)

    console.print("\n[bold]Generated pipeline[/]")
    console.print(Syntax(code, "python", theme="ansi_dark", line_numbers=False))

    console.print("\n[bold yellow]Sandbox run[/] (isolated temp dir, sampled/real data → DuckDB)")
    result = run_pipeline_code(code, out_db=db)
    if not result.ok:
        console.print("[bold red]Pipeline failed in sandbox — not applying.[/]")
        console.print(result.stderr[-2000:] or result.stdout[-2000:])
        raise typer.Exit(1)
    console.print("[green]✓ ran cleanly[/]")

    plans = inspect_dataset(db)
    render_plan(plans, console)

    if not yes and not Confirm.ask("\n[bold]Apply?[/] (writes the pipeline to disk)"):
        console.print("[dim]Discarded. Nothing written.[/]")
        raise typer.Exit(0)

    Path(out).write_text(code, encoding="utf-8")
    console.print(f"[bold green]✓ Applied.[/] Saved [bold]{out}[/] — you own this code.")

    if quality:
        _run_quality(db, model=model, emit=emit_checks, use_llm=False)


@app.command()
def check(
    db: Path = typer.Option("sandbox.duckdb", "--db", help="DuckDB file to check."),
    model: str | None = typer.Option(None, "--model"),
    llm: bool = typer.Option(False, "--llm", help="Also ask an LLM for domain checks."),
    emit_checks: Path | None = typer.Option(None, "--emit-checks"),
):
    """Generate and run data-quality checks against an already-loaded DuckDB."""
    if not Path(db).exists():
        console.print(f"[red]{db} not found. Run `nl2pipe build` first.[/]")
        raise typer.Exit(2)
    _run_quality(db, model=model, emit=emit_checks, use_llm=llm)


def _run_quality(db: Path, model: str | None, emit: Path | None, use_llm: bool) -> None:
    console.print("\n[bold]Data-quality checks[/]")
    checks = q.generate_checks(db)
    if use_llm:
        try:
            checks += q.suggest_llm_checks(db, schema="sandbox", model=model)
        except Exception as exc:  # noqa: BLE001 - LLM is best-effort here
            console.print(f"[yellow]LLM checks skipped: {exc}[/]")

    results = q.run_checks(db, checks)
    passed = sum(r.passed for r in results)
    for r in results:
        mark = "[green]PASS[/]" if r.passed else f"[red]FAIL ({r.bad_rows} bad rows)[/]"
        console.print(f"  {mark}  {r.check.name}")
    console.print(f"\n[bold]{passed}/{len(results)} checks passed.[/]")

    if emit:
        Path(emit).write_text(q.checks_to_sql(checks), encoding="utf-8")
        console.print(f"[green]✓ wrote checks to {emit}[/]")


@app.command()
def mcp(
    db: Path = typer.Option("sandbox.duckdb", "--db", help="DuckDB file to serve."),
):
    """Expose the loaded data as an MCP server (needs the 'mcp' extra)."""
    from .mcp_server import serve

    serve(str(db))


@app.command()
def version():
    """Print the version."""
    console.print(f"nl2pipe {__version__}")


if __name__ == "__main__":
    app()
