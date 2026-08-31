"""Unified LLM interface with Groq -> Gemini fallback (§7).

The mid-stream case is the interesting one. If Groq dies after emitting tokens,
we cannot simply continue with Gemini - the two halves would not join up into a
coherent answer. So the stream yields a `provider_switch` signal, the caller
discards what it has shown, and Gemini's output replaces it from the start.

Failure of both providers raises LLMUnavailable, which the API layer turns into a
503 error event carrying no provider names or stack traces.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.core.exceptions import LLMUnavailable
from app.llm import DEFAULT_MAX_TOKENS, gemini_provider, groq_provider

log = logging.getLogger(__name__)

PROVIDERS = (groq_provider, gemini_provider)


@dataclass
class GenerationResult:
    """Filled in as generation proceeds; read after the stream is exhausted."""

    provider: str | None = None
    latency_ms: int | None = None
    switched: bool = False
    attempts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StreamEvent:
    """Either a token, or a signal that the frontend must reset its buffer."""

    kind: str  # "token" | "provider_switch"
    text: str = ""
    provider: str = ""


async def stream(
    messages: list[dict[str, str]],
    result: GenerationResult | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> AsyncIterator[StreamEvent]:
    """Stream from Groq, falling back to Gemini on a transient failure."""
    result = result if result is not None else GenerationResult()
    started = time.perf_counter()
    last_error: BaseException | None = None

    for index, provider in enumerate(PROVIDERS):
        emitted = 0
        result.attempts.append(provider.NAME)
        try:
            async for token in provider.stream(messages, max_tokens=max_tokens):
                if emitted == 0 and index > 0:
                    # Tell the caller to throw away the previous provider's
                    # partial output before rendering anything from this one.
                    result.switched = True
                    yield StreamEvent(kind="provider_switch", provider=provider.NAME)
                emitted += 1
                yield StreamEvent(kind="token", text=token, provider=provider.NAME)

            if emitted == 0:
                raise RuntimeError(f"{provider.NAME} produced an empty stream")

            result.provider = provider.NAME
            result.latency_ms = int((time.perf_counter() - started) * 1000)
            return

        except Exception as exc:
            last_error = exc
            is_last = index == len(PROVIDERS) - 1
            if not is_last and not provider.is_transient(exc) and emitted == 0:
                # A non-transient failure (bad request, content refusal) would
                # fail the same way on the other provider. Don't burn the
                # fallback on it - but do fall back if we died mid-stream,
                # because the user is otherwise left with half an answer.
                log.warning("%s failed non-transiently: %s", provider.NAME, type(exc).__name__)
                raise LLMUnavailable() from exc
            log.warning(
                "%s failed after %d token(s), falling back: %s",
                provider.NAME,
                emitted,
                type(exc).__name__,
            )

    log.error("all providers failed; last error: %s", type(last_error).__name__)
    raise LLMUnavailable() from last_error


async def complete(
    messages: list[dict[str, str]],
    result: GenerationResult | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Non-streaming generation with the same fallback policy."""
    result = result if result is not None else GenerationResult()
    started = time.perf_counter()
    last_error: BaseException | None = None

    for index, provider in enumerate(PROVIDERS):
        result.attempts.append(provider.NAME)
        try:
            text = await provider.complete(messages, max_tokens=max_tokens)
            if not text.strip():
                raise RuntimeError(f"{provider.NAME} returned an empty completion")
            result.provider = provider.NAME
            result.latency_ms = int((time.perf_counter() - started) * 1000)
            result.switched = index > 0
            return text
        except Exception as exc:
            last_error = exc
            if index < len(PROVIDERS) - 1 and not provider.is_transient(exc):
                log.warning("%s failed non-transiently: %s", provider.NAME, type(exc).__name__)
                raise LLMUnavailable() from exc
            log.warning("%s failed, falling back: %s", provider.NAME, type(exc).__name__)

    log.error("all providers failed; last error: %s", type(last_error).__name__)
    raise LLMUnavailable() from last_error
