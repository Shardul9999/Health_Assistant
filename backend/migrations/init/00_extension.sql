-- Runs automatically on first container boot, before Alembic migrations.
-- Place at: backend/migrations/init/00_extension.sql
-- The pgvector/pgvector image ships the extension binary; this enables it in the DB.

CREATE EXTENSION IF NOT EXISTS vector;
