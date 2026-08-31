"""Request/response models for the chat and session APIs (§4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=4000)


class SourceCitation(BaseModel):
    id: uuid.UUID
    title: str
    source_url: str
    source_org: str
    license: str
    snippet: str
    similarity: float


class ChatResponse(BaseModel):
    """Non-streaming response. The SSE endpoint carries the same fields split
    across `session` / `sources` / `token` / `done` events."""

    session_id: uuid.UUID
    message_id: uuid.UUID
    content: str
    sources: list[SourceCitation]
    provider: str | None
    latency_ms: int | None
    red_flag: bool
    red_flag_category: str | None = None
    disclaimer: str


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    retrieved_chunk_ids: list[uuid.UUID] | None
    llm_provider: str | None
    latency_ms: int | None
    was_red_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetail(SessionOut):
    messages: list[MessageOut]
