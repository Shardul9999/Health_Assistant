"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth import AuthedUser, verify_token
from app.core.exceptions import Unauthorized
from app.core.logging import user_id_var

# auto_error=False so a missing header raises our own Unauthorized (401 with the
# documented {"code": "UNAUTHORIZED"} body) rather than FastAPI's 403 default.
_bearer = HTTPBearer(auto_error=False)


async def current_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthedUser:
    if creds is None or not creds.credentials:
        raise Unauthorized()
    user = verify_token(creds.credentials)
    # Bind onto the log context so lines emitted while handling this request -
    # retriever, LLM client - are attributable.
    user_id_var.set(user.user_id)
    # Also stash it on request.state: Starlette runs the endpoint in a separate
    # task from BaseHTTPMiddleware, so a ContextVar set here does not propagate
    # back up to the middleware's summary log line. request.state does.
    request.state.user_id = user.user_id
    return user


CurrentUser = Annotated[AuthedUser, Depends(current_user)]
