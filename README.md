# AI-Powered Health Symptom-Checker

A grounded RAG assistant that answers health questions using **only** verified medical
reference material (WHO, NHS, NIH, CDC). Every answer is traceable to a retrieved source
chunk. The system never diagnoses — it explains, cites, and routes users toward
professional care when symptoms are serious.

> **Informational only.** Not medical advice, and not a substitute for professional
> diagnosis. In an emergency in India: **112**, ambulance **108**.

Build spec: [PROJECT_PLAN.md](PROJECT_PLAN.md).

**Docs:** [Design](docs/DESIGN.md) · [Benchmarks](docs/BENCHMARKS.md) · [Demo script](docs/DEMO.md)

---

## Live

| | |
|---|---|
| **App** | https://health-assistant-lake.vercel.app |
| **API health** | https://health-assistant-api-3aoy.onrender.com/health |

Frontend on Vercel, backend on Render (Docker), Postgres on Neon with pgvector, Redis on
Upstash. The backend sleeps after 15 minutes idle on Render's free tier, so the first
request after a quiet period takes 30-60 seconds. Load the health URL first if you are
about to demo it.

Sign-in uses a Clerk development instance, which shows a small development badge on the
sign-in screen. A production instance needs a domain with configurable DNS, which a
`vercel.app` subdomain is not.

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

Tests: `pytest` (add `-m "not live"` to skip the one test that calls Gemini).

## 4. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Sign in with Clerk, then ask a question. Frontend tests: `npm test`.

## 5. Ingesting a document

Source pages are fetched by hand into `data/raw/` (gitignored — see
[data/CORPUS_NOTES.md](data/CORPUS_NOTES.md) for why, and for the licensing rules that
govern each source). Metadata comes from `data/corpus_manifest.json`:

```bash
cd backend
python scripts/fetch_corpus.py                 # download what the manifest allows
python scripts/ingest.py --all                 # chunk + embed everything in data/raw/
python scripts/ingest.py --source ../data/raw/nhs-anaemia-iron.html --manifest-id nhs-anaemia-iron
```

`fetch_corpus.py` prints anything it could not download. **8 CDC pages cannot be fetched
automatically** — bot protection returns 403 even for `robots.txt`, so their crawl policy
cannot be read. Save those from a browser and re-run `ingest.py --all`; the script lists the
exact ids and URLs. `data/raw/` is gitignored, so a fresh clone has to repeat this step.

### Saving a page by hand

1. Open the URL in a normal browser tab and check the article is actually readable —
   if you see a CAPTCHA or "Access Denied", saving it captures the block page, not the
   article. The ingester detects this and says so, but it wastes a round trip.
2. `Ctrl+S`. Any format works: **Webpage, Single File (`.mhtml`)** is the simplest,
   since it is one file with no sibling folder. `.html` is equally fine.
3. Rename the file to the **manifest id**, keeping the extension —
   `data/raw/cdc-stroke-signs.mhtml`. Browsers name the file after the page title, so
   this step is always needed. `ingest.py --all` lists any file in `data/raw/` whose
   name matches no manifest id, so a forgotten rename is visible rather than silent.
4. `python scripts/ingest.py --all`.

Accepted: `.html`, `.htm`, `.xhtml`, `.mhtml`, `.mht`, `.pdf`, `.txt`, `.md`. Format is
detected from the file contents, so a wrong extension is not fatal. If a page refuses to
extract, the error names the likely cause; as a last resort, copy the article text into
`data/raw/<manifest-id>.txt`, which always works.

Ingestion is idempotent — the cleaned text is hashed, and re-running on unchanged source
is a no-op. Use `--force` to replace a document and its chunks.

Confirm what landed:

```bash
docker exec health_db psql -U health -d health_assistant \
  -c "SELECT d.title, d.source_org, d.license, count(c.id) AS chunks
      FROM documents d LEFT JOIN chunks c ON c.document_id = d.id GROUP BY d.id;"
```

---

## Deploying (Phase 4)

Already deployed - see [Live](#live) above. Local dev needs no cloud accounts beyond the
three API keys. To deploy your own copy:

1. **Postgres with pgvector** - Neon or Railway both provide it. The Docker image's
   start command runs `alembic upgrade head`, which enables the extension and creates
   the schema, so no manual SQL is needed. **Rewrite the connection string**: the app
   uses asyncpg, so it must read `postgresql+asyncpg://...` with the query string
   removed - SQLAlchemy passes unknown params straight to asyncpg as keyword arguments
   and `sslmode=` is not one it accepts. TLS still happens; asyncpg defaults to
   `prefer`. On Neon, take the **direct** endpoint, not the one with `-pooler` in the
   host: that is PgBouncer in transaction mode, which breaks asyncpg's prepared
   statements intermittently.
2. **Redis** - any managed instance. Upstash works and is free; take the **Redis
   protocol** URL, not the REST endpoint, and note it is `rediss://` (TLS). A REST URL
   here surfaces as `redis: reachable: false` with a `ValueError` on `/health`.
3. **Backend** - [`render.yaml`](render.yaml) is a Render blueprint. Set every
   `sync: false` variable in the dashboard. Set `ENVIRONMENT=production` to switch
   logs to JSON, and put the deployed frontend origin in `ALLOWED_ORIGINS`.
4. **Frontend** - [`frontend/vercel.json`](frontend/vercel.json) is ready for Vercel.
   **Set Root Directory to `frontend`**, or Vercel scans the repo root, finds
   `backend/requirements.txt` and tries to build a Python project. Set
   `VITE_CLERK_PUBLISHABLE_KEY` and point `VITE_API_BASE_URL` at the deployed API. Turn
   **Deployment Protection** off under Settings, or every visitor gets a Vercel login
   page. Use the production domain from Settings -> Domains in `ALLOWED_ORIGINS`, not a
   per-deployment URL - those carry a hash that changes on every push.
5. **Re-ingest the corpus** against the hosted database - `data/raw/` is gitignored, so
   run `python scripts/ingest.py --all` with `DATABASE_URL` pointed at production.

CORS is driven entirely by `ALLOWED_ORIGINS`; a missing origin there is the usual cause
of a frontend that loads but cannot talk to the API.

## Benchmarks

```bash
cd backend
python scripts/benchmark.py            # writes docs/BENCHMARKS.md
python scripts/benchmark.py --limit 10 # quick sample
```

Paced by default to stay inside Groq's free-tier token budget. See
[docs/BENCHMARKS.md](docs/BENCHMARKS.md) for the current numbers and their caveats.

## Layout

```
backend/    FastAPI service — auth, RAG, safety, persistence
frontend/   Vite + React 18 + TypeScript SPA
data/       Corpus manifest, licensing notes, raw/processed sources (gitignored)
docs/       Design doc, benchmarks, demo script
```

## Safety invariants

These are requirements, not polish. See §6 of the plan.

- Red-flag symptoms short-circuit the pipeline before retrieval — no LLM call.
- When retrieval finds nothing above the similarity floor, the assistant says so rather
  than answering from model knowledge.
- The disclaimer bar is always visible and not dismissible.
- User messages are data, never instructions.
