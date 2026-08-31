"""Groq provider.

The configured model (openai/gpt-oss-120b) is a reasoning model: it emits
reasoning tokens before any visible content, and puts them in a separate
`reasoning` field rather than in `content`. Two consequences:

* `delta.content` is already clean - reasoning never leaks into the answer.
* Time-to-first-token is worse than the raw inference speed suggests, because
  reasoning happens first. `reasoning_effort="low"` keeps that short; this task
  is extractive summarisation of supplied context, not a maths olympiad.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from groq import AsyncGroq
from groq import APIError, APIStatusError, APITimeoutError, RateLimitError

from app.config import settings
from app.llm import DEFAULT_MAX_TOKENS

NAME = "groq"
TIMEOUT_S = 8.0  # §7

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key, timeout=TIMEOUT_S, max_retries=0)
    return _client


def is_transient(exc: BaseException) -> bool:
    """Fallback triggers on timeout, 5xx, and provider rate limits - not on a
    valid refusal or a malformed request, which Gemini would fail the same way."""
    if isinstance(exc, (APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500 or exc.status_code == 429
    if isinstance(exc, APIError):
        return True
    return isinstance(exc, (TimeoutError, ConnectionError))


async def stream(messages: list[dict[str, str]], max_tokens: int = DEFAULT_MAX_TOKENS) -> AsyncIterator[str]:
    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.2,  # low: we want faithful extraction, not creativity
        max_tokens=max_tokens,
        reasoning_effort="low",
        stream=True,
    )
    async for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


async def complete(messages: list[dict[str, str]], max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
        reasoning_effort="low",
    )
    return response.choices[0].message.content or ""
