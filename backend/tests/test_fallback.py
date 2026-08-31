"""LLM fallback (§7, §10).

Groq failing must be invisible to the user except in the recorded provider.
Both failing must surface as 503 and must not leak provider names or stack
traces to the client.
"""

from collections.abc import AsyncIterator

import pytest

from app.core.exceptions import LLMUnavailable
from app.llm import client as llm
from app.llm.client import GenerationResult

MESSAGES = [{"role": "user", "content": "what is anaemia"}]


class FakeProvider:
    """Stands in for groq_provider / gemini_provider."""

    def __init__(self, name, tokens=None, error=None, fail_after=None, transient=True):
        self.NAME = name
        self._tokens = tokens or []
        self._error = error
        self._fail_after = fail_after
        self._transient = transient
        self.calls = 0

    def is_transient(self, exc):
        return self._transient

    async def stream(self, messages, max_tokens=1024) -> AsyncIterator[str]:
        self.calls += 1
        for i, token in enumerate(self._tokens):
            if self._fail_after is not None and i == self._fail_after:
                raise self._error or RuntimeError("boom")
            yield token
        if self._error is not None and self._fail_after is None:
            raise self._error

    async def complete(self, messages, max_tokens=1024) -> str:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return "".join(self._tokens)


@pytest.fixture
def patch_providers(monkeypatch):
    def apply(primary, secondary):
        monkeypatch.setattr(llm, "PROVIDERS", (primary, secondary))
    return apply


# --------------------------------------------------------------------------- streaming

async def test_groq_success_never_calls_gemini(patch_providers):
    groq = FakeProvider("groq", tokens=["Anae", "mia is"])
    gemini = FakeProvider("gemini", tokens=["should not run"])
    patch_providers(groq, gemini)

    result = GenerationResult()
    text = "".join([e.text async for e in llm.stream(MESSAGES, result=result)])

    assert text == "Anaemia is"
    assert result.provider == "groq"
    assert result.switched is False
    assert gemini.calls == 0


async def test_gemini_serves_when_groq_fails(patch_providers):
    groq = FakeProvider("groq", error=TimeoutError("groq timed out"))
    gemini = FakeProvider("gemini", tokens=["Anaemia ", "is a ", "condition."])
    patch_providers(groq, gemini)

    result = GenerationResult()
    events = [e async for e in llm.stream(MESSAGES, result=result)]

    assert result.provider == "gemini", "fallback must record the provider that served"
    assert "".join(e.text for e in events) == "Anaemia is a condition."
    assert result.attempts == ["groq", "gemini"]


async def test_midstream_failure_emits_provider_switch(patch_providers):
    """§7: the frontend must be told to discard the partial output."""
    groq = FakeProvider("groq", tokens=["Half ", "an ", "answer"], fail_after=2,
                        error=TimeoutError("died mid-stream"))
    gemini = FakeProvider("gemini", tokens=["A ", "complete ", "answer."])
    patch_providers(groq, gemini)

    result = GenerationResult()
    events = [e async for e in llm.stream(MESSAGES, result=result)]

    switches = [e for e in events if e.kind == "provider_switch"]
    assert len(switches) == 1, "exactly one provider_switch expected"
    assert switches[0].provider == "gemini"
    assert result.switched is True

    # Everything after the switch is Gemini's, and it is a whole answer.
    after = events[events.index(switches[0]) + 1 :]
    assert "".join(e.text for e in after) == "A complete answer."


async def test_both_providers_failing_raises_llm_unavailable(patch_providers):
    patch_providers(
        FakeProvider("groq", error=TimeoutError("down")),
        FakeProvider("gemini", error=TimeoutError("also down")),
    )
    with pytest.raises(LLMUnavailable):
        [e async for e in llm.stream(MESSAGES)]


async def test_empty_stream_counts_as_failure(patch_providers):
    """A provider returning nothing is a failure, not a valid empty answer."""
    groq = FakeProvider("groq", tokens=[])
    gemini = FakeProvider("gemini", tokens=["Real answer."])
    patch_providers(groq, gemini)

    result = GenerationResult()
    text = "".join([e.text async for e in llm.stream(MESSAGES, result=result)])
    assert text == "Real answer."
    assert result.provider == "gemini"


async def test_non_transient_failure_does_not_burn_the_fallback(patch_providers):
    """A bad request fails identically on both providers - don't retry it."""
    groq = FakeProvider("groq", error=ValueError("malformed request"), transient=False)
    gemini = FakeProvider("gemini", tokens=["never reached"])
    patch_providers(groq, gemini)

    with pytest.raises(LLMUnavailable):
        [e async for e in llm.stream(MESSAGES)]
    assert gemini.calls == 0


# --------------------------------------------------------------------------- non-streaming

async def test_complete_falls_back_and_records_provider(patch_providers):
    patch_providers(
        FakeProvider("groq", error=TimeoutError("down")),
        FakeProvider("gemini", tokens=["Grounded answer."]),
    )
    result = GenerationResult()
    text = await llm.complete(MESSAGES, result=result)
    assert text == "Grounded answer."
    assert result.provider == "gemini"
    assert result.switched is True


async def test_complete_raises_when_both_fail(patch_providers):
    patch_providers(
        FakeProvider("groq", error=TimeoutError("down")),
        FakeProvider("gemini", error=TimeoutError("also down")),
    )
    with pytest.raises(LLMUnavailable):
        await llm.complete(MESSAGES)


async def test_llm_unavailable_leaks_nothing(patch_providers):
    """§7: never let a fallback failure leak provider names or stack traces."""
    patch_providers(
        FakeProvider("groq", error=TimeoutError("groq key sk_live_secret invalid")),
        FakeProvider("gemini", error=TimeoutError("gemini AIzaSyFAKE invalid")),
    )
    try:
        await llm.complete(MESSAGES)
    except LLMUnavailable as exc:
        payload = exc.payload()
        assert payload["code"] == "LLM_UNAVAILABLE"
        blob = str(payload).lower()
        for leak in ("groq", "gemini", "sk_live", "aizasy", "traceback"):
            assert leak not in blob, f"error payload leaked {leak!r}"
    else:
        pytest.fail("expected LLMUnavailable")
