"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth import AuthedUser, verify_token
from app.core.exceptions import Unauthorized

# auto_error=False so a missing header raises our own Unauthorized (401 with the
# documented {"code": "UNAUTHORIZED"} body) rather than FastAPI's 403 default.
_bearer = HTTPBearer(auto_error=False)


async def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthedUser:
    if creds is None or not creds.credentials:
        raise Unauthorized()
    return verify_token(creds.credentials)


CurrentUser = Annotated[AuthedUser, Depends(current_user)]
