"""Model-agnostic LLM access.

Uses `litellm` so the same code targets Claude, OpenAI, or a local Ollama model
by changing one environment variable — data engineers should not be locked to a
vendor. `litellm` is an optional dependency: import it lazily so the
sandbox/plan/diff/quality path works with no LLM installed and no API key.

Environment:
    NL2PIPE_MODEL   e.g. "claude-sonnet-4-5", "gpt-4o", "ollama/llama3.1"
    (plus the provider's own key var, e.g. ANTHROPIC_API_KEY / OPENAI_API_KEY)
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-sonnet-4-5"


class LLMNotConfigured(RuntimeError):
    """Raised when generation is requested but no LLM backend is available."""


def resolve_model(explicit: str | None = None) -> str:
    return explicit or os.environ.get("NL2PIPE_MODEL", DEFAULT_MODEL)


def complete(system: str, user: str, model: str | None = None) -> str:
    """Return the model's text response for a system+user prompt."""
    try:
        from litellm import completion  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via CLI message
        raise LLMNotConfigured(
            "LLM generation needs the 'llm' extra. Install it with:\n"
            "  pip install 'nl2pipe[llm]'\n"
            "then set NL2PIPE_MODEL and the provider key (e.g. ANTHROPIC_API_KEY).\n"
            "Or skip generation entirely and pass an existing script with --code-file."
        ) from exc

    resp = completion(
        model=resolve_model(model),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    return resp["choices"][0]["message"]["content"]
