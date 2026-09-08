# Contributing

Thanks for your interest! This project is intentionally small and sharp.

## Dev setup
```bash
python -m venv .venv && source .venv/bin/activate   # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev,llm,mcp]"
```

## Before opening a PR
```bash
ruff check .
pytest
```
Both must pass (CI enforces them). Add a test for any behavior change — the
sandbox/plan/quality path is fully testable offline with the example pipeline,
so no API key is needed to contribute.

## Scope
Keep the core honest: generation is the easy part; the value is the
sandbox + plan/diff/apply gate + data-quality checks. Features that erode the
human approval step will not be merged.
