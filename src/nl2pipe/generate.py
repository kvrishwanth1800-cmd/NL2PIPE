"""Turn a natural-language request into dlt pipeline source code."""

from __future__ import annotations

from . import llm
from .prompts import SYSTEM_PROMPT


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences a model may add despite instructions.

    Pure function so it can be unit-tested without any network/LLM call.
    """
    t = text.strip()
    if t.startswith("```"):
        # drop the opening fence line (``` or ```python)
        first_newline = t.find("\n")
        if first_newline != -1:
            t = t[first_newline + 1 :]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip() + "\n"


def generate_pipeline(request: str, model: str | None = None) -> str:
    """Generate runnable dlt pipeline code for a plain-English request."""
    raw = llm.complete(SYSTEM_PROMPT, request, model=model)
    return strip_code_fences(raw)
