"""Inspect what a pipeline produced and render a plan/diff before apply.

This is the point of the whole tool: an engineer will not run generated pipeline
code blind. After the sandbox run we read the resulting DuckDB schema and show,
Terraform-style, exactly what would be created — tables, columns, types, row
counts — so a human can approve (or reject) before any file is written or any
warehouse is touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb
from rich.console import Console
from rich.table import Table

# dlt bookkeeping tables/schemas we hide from the user-facing plan.
INTERNAL_PREFIX = "_dlt"


@dataclass
class Column:
    name: str
    dtype: str
    nullable: bool


@dataclass
class TablePlan:
    name: str
    rows: int
    columns: list[Column] = field(default_factory=list)


def inspect_dataset(db_path: str | Path, schema: str = "sandbox") -> list[TablePlan]:
    """Return the user-facing tables in `schema` with columns and row counts."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        catalog = con.execute("SELECT current_database()").fetchone()[0]
        tables = con.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = ? AND table_catalog = ?
            ORDER BY table_name
            """,
            [schema, catalog],
        ).fetchall()

        plans: list[TablePlan] = []
        for (tbl,) in tables:
            if tbl.startswith(INTERNAL_PREFIX):
                continue
            cols_raw = con.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = ? AND table_name = ?
                ORDER BY ordinal_position
                """,
                [schema, tbl],
            ).fetchall()
            columns = [
                Column(name=c[0], dtype=c[1], nullable=(str(c[2]).upper() == "YES"))
                for c in cols_raw
                if not c[0].startswith(INTERNAL_PREFIX)
            ]
            rows = con.execute(
                f'SELECT count(*) FROM "{catalog}"."{schema}"."{tbl}"'
            ).fetchone()[0]
            plans.append(TablePlan(name=tbl, rows=rows, columns=columns))
        return plans
    finally:
        con.close()


def render_plan(plans: list[TablePlan], console: Console | None = None) -> None:
    """Pretty-print the plan/diff to the terminal."""
    console = console or Console()
    if not plans:
        console.print("[yellow]No user tables were produced.[/]")
        return

    console.print("\n[bold green]Plan[/] — applying this pipeline would create:\n")
    for tp in plans:
        table = Table(title=f"+ {tp.name}   (~{tp.rows:,} rows)", title_justify="left")
        table.add_column("column", style="bold")
        table.add_column("type")
        table.add_column("nullable", justify="center")
        for col in tp.columns:
            table.add_row(col.name, col.dtype, "✓" if col.nullable else "—")
        console.print(table)
