"""Model-agnostic LLM access.

Uses `litellm` so the same code targets Claude, OpenAI, Gemini, OpenRouter, or a
local Ollama model by changing one environment variable — data engineers should
not be locked to a vendor. `litellm` is an optional dependency: import it lazily
so the sandbox/plan/diff/quality path works with no LLM installed and no API key.

Provider errors (bad model name, auth, rate limits, network) are converted into
a single, actionable `LLMCallError` message instead of an 80-line traceback —
the tool should fail cleanly and tell you what to fix.

Environment:
    NL2PIPE_MODEL   e.g. "claude-sonnet-4-5", "gpt-4o", "gemini/gemini-3.6-flash",
                    "openrouter/deepseek/deepseek-chat", "ollama/llama3.1"
    (plus the provider's own key var, e.g. ANTHROPIC_API_KEY / OPENAI_API_KEY /
     GEMINI_API_KEY / OPENROUTER_API_KEY)
"""

from __future__ import annotations

import os
import re

DEFAULT_MODEL = "claude-sonnet-4-5"

# Map a litellm/OpenAI exception class name -> a short, human hint on what to do.
_HINTS: dict[str, str] = {
    "NotFoundError": "That model name isn't available. Check NL2PIPE_MODEL "
    "(providers rename/retire models often) and keep the provider prefix, "
    "e.g. gemini/..., openrouter/....",
    "AuthenticationError": "Authentication failed. Check the provider's API key "
    "env var (e.g. GEMINI_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY).",
    "PermissionDeniedError": "The provider refused this request — often an "
    "account guardrail or data-policy setting blocking the model/provider.",
    "RateLimitError": "Rate limited or out of quota. Wait and retry, or switch model.",
    "ContextWindowExceededError": "The prompt was too large for this model.",
    "APIConnectionError": "Couldn't reach the provider. Check your network/proxy.",
    "Timeout": "The provider timed out. Retry, or try a faster model.",
    "ServiceUnavailableError": "The provider is temporarily unavailable. Retry shortly.",
    "BadRequestError": "The provider rejected the request parameters.",
}


class LLMNotConfigured(RuntimeError):
    """Raised when generation is requested but no LLM backend is installed."""


class LLMCallError(RuntimeError):
    """Raised when the LLM provider call fails (bad model, auth, network, ...)."""


def resolve_model(explicit: str | None = None) -> str:
    return explicit or os.environ.get("NL2PIPE_MODEL", DEFAULT_MODEL)


def _short_reason(exc: Exception) -> str:
    """Pull a concise reason out of a provider exception, dropping the noise."""
    text = getattr(exc, "message", "") or str(exc)
    # Providers often nest the useful sentence in a JSON "message" field.
    m = re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        text = m.group(1).encode().decode("unicode_escape")
    text = " ".join(text.split())  # collapse whitespace/newlines
    return text[:300] + ("…" if len(text) > 300 else "")


def _hint_for(exc: Exception) -> str:
    return _HINTS.get(type(exc).__name__, "")


def complete(system: str, user: str, model: str | None = None) -> str:
    """Return the model's text response for a system+user prompt.

    Raises LLMNotConfigured if litellm isn't installed, or LLMCallError with a
    clean message if the provider call fails.
    """
    try:
        import litellm  # type: ignore
        from litellm import completion  # type: ignore

        # Silence litellm's own "Give Feedback / LiteLLM.Info" banners so our
        # single clean error line is all the user sees on failure.
        litellm.suppress_debug_info = True
        import logging

        logging.getLogger("LiteLLM").setLevel(logging.ERROR)
    except ImportError as exc:  # pragma: no cover - exercised via CLI message
        raise LLMNotConfigured(
            "LLM generation needs the 'llm' extra. Install it with:\n"
            "  pip install 'nl2pipe[llm]'\n"
            "then set NL2PIPE_MODEL and the provider key (e.g. ANTHROPIC_API_KEY).\n"
            "Or skip generation entirely and pass an existing script with --code-file."
        ) from exc

    resolved = resolve_model(model)
    try:
        resp = completion(
            model=resolved,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
    except Exception as exc:  # deliberately distill any provider error into one line
        parts = [f"LLM call to '{resolved}' failed ({type(exc).__name__})."]
        reason = _short_reason(exc)
        if reason:
            parts.append(reason)
        hint = _hint_for(exc)
        if hint:
            parts.append(hint)
        raise LLMCallError("\n".join(parts)) from exc

    return resp["choices"][0]["message"]["content"]
