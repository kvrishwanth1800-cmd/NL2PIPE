"""Run generated pipeline code in isolation before it touches anything real.

v0 isolation = a fresh temp working directory + a subprocess + a wall-clock
timeout. That is enough to stop a generated script from scribbling over your
project, and it means the DuckDB file it produces is disposable. It is NOT a
security boundary against hostile code — real isolation (a microVM such as
Firecracker, or an E2B-style sandbox) is on the roadmap and called out honestly
in the README. Always read generated code before trusting it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    db_path: Path | None  # DuckDB file produced by the run, if any


def run_pipeline_code(
    code: str,
    out_db: str | Path = "sandbox.duckdb",
    timeout: int = 300,
) -> SandboxResult:
    """Execute `code` as a standalone script in a throwaway directory.

    On success the DuckDB file the pipeline created is copied to `out_db`.
    """
    out_db = Path(out_db).resolve()
    with tempfile.TemporaryDirectory(prefix="nl2pipe-") as tmp:
        tmpdir = Path(tmp)
        script = tmpdir / "pipeline.py"
        script.write_text(code, encoding="utf-8")

        # Isolate dlt's global state so each run is hermetic: without this, dlt
        # persists per-pipeline config under ~/.dlt and pins the DuckDB file to
        # wherever the pipeline first ran. Redirecting HOME + DLT_DATA_DIR into
        # the temp dir keeps every sandbox run clean and self-contained.
        env = os.environ.copy()
        env["HOME"] = str(tmpdir)
        env["DLT_DATA_DIR"] = str(tmpdir / ".dlt")

        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )

        db_path: Path | None = None
        if proc.returncode == 0:
            produced = sorted(tmpdir.glob("*.duckdb"))
            if produced:
                shutil.copy(produced[0], out_db)
                db_path = out_db

        return SandboxResult(
            ok=proc.returncode == 0 and db_path is not None,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            db_path=db_path,
        )
