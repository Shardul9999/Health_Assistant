"""Custom exception types and their HTTP mapping.

Rule from §7: never leak provider names, keys, or stack traces to the client.
Every handler here returns a fixed shape: {"code": ..., "message": ...}.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base for errors that are safe to surface to a client."""

    code = "INTERNAL_ERROR"
    status_code = 500
    message = "Something went wrong."

    def __init__(self, message: str | None = None):
        self.message = message or self.message
        super().__init__(self.message)

    def payload(self) -> dict:
        return {"code": self.code, "message": self.message}


class Unauthorized(AppError):
    code = "UNAUTHORIZED"
    status_code = 401
    message = "Authentication required."


class NotFound(AppError):
    code = "NOT_FOUND"
    status_code = 404
    message = "Not found."


class RateLimited(AppError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many requests."

    def __init__(self, retry_after_s: int, message: str | None = None):
        self.retry_after_s = retry_after_s
        super().__init__(message)

    def payload(self) -> dict:
        return {**super().payload(), "retry_after_s": self.retry_after_s}


class LLMUnavailable(AppError):
    code = "LLM_UNAVAILABLE"
    status_code = 503
    message = "The assistant is temporarily unavailable. Please try again shortly."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {}
        if isinstance(exc, RateLimited):
            headers["Retry-After"] = str(exc.retry_after_s)
        return JSONResponse(status_code=exc.status_code, content=exc.payload(), headers=headers)
