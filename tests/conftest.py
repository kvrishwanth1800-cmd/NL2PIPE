from pathlib import Path

import pytest

from nl2pipe.sandbox import run_pipeline_code

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "example_pipeline.py"


@pytest.fixture(scope="session")
def sandbox_db(tmp_path_factory) -> Path:
    """Run the example pipeline in the sandbox once and return the DuckDB path."""
    out = tmp_path_factory.mktemp("db") / "sandbox.duckdb"
    result = run_pipeline_code(EXAMPLE.read_text(encoding="utf-8"), out_db=out)
    assert result.ok, f"sandbox run failed:\n{result.stderr}"
    return out
