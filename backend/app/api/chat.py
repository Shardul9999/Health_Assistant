"""POST /api/chat - the main endpoint (§4).

Pipeline order matters and is not negotiable:

    1. rate limit
    2. red-flag check on the RAW message      <- before anything else touches it
    3. retrieval with the similarity floor
    4. generation, only if retrieval found something

Steps 2 and 3 both short-circuit. A red-flag message never reaches the retriever
or the LLM; an off-corpus message never reaches the LLM. In both cases the reply
is fixed text written in advance, and both are persisted like any other message
so the session history stays complete.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LLMUnavailable, RateLimited
from app.core.rate_limit import check as check_rate_limit
from app.db.models import Message, Session
from app.db.session import AsyncSessionLocal, get_db
from app.deps import CurrentUser
from app.llm import client as llm
from app.rag.prompts import build_messages
from app.rag.retriever import RetrievedChunk, retrieve
from app.safety.disclaimers import NO_CONTEXT_RESPONSE, STANDARD_DISCLAIMER, escalation_response
from app.safety.red_flags import detect as detect_red_flag
from app.schemas.chat import ChatRequest, ChatResponse, SourceCitation
from app.services.sessions import get_owned_session

router = APIRouter(prefix="/api", tags=["chat"])


def _citations(chunks: list[RetrievedChunk]) -> list[SourceCitation]:
    return [
        SourceCitation(
            id=c.id,
            title=c.title,
            source_url=c.source_url,
            source_org=c.source_org,
            license=c.license,
            snippet=c.snippet(),
            similarity=round(c.similarity, 4),
        )
        for c in chunks
    ]


async def _resolve_session(
    db: AsyncSession, user_id: str, session_id: uuid.UUID | None, first_message: str
) -> Session:
    if session_id is not None:
        return await get_owned_session(db, session_id, user_id)
    # Title from the first message, trimmed. Generating one via the LLM would
    # add a second round trip to every new conversation for very little gain.
    title = first_message.strip().split("\n")[0][:60]
    session = Session(clerk_user_id=user_id, title=title or "New conversation")
    db.add(session)
    await db.flush()
    return session


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Non-streaming chat. Same pipeline as the SSE endpoint, easier to curl."""
    limit = await check_rate_limit(user.user_id)
    if not limit.allowed:
        raise RateLimited(retry_after_s=limit.retry_after_s)

    started = time.perf_counter()
    session = await _resolve_session(db, user.user_id, body.session_id, body.message)
    db.add(Message(session_id=session.id, role="user", content=body.message))

    flag = detect_red_flag(body.message)
    if flag is not None:
        # Short-circuit: no embedding, no retrieval, no LLM call.
        content = escalation_response(flag.category)
        assistant = Message(
            session_id=session.id,
            role="assistant",
            content=content,
            was_red_flag=True,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        db.add(assistant)
        await db.commit()
        return ChatResponse(
            session_id=session.id,
            message_id=assistant.id,
            content=content,
            sources=[],
            provider=None,
            latency_ms=assistant.latency_ms,
            red_flag=True,
            red_flag_category=flag.category.value,
            disclaimer=STANDARD_DISCLAIMER,
        )

    chunks = await retrieve(db, body.message)
    if not chunks:
        # Grounding is enforced here: the model is never given the chance to
        # answer from its own knowledge.
        assistant = Message(
            session_id=session.id,
            role="assistant",
            content=NO_CONTEXT_RESPONSE,
            retrieved_chunk_ids=[],
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        db.add(assistant)
        await db.commit()
        return ChatResponse(
            session_id=session.id,
            message_id=assistant.id,
            content=NO_CONTEXT_RESPONSE,
            sources=[],
            provider=None,
            latency_ms=assistant.latency_ms,
            red_flag=False,
            disclaimer=STANDARD_DISCLAIMER,
        )

    result = llm.GenerationResult()
    content = await llm.complete(build_messages(body.message, chunks), result=result)

    assistant = Message(
        session_id=session.id,
        role="assistant",
        content=content,
        retrieved_chunk_ids=[c.id for c in chunks],
        llm_provider=result.provider,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    db.add(assistant)
    await db.commit()

    return ChatResponse(
        session_id=session.id,
        message_id=assistant.id,
        content=content,
        sources=_citations(chunks),
        provider=result.provider,
        latency_ms=assistant.latency_ms,
        red_flag=False,
        disclaimer=STANDARD_DISCLAIMER,
    )


# --------------------------------------------------------------------------- SSE


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _chat_events(body: ChatRequest, user_id: str) -> AsyncIterator[str]:
    """Yields the event stream described in §4.

    Owns its own DB session rather than using the request-scoped dependency: the
    response body outlives the handler, and FastAPI closes dependency-managed
    sessions when the handler returns.
    """
    started = time.perf_counter()

    limit = await check_rate_limit(user_id)
    if not limit.allowed:
        yield _sse(
            "error",
            {
                "code": "RATE_LIMITED",
                "message": "You've sent too many messages. Please wait a moment.",
                "retry_after_s": limit.retry_after_s,
            },
        )
        return

    async with AsyncSessionLocal() as db:
        try:
            session = await _resolve_session(db, user_id, body.session_id, body.message)
        except Exception:
            yield _sse("error", {"code": "NOT_FOUND", "message": "Session not found."})
            return

        yield _sse("session", {"session_id": str(session.id)})
        db.add(Message(session_id=session.id, role="user", content=body.message))

        flag = detect_red_flag(body.message)
        if flag is not None:
            content = escalation_response(flag.category)
            latency = int((time.perf_counter() - started) * 1000)
            db.add(
                Message(
                    session_id=session.id,
                    role="assistant",
                    content=content,
                    was_red_flag=True,
                    latency_ms=latency,
                )
            )
            await db.commit()
            # Sent whole, not token by token - this must not look like a normal
            # streamed chat reply.
            yield _sse("red_flag", {"category": flag.category.value, "content": content})
            yield _sse(
                "done",
                {"provider": None, "latency_ms": latency, "red_flag": True},
            )
            return

        chunks = await retrieve(db, body.message)
        yield _sse(
            "sources",
            {"chunks": [c.model_dump(mode="json") for c in _citations(chunks)]},
        )

        if not chunks:
            latency = int((time.perf_counter() - started) * 1000)
            db.add(
                Message(
                    session_id=session.id,
                    role="assistant",
                    content=NO_CONTEXT_RESPONSE,
                    retrieved_chunk_ids=[],
                    latency_ms=latency,
                )
            )
            await db.commit()
            yield _sse("no_context", {"content": NO_CONTEXT_RESPONSE})
            yield _sse(
                "done", {"provider": None, "latency_ms": latency, "red_flag": False}
            )
            return

        result = llm.GenerationResult()
        parts: list[str] = []
        try:
            async for event in llm.stream(build_messages(body.message, chunks), result=result):
                if event.kind == "provider_switch":
                    # The frontend discards what it has rendered and starts over
                    # from the new provider's output (§7).
                    parts.clear()
                    yield _sse("provider_switch", {"provider": event.provider})
                else:
                    parts.append(event.text)
                    yield _sse("token", {"text": event.text})
        except LLMUnavailable:
            yield _sse(
                "error",
                {
                    "code": "LLM_UNAVAILABLE",
                    "message": "The assistant is temporarily unavailable. Please try again shortly.",
                },
            )
            return

        latency = int((time.perf_counter() - started) * 1000)
        db.add(
            Message(
                session_id=session.id,
                role="assistant",
                content="".join(parts),
                retrieved_chunk_ids=[c.id for c in chunks],
                llm_provider=result.provider,
                latency_ms=latency,
            )
        )
        await db.commit()

        yield _sse(
            "done",
            {"provider": result.provider, "latency_ms": latency, "red_flag": False},
        )


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, user: CurrentUser) -> StreamingResponse:
    return StreamingResponse(
        _chat_events(body, user.user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # stop nginx buffering the stream in Phase 4
        },
    )
