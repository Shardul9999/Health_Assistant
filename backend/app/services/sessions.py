"""Session ownership and history (§4).

Every read and write checks clerk_user_id. A session belonging to another user
returns 404, not 403: telling a stranger that a session id exists but is not
theirs is itself a small leak.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFound
from app.db.models import Message, Session


async def get_owned_session(
    db: AsyncSession, session_id: uuid.UUID, user_id: str, with_messages: bool = False
) -> Session:
    stmt = select(Session).where(
        Session.id == session_id,
        Session.clerk_user_id == user_id,
        Session.deleted_at.is_(None),
    )
    if with_messages:
        stmt = stmt.options(selectinload(Session.messages))
    session = (await db.execute(stmt)).scalar_one_or_none()
    if session is None:
        raise NotFound("Session not found.")
    return session


async def list_sessions(db: AsyncSession, user_id: str) -> list[Session]:
    stmt = (
        select(Session)
        .where(Session.clerk_user_id == user_id, Session.deleted_at.is_(None))
        .order_by(Session.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars())


async def list_messages(db: AsyncSession, session_id: uuid.UUID, user_id: str) -> list[Message]:
    await get_owned_session(db, session_id, user_id)
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars())
