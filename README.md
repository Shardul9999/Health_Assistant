# AI-Powered Health Symptom-Checker

A grounded RAG assistant that answers health questions using **only** verified medical
reference material (WHO, CDC, NIH, NHS). Every answer is traceable to a retrieved source
chunk. The system never diagnoses — it explains, cites, and routes users toward
professional care when symptoms are serious.

> **Informational only.** Not medical advice, and not a substitute for professional
> diagnosis. In an emergency in India: **112**, ambulance **108**.

Build spec: [PROJECT_PLAN.md](PROJECT_PLAN.md). Current status: **Phase 1 (Foundations)**.

---

## Prerequisites

- Docker Desktop
- Python 3.11
- Node.js 20+

## 1. Accounts and keys

Three services need free-tier accounts. Postgres and Redis run locally in Docker and
need no account.

| Service | Where to get the key | Goes in |
|---|---|---|
| Clerk | [dashboard.clerk.com](https://dashboard.clerk.com) → your app → API Keys | Publishable key → `frontend/.env`; Secret key + JWKS URL → `backend/.env` |
| Groq | [console.groq.com/keys](https://console.groq.com/keys) | `backend/.env` |
| Google AI Studio (Gemini) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `backend/.env` |

```bash
cp backend/.env.example backend/.env      # then fill in the four secrets
cp frontend/.env.example frontend/.env    # then fill in the publishable key
```

`.env` files are gitignored. Never commit real values.

## 2. Local infrastructure

```bash
docker compose up -d
```

Brings up Postgres 16 with pgvector (port 5432) and Redis 7 (port 6379).
`backend/migrations/init/00_extension.sql` enables the `vector` extension on the
database's first boot.

Verify:

```bash
docker compose ps
docker exec health_db psql -U health -d health_assistant -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

## 3. Backend

```bash
cd backend
py -3.11 -m venv .venv                    # Windows;  python3.11 -m venv .venv elsewhere
.venv/Scripts/activate                    # source .venv/bin/activate elsewhere
pip install -r requirements.txt
alembic upgrade head                      # creates the four tables + HNSW index
uvicorn app.main:app --reload --port 8000
```

Check it:

```bash
curl http://localhost:8000/health
# {"status":"ok","database":{"reachable":true,"pgvector":true},"redis":{"reachable":true}}

curl -i http://localhost:8000/api/me
# 401 {"code":"UNAUTHORIZED","message":"Authentication required."}
```

Tests: `pytest`

## 4. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Sign in with Clerk; the page verifies your token against the backend and shows the live
Postgres/Redis status.

## 5. Ingesting a document

Source pages are fetched by hand into `data/raw/` (gitignored — see
[data/CORPUS_NOTES.md](data/CORPUS_NOTES.md) for why, and for the licensing rules that
govern each source). Metadata comes from `data/corpus_manifest.json`:

```bash
cd backend
python scripts/verify_corpus.py --manifest ../data/corpus_manifest.json --priority 1
python scripts/ingest.py --source ../data/raw/nhs-anaemia-iron.html --manifest-id nhs-anaemia-iron
```

Ingestion is idempotent — the cleaned text is hashed, and re-running on unchanged source
is a no-op. Use `--force` to replace a document and its chunks.

Confirm what landed:

```bash
docker exec health_db psql -U health -d health_assistant \
  -c "SELECT d.title, d.source_org, d.license, count(c.id) AS chunks
      FROM documents d LEFT JOIN chunks c ON c.document_id = d.id GROUP BY d.id;"
```

---

## Layout

```
backend/    FastAPI service — auth, RAG, safety, persistence
frontend/   Vite + React 18 + TypeScript SPA
data/       Corpus manifest, licensing notes, raw/processed sources (gitignored)
docs/       Design doc and benchmarks (Phase 4)
```

## Safety invariants

These are requirements, not polish. See §6 of the plan.

- Red-flag symptoms short-circuit the pipeline before retrieval — no LLM call.
- When retrieval finds nothing above the similarity floor, the assistant says so rather
  than answering from model knowledge.
- The disclaimer bar is always visible and not dismissible.
- User messages are data, never instructions.
