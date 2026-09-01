"""Structured logging with request IDs (§9).

Every log line is JSON in production and human-readable in development, and every
line emitted while handling a request carries that request's id. Without the id,
a 503 in a log file is unattributable: you cannot tell which of the interleaved
concurrent requests it belonged to, which is exactly when you need to.

The id is held in a ContextVar rather than passed around, so it reaches the
retriever and the LLM client without threading a parameter through every call.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")

REQUEST_ID_HEADER = "X-Request-ID"


def _add_context(_logger, _name, event_dict):
    """Attach the ambient request id and user to every event."""
    event_dict["request_id"] = request_id_var.get()
    user = user_id_var.get()
    if user != "-":
        event_dict["user_id"] = user
    return event_dict


def configure_logging(json_logs: bool = False, level: str = "INFO") -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        _add_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, our own modules) through the
    # same renderer so the output is one consistent stream.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=(
                structlog.processors.JSONRenderer()
                if json_logs
                else structlog.dev.ConsoleRenderer(colors=False)
            ),
            foreign_pre_chain=[
                _add_context,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
            ],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Access logs would duplicate the request/response pair we emit ourselves.
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str | None = None):
    return structlog.get_logger(name)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, logs the request/response pair, echoes the header.

    An inbound X-Request-ID is honoured so a trace survives a proxy hop in
    Phase 4's deployment; otherwise one is generated.
    """

    def __init__(self, app, logger=None):
        super().__init__(app)
        self._log = logger or structlog.get_logger("http")

    async def dispatch(self, request: Request, call_next):
        import time

        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self._log.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            request_id_var.reset(token)
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        # /health is polled constantly; logging it at info level buries
        # everything else.
        if request.url.path != "/health":
            # Set by the auth dependency. Read from request.state rather than the
            # ContextVar because the endpoint ran in a different task.
            user = getattr(request.state, "user_id", None)
            self._log.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
                **({"user_id": user} if user else {}),
            )
        response.headers[REQUEST_ID_HEADER] = request_id
        request_id_var.reset(token)
        return response
