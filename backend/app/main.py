"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health, protected, sessions
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestContextMiddleware, configure_logging, get_logger
from app.core.redis_client import close_redis
from app.db.session import engine

# Configured before anything else so import-time and startup logs are formatted.
configure_logging(json_logs=settings.json_logs, level=settings.log_level)
log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "startup",
        environment=settings.environment,
        embedding_model=settings.embedding_model,
        groq_model=settings.groq_model,
        gemini_model=settings.gemini_model,
        allowed_origins=settings.cors_origins,
    )
    yield
    log.info("shutdown")
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Health Symptom-Checker API",
    description="Grounded RAG assistant. Informational only — not medical advice.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(protected.router)
app.include_router(chat.router)
app.include_router(sessions.router)
