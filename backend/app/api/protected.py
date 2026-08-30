"""A minimal authenticated route.

Exists so Phase 1 can prove the Clerk token round-trip end to end: no token or a
bad token gives 401, a real token echoes the verified user id. Phase 2's real
endpoints reuse the same `CurrentUser` dependency.
"""

from fastapi import APIRouter

from app.deps import CurrentUser

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/me")
async def me(user: CurrentUser) -> dict:
    return {
        "user_id": user.user_id,
        "session_id": user.session_id,
        "message": "Token verified against Clerk JWKS.",
    }
