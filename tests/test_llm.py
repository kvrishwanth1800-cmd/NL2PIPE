import sys
import types

import pytest

from nl2pipe import llm


def test_short_reason_pulls_json_message():
    class E(Exception):
        pass

    e = E()
    e.message = (
        'GeminiException - {"error": {"message": "This model '
        'models/gemini-2.0-flash is no longer available. Please update.", "code": 404}}'
    )
    reason = llm._short_reason(e)
    assert "no longer available" in reason
    assert "{" not in reason  # raw JSON stripped out


def test_hint_for_known_and_unknown():
    class NotFoundError(Exception):
        pass

    class Weird(Exception):
        pass

    assert "model" in llm._hint_for(NotFoundError()).lower()
    assert llm._hint_for(Weird()) == ""


def test_complete_wraps_provider_error(monkeypatch):
    fake = types.ModuleType("litellm")

    class NotFoundError(Exception):
        def __init__(self):
            super().__init__("boom")
            self.message = 'x {"message": "model gone, use new-model"} y'

    def completion(**kwargs):
        raise NotFoundError()

    fake.completion = completion
    monkeypatch.setitem(sys.modules, "litellm", fake)

    with pytest.raises(llm.LLMCallError) as ei:
        llm.complete("sys", "user", model="gemini/whatever")

    msg = str(ei.value)
    assert "gemini/whatever" in msg   # names the model it tried
    assert "NotFoundError" in msg     # names the error class
    assert "model gone" in msg        # surfaces the provider's reason
