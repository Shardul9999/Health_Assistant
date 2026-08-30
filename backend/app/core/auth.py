"""Clerk JWT verification.

Clerk signs session tokens with RS256 and publishes the public keys at the
instance's JWKS endpoint. We verify the signature and the standard time claims;
the subject (`sub`) is the Clerk user id used everywhere else as the ownership key.

No secret key is needed for verification — CLERK_SECRET_KEY is only required for
Clerk's backend REST API, which this phase does not call.
"""

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from app.config import settings
from app.core.exceptions import Unauthorized

# PyJWKClient caches fetched keys in-process and refetches on an unknown kid,
# so key rotation is handled without a restart.
_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if not settings.clerk_jwks_url:
        raise Unauthorized("Auth is not configured on this server.")
    if _jwk_client is None:
        _jwk_client = PyJWKClient(settings.clerk_jwks_url, cache_keys=True)
    return _jwk_client


@dataclass(frozen=True)
class AuthedUser:
    user_id: str  # Clerk `sub` — the value stored in sessions.clerk_user_id
    session_id: str | None
    claims: dict


def verify_token(token: str) -> AuthedUser:
    """Verify a Clerk session JWT. Raises Unauthorized on any failure."""
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            # Clerk session tokens carry no `aud` by default.
            options={"verify_aud": False, "require": ["exp", "sub"]},
            leeway=5,  # tolerate small clock skew between Clerk and this host
        )
    except Unauthorized:
        raise
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Session expired. Please sign in again.") from None
    except Exception:
        # Deliberately opaque: never echo JWT internals or key material back.
        raise Unauthorized("Invalid authentication token.") from None

    return AuthedUser(
        user_id=claims["sub"],
        session_id=claims.get("sid"),
        claims=claims,
    )
