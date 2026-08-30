"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, protected
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.redis_client import close_redis
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Health Symptom-Checker API",
    description="Grounded RAG assistant. Informational only — not medical advice.",
    version="0.1.0",
    lifespan=lifespan,
)

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
