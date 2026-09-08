# nl2pipe

**Describe a data pipeline in plain English → get a working [`dlt`](https://dlthub.com) pipeline, sandbox-run on DuckDB, with a plan/diff you approve before anything is written.**

`nl2pipe` is a small, honest CLI for the part of data engineering that is pure toil: writing the boilerplate for a new pipeline and its data-quality checks. It generates the code, proves it runs against sampled data in an isolated sandbox, shows you a Terraform-style plan of exactly what would land (tables, columns, types, row counts), and only writes the pipeline **after you approve**. The output is plain `dlt` code you own — drop it into Airflow, Dagster, or cron.

```
 request ──► generate dlt code ──► run in sandbox ──► show plan/diff
          ──► you approve ──► write pipeline.py ──► auto-generate DQ checks
```

## Why this exists (and what it deliberately does *not* do)

Data teams lose **40–50% of their time to pipeline building and maintenance** and another large chunk to data-quality firefighting (Fivetran/Wakefield 2021; Monte Carlo 2022). LLMs make *generating* a pipeline nearly free — but engineers won't run generated code blind, and generation is only ~10% of the job.

So `nl2pipe` is built around the *valuable* parts, not the flashy one:

- ✅ **Drafts the boilerplate** of a new pipeline in seconds.
- ✅ **Sandboxes it** in a throwaway dir before it touches anything real.
- ✅ **Shows a plan/diff** so a human reviews schema impact before apply.
- ✅ **Auto-generates data-quality checks** (the chore everyone skips).
- ✅ **Gives you code you own** — no runtime lock-in.
- ✅ **Model-agnostic** — Claude, OpenAI, or local Ollama via one env var.

It does **not** maintain pipelines, handle schema drift, or replace your judgment — the human approval gate is the point. Isolation in v0 is a subprocess + temp dir + timeout, *not* a security boundary against hostile code; always read generated code before trusting it. Real microVM isolation is on the roadmap.

## Quickstart

### Windows (PowerShell)
```powershell
git clone https://github.com/your-username/nl2pipe; cd nl2pipe
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[llm]"

# point it at any model you like:
$env:NL2PIPE_MODEL = "claude-sonnet-4-5"      # or "gpt-4o", or "ollama/llama3.1"
$env:ANTHROPIC_API_KEY = "sk-..."              # or OPENAI_API_KEY, or nothing for Ollama

nl2pipe build "Load the public GitHub events API into a table, incremental on created_at"
```

### macOS / Linux
```bash
git clone https://github.com/your-username/nl2pipe && cd nl2pipe
python -m venv .venv && source .venv/bin/activate
pip install -e ".[llm]"
export NL2PIPE_MODEL="claude-sonnet-4-5" ANTHROPIC_API_KEY="sk-..."
nl2pipe build "Load the public GitHub events API into a table, incremental on created_at"
```

### No API key? Try it offline
The whole sandbox → plan → diff → quality path works on any existing `dlt` script:
```bash
pip install -e .           # base install, no LLM needed
nl2pipe build --code-file examples/example_pipeline.py --emit-checks dq.sql
```

## Providers

Model-agnostic via [litellm](https://github.com/BerriAI/litellm) — set `NL2PIPE_MODEL` and the provider's own key:

| Provider | `NL2PIPE_MODEL` | Key variable |
|---|---|---|
| Anthropic | `claude-sonnet-4-5` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Google Gemini | `gemini/gemini-2.5-flash` | `GEMINI_API_KEY` |
| OpenRouter | `openrouter/deepseek/deepseek-chat` | `OPENROUTER_API_KEY` |
| Local (Ollama) | `ollama/llama3.1` | *(none)* |

Provider errors fail cleanly with one actionable line — no stack trace. If you see
`model ... is no longer available`, the provider retired that name: grab the current
one from their console and keep the prefix (e.g. `gemini/...`). If a provider says the
model is *blocked by a guardrail / data policy*, that's an account setting on the
provider's side, not this tool.

## Commands

| Command | What it does |
|---|---|
| `nl2pipe build "<request>"` | Generate → sandbox → plan → approve → write `pipeline.py` → DQ checks |
| `nl2pipe build --code-file X.py` | Same flow, but run an existing script instead of generating |
| `nl2pipe check` | Generate + run data-quality checks on an already-loaded DuckDB |
| `nl2pipe check --llm` | Also ask the model for domain-specific checks |
| `nl2pipe mcp` | Serve the loaded data as a read-only MCP server (needs `.[mcp]`) |

Useful flags: `--yes` (skip approval, for CI), `--no-quality`, `--emit-checks dq.sql`, `--model`, `--db`, `--out`.

## What a run looks like

```
Plan — applying this pipeline would create:

+ users   (~3 rows)
  column   | type    | nullable
  id       | BIGINT  |    —
  name     | VARCHAR |    ✓
  email    | VARCHAR |    ✓

Apply? (writes the pipeline to disk) [y/n]: y
✓ Applied. Saved pipeline.py — you own this code.

Data-quality checks
  PASS  users: not empty
  PASS  users.id: no nulls
  PASS  users.id: unique
```

## MCP integration

Once data is loaded, `nl2pipe mcp` exposes read-only tools (`list_tables`, `describe_table`, `run_sql`) over the [Model Context Protocol](https://modelcontextprotocol.io), so Cursor / Claude Desktop can query your data through a governed, SELECT-only surface. Every query you ship becomes something your AI apps can trust.

## Architecture

```
cli.py        Typer commands, approval gate
 ├─ generate  request ──► dlt code (model-agnostic via litellm)
 ├─ sandbox   run code in isolated temp dir → disposable DuckDB
 ├─ plan      inspect schema → render Terraform-style plan/diff
 ├─ quality   profile data → deterministic DQ checks (+ optional LLM)
 └─ mcp       expose loaded data as read-only MCP tools
```

Each module is small, pure where possible, and independently tested. See `tests/`.

## Roadmap

- **v0.2 (now)** — generate · sandbox · plan/diff/apply · auto DQ checks · MCP server
- **v0.3** — warehouse targets (Postgres, Snowflake, BigQuery), incremental-diff against an existing table, schema-drift detection
- **v0.4** — real microVM isolation, connector auto-generation from an OpenAPI spec
- **later** — the broader vision: a governed, verification-first substrate for autonomous data engineering (this CLI is its validated first wedge)

## License

Apache-2.0. See [LICENSE](LICENSE).
