#!/usr/bin/env python3
"""Mint a short-lived Clerk session token for local API testing.

    TOKEN=$(python scripts/dev_token.py)
    curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/me

Clerk session tokens expire after about 60 seconds, so mint a fresh one per test
run rather than saving it. Requires CLERK_SECRET_KEY and at least one user in the
Clerk instance - sign up once through the frontend if there are none.

Local development only. This uses the Clerk Backend API to create a session
without a password, which is fine against a test instance and must never be
wired into anything user-facing.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import httpx  # noqa: E402

from app.config import settings  # noqa: E402

API = "https://api.clerk.com/v1"


async def mint(user_id: str | None = None) -> str:
    if not settings.clerk_secret_key:
        raise SystemExit("CLERK_SECRET_KEY is not set - see backend/.env.example")

    headers = {"Authorization": f"Bearer {settings.clerk_secret_key}"}
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        if user_id is None:
            r = await client.get(f"{API}/users?limit=1")
            r.raise_for_status()
            users = r.json()
            if not users:
                raise SystemExit(
                    "No users in the Clerk instance. Sign up once via the frontend first."
                )
            user_id = users[0]["id"]

        r = await client.post(f"{API}/sessions", json={"user_id": user_id})
        if r.status_code not in (200, 201):
            raise SystemExit(f"could not create session: HTTP {r.status_code} {r.text[:200]}")
        session_id = r.json()["id"]

        r = await client.post(f"{API}/sessions/{session_id}/tokens", json={})
        if r.status_code not in (200, 201):
            raise SystemExit(f"could not mint token: HTTP {r.status_code} {r.text[:200]}")
        return r.json()["jwt"]


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    print(asyncio.run(mint(arg)))
