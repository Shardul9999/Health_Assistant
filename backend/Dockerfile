# Backend image. Used for the Phase 4 deployment (Render/Railway); not needed for
# local dev, where uvicorn runs on the host against the compose Postgres/Redis.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Migrations run on boot so a fresh managed Postgres is schema-ready without a
# manual step; `alembic upgrade head` is idempotent and also issues
# CREATE EXTENSION IF NOT EXISTS vector, which the compose-only init SQL cannot
# do for a hosted database.
#
# $PORT is set by Render and Railway; 8000 is the local default.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
