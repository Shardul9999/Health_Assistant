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
