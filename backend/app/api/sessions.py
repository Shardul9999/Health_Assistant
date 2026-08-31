"""Session history endpoints (§4)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import CurrentUser
from app.schemas.chat import MessageOut, SessionOut
from app.services.sessions import get_owned_session, list_messages, list_sessions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
async def get_sessions(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return await list_sessions(db, user.user_id)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
async def get_messages(
    session_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    return await list_messages(db, session_id, user.user_id)


@router.delete("/{session_id}", status_code=204, response_class=Response)
async def delete_session(
    session_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> Response:
    session = await get_owned_session(db, session_id, user.user_id)
    session.deleted_at = datetime.now(timezone.utc)  # soft delete
    await db.commit()
    return Response(status_code=204)
