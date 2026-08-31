"""Gemini provider - the fallback leg of §7.

Gemini takes the system prompt as a separate `system_instruction` rather than a
message with role "system", so the shared message list is split here. Everything
else about the interface matches groq_provider so client.py can treat them
interchangeably.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.config import settings
from app.llm import DEFAULT_MAX_TOKENS

NAME = "gemini"
TIMEOUT_S = 12.0  # §7

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def is_transient(exc: BaseException) -> bool:
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status in (429, 500, 502, 503, 504):
        return True
    text = str(exc)
    return any(
        marker in text
        for marker in ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL")
    ) or isinstance(exc, (TimeoutError, ConnectionError))


def _split(messages: list[dict[str, str]]) -> tuple[str, list[types.Content]]:
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
        if m["role"] != "system"
    ]
    return system, contents


def _config(system: str, max_tokens: int) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=system or None,
        temperature=0.2,
        max_output_tokens=max_tokens,
        # gemini-2.5-flash thinks by default, and thinking tokens are charged
        # against max_output_tokens. Left on, they silently eat the budget and
        # the visible answer gets truncated mid-sentence. This task is extractive
        # summarisation of supplied context, so there is nothing to think about.
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        http_options=types.HttpOptions(timeout=int(TIMEOUT_S * 1000)),
    )


async def stream(messages: list[dict[str, str]], max_tokens: int = DEFAULT_MAX_TOKENS) -> AsyncIterator[str]:
    client = _get_client()
    system, contents = _split(messages)
    response = await client.aio.models.generate_content_stream(
        model=settings.gemini_model,
        contents=contents,
        config=_config(system, max_tokens),
    )
    async for chunk in response:
        if chunk.text:
            yield chunk.text


async def complete(messages: list[dict[str, str]], max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    client = _get_client()
    system, contents = _split(messages)
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=_config(system, max_tokens),
    )
    return response.text or ""
