"""Expose the loaded data as an MCP server.

This is the flywheel piece from the design doc: once a pipeline has loaded data,
any MCP-aware app (Cursor, Claude Desktop, etc.) can query it through governed,
read-only tools. Every tool here is read-only by design — the agent can inspect
and SELECT, never mutate. Requires the 'mcp' extra: `pip install 'nl2pipe[mcp]'`.
"""

from __future__ import annotations

import duckdb


def serve(db_path: str, schema: str = "sandbox") -> None:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "MCP support needs the 'mcp' extra: pip install 'nl2pipe[mcp]'"
        ) from exc

    server = FastMCP("nl2pipe")

    def _connect():
        # read_only connection: agents can never mutate the data.
        return duckdb.connect(db_path, read_only=True)

    @server.tool()
    def list_tables() -> list[str]:
        """List the tables available in the loaded dataset."""
        con = _connect()
        try:
            rows = con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = ? ORDER BY table_name",
                [schema],
            ).fetchall()
            return [r[0] for r in rows if not r[0].startswith("_dlt")]
        finally:
            con.close()

    @server.tool()
    def describe_table(table: str) -> list[dict]:
        """Return column names and types for a table."""
        con = _connect()
        try:
            rows = con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                [schema, table],
            ).fetchall()
            return [{"column": r[0], "type": r[1]} for r in rows]
        finally:
            con.close()

    @server.tool()
    def run_sql(query: str) -> list[dict]:
        """Run a READ-ONLY SQL query against the dataset and return rows."""
        stripped = query.strip().lower()
        if not stripped.startswith(("select", "with")):
            raise ValueError("Only SELECT / WITH queries are allowed.")
        con = _connect()
        try:
            cur = con.execute(query)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            con.close()

    server.run()
