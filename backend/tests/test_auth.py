"""Auth boundary (§10): no token -> 401, bad token -> 401, never a 500."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_protected_route_rejects_missing_token(client):
    res = client.get("/api/me")
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


def test_protected_route_rejects_malformed_token(client):
    res = client.get("/api/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


def test_protected_route_rejects_wrong_scheme(client):
    res = client.get("/api/me", headers={"Authorization": "Basic abc123"})
    assert res.status_code == 401


def test_error_body_leaks_nothing(client):
    """§7: no provider names, key material, or stack traces in client errors."""
    body = res_text = client.get(
        "/api/me", headers={"Authorization": "Bearer not.a.jwt"}
    ).text.lower()
    for leak in ("traceback", "jwks", "clerk_secret", "sk_", "gsk_", "aiza"):
        assert leak not in body, f"error response leaked {leak!r}"
    assert set(client.get("/api/me").json()) == {"code", "message"}
    assert res_text


# --------------------------------------------------------------------------- ownership

import uuid  # noqa: E402

from app.core.exceptions import NotFound  # noqa: E402
from app.db.models import Message, Session  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services.sessions import (  # noqa: E402
    get_owned_session,
    list_messages,
    list_sessions,
)


@pytest.fixture
async def db():
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except Exception:
        pytest.skip("Postgres unavailable - run `docker compose up -d`")


@pytest.fixture
async def owned_session(db):
    """A session belonging to user A, with one message."""
    owner = f"user_a_{uuid.uuid4().hex[:10]}"
    session = Session(clerk_user_id=owner, title="Test conversation")
    db.add(session)
    await db.flush()
    db.add(Message(session_id=session.id, role="user", content="what is anaemia"))
    await db.commit()
    yield owner, session.id
    await db.delete(await db.get(Session, session.id))
    await db.commit()


async def test_owner_can_read_their_session(db, owned_session):
    owner, session_id = owned_session
    assert (await get_owned_session(db, session_id, owner)).id == session_id


async def test_another_users_session_is_not_found(db, owned_session):
    """§4: 404, not 403 - confirming the id exists is itself a small leak."""
    _, session_id = owned_session
    with pytest.raises(NotFound):
        await get_owned_session(db, session_id, f"user_b_{uuid.uuid4().hex[:10]}")


async def test_another_user_cannot_read_the_messages(db, owned_session):
    _, session_id = owned_session
    with pytest.raises(NotFound):
        await list_messages(db, session_id, f"user_b_{uuid.uuid4().hex[:10]}")


async def test_listing_is_scoped_to_the_caller(db, owned_session):
    owner, session_id = owned_session
    assert session_id in {s.id for s in await list_sessions(db, owner)}
    assert await list_sessions(db, f"user_b_{uuid.uuid4().hex[:10]}") == []


async def test_soft_deleted_sessions_are_hidden_from_their_owner(db, owned_session):
    from datetime import datetime, timezone

    owner, session_id = owned_session
    session = await get_owned_session(db, session_id, owner)
    session.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    with pytest.raises(NotFound):
        await get_owned_session(db, session_id, owner)
    assert session_id not in {s.id for s in await list_sessions(db, owner)}


async def test_a_nonexistent_session_is_not_found(db):
    with pytest.raises(NotFound):
        await get_owned_session(db, uuid.uuid4(), "user_whoever")
