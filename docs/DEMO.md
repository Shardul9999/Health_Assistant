# Demo Script

Six beats, about seven minutes. Rehearse it end to end at least twice — including the
setup — because the failure mode in a live demo is never the software, it is fumbling
a terminal while people watch.

---

## Setup (do this 15 minutes before, not in front of anyone)

```bash
docker compose up -d                       # Docker Desktop must be running first
cd backend && .venv/Scripts/activate
uvicorn app.main:app --port 8000           # leave running
cd ../frontend && npm run dev              # leave running
```

Check before you walk in:

```bash
curl http://localhost:8000/health
# {"status":"ok","database":{"reachable":true,"pgvector":true},"redis":{"reachable":true}}

docker exec health_redis redis-cli FLUSHALL   # clear rate-limit windows
```

- Sign in **beforehand** so the demo starts on the chat screen, and click **New chat**.
- Browser zoom to ~125%. The citation panel text is small.
- Have `docs/BENCHMARKS.md` open in a second tab.
- **Record a backup video of the whole run.** Venue wifi fails; both LLM providers are
  remote.

---

## 1 · Sign in — 15 seconds

Sign out and back in once so they see the Clerk flow, then land on the chat screen.

> "Auth is Clerk. The backend verifies the session JWT against Clerk's JWKS on every
> request — it doesn't trust anything the browser tells it."

Don't linger. Nobody is impressed by a login form.

---

## 2 · A grounded answer — 90 seconds

Type: **"What causes iron deficiency anaemia?"**

Let it stream. While it does:

> "It's streaming over server-sent events. Before a single token was generated, the
> question was embedded and searched against a vector store of 153 passages from WHO, NHS
> and NIH documents. Only the passages that scored above a similarity threshold were put
> in front of the model."

When it finishes, point at the inline blue chips:

> "Every factual sentence carries the title of the source it came from."

Click **5 sources**.

> "Here are the actual passages, the organisation, the licence, and the similarity score.
> The links go to the original page. Nothing here came from the model's own knowledge."

Open one source link in a new tab. Land the point: **the answer is auditable.**

---

## 3 · Grounding proof — 60 seconds  ← *the important one*

Type: **"How do I fix my laptop keyboard?"**

> "It refuses. Not because someone wrote a rule about laptops — because retrieval returned
> nothing above the similarity floor, so the model was never called at all."

Then the sharper version. Type: **"What is the capital of France?"**

> "It knows this. Every model does. It still refuses, because the refusal isn't a decision
> the model makes — the pipeline structurally cannot reach it without retrieved context."

> "This is the whole argument of the project. A general chatbot answers everything, which
> means you can never tell which answers are grounded. This one can only answer from its
> sources, so every answer it gives you is."

If someone asks how you know it isn't just refusing everything — that's what beat 2 was
for. Offer to run any in-corpus question they like: dengue, tuberculosis, typhoid, asthma.

---

## 4 · Red flag — 90 seconds

Type: **"I have crushing chest pain radiating to my arm."**

The escalation appears near-instantly, as a red banner rather than a chat bubble.

> "Notice how fast that was. Around 20 milliseconds, against roughly 3 seconds for the
> previous answer. That's not caching — it's the shape of the pipeline. Red-flag detection
> runs on the raw message before embedding, before retrieval, before the model. Nothing
> downstream executed."

> "The response is fixed text written in advance. It names the concern, routes to 112 or
> an ambulance on 108, and stops. It doesn't speculate about causes and it asks no
> follow-up questions — asking 'how bad is it?' delays the call and implies the system can
> judge. It can't."

Then, if you have the time — and this is the line evaluators remember:

Type: **"I know it's just my acid reflux but my chest hurts."**

> "It escalates anyway. The corpus contains an NIH page on reflux that describes chest
> discomfort overlapping with cardiac symptoms — exactly the distinction a retrieval system
> must never try to make. The cost asymmetry is total: an unnecessary 'please get checked'
> is a minor annoyance, a missed cardiac event isn't recoverable. So chest pain escalates
> every time, even when the user is probably right."

Mention the mental-health path (Tele-MANAS 14416) rather than demonstrating it — reading a
self-harm escalation aloud to a room is a poor choice.

---

## 5 · Provider fallback — 45 seconds

Point at the small grey line under an earlier answer: `served by groq · 2729 ms`.

Two ways to show the fallback, easiest first:

**Option A (safe).** Open `docs/BENCHMARKS.md` at the provider-split table.

> "Every response records which provider served it. Groq is primary; Gemini is the
> fallback, and it's genuinely exercised — Groq's free tier is 8000 tokens a minute and a
> grounded query reserves about 4000, so under rapid questioning we fall back routinely.
> These numbers came from a real run."

**Option B (live, riskier).** Before the demo, set `GROQ_API_KEY` to a bad value and
restart the backend. Ask a question — the answer arrives normally and the footer reads
`served by gemini`.

> "Same answer, different vendor, no error shown to the user. If Groq fails mid-sentence
> the client discards the partial and re-renders from Gemini rather than splicing two half
> answers together."

Only do Option B if you have rehearsed the restart.

---

## 6 · Rate limit — 30 seconds

Send four or five short messages fast (`hello`, `hi`, `test`…).

> "10 requests a minute per user, as a sliding window in Redis. The countdown comes from
> the server, not a guess in the browser."

> "It's a single Lua script — trim, count, add, expire — because as separate round trips
> two concurrent requests can both see a count of nine and both get through. And it fails
> open: if Redis dies, requests are allowed. A rate limiter that takes down the app is
> worse than no rate limiter."

---

## Closing line

> "42 licence-checked documents, 153 passages, and every answer traceable to one of them.
> The system's most important behaviour is what it refuses to do: it won't answer without
> a source, and it won't try to assess an emergency."

---

## Questions you should expect

**"What if it cites a source that doesn't say that?"**
The citation is checked mechanically for every answer in the benchmark run — the bracketed
title must exactly match a chunk retrieval actually returned. That catches invented
sources. It does not verify the *claim* against the passage; that's an LLM-as-judge
evaluation and it's the honest next step.

**"Why not fine-tune a medical model?"**
Fine-tuning moves knowledge into weights, where it can't be cited or updated. This project's
requirement is traceability, which is a retrieval property, not a weights property. A
fine-tuned model that says the right thing still can't show you where it came from.

**"Could it replace a doctor / triage nurse?"**
No, and it's built so it can't drift toward that. No diagnosis, no dosages, no triage
questions, and emergencies are routed out of the system rather than handled inside it.

**"What happens with a symptom that isn't in the corpus?"**
The no-context refusal from beat 3. That's the designed behaviour, and offering to try one
live is a strong answer.

**"Why is the corpus only 42 documents?"**
Eight CDC pages are blocked by bot protection that 403s even `robots.txt`, so their crawl
policy can't be read and automating around it isn't appropriate. They need saving by hand.
Red-flag escalation is keyword-based and unaffected.

**"How do you know the red-flag detection actually works?"**
98 unit tests covering every category plus near-miss phrasings — "my chest feels tight",
third-person, misspelled, buried mid-sentence. Offer to run `pytest tests/test_red_flags.py`
live; it takes under a second.

**"Isn't the LLM still the weak link?"**
Yes, and that's why it's constrained on both sides: it never sees a red-flag message, and
it's never called without retrieved context. It can only paraphrase passages it was handed.

---

## If something breaks

| Symptom | Fix |
|---|---|
| Frontend loads, chat fails | Backend down. Check `curl localhost:8000/health` |
| `database: reachable: false` | `docker compose up -d`; Docker Desktop must be running |
| Everything returns 429 | `docker exec health_redis redis-cli FLUSHALL` |
| Answers refuse everything | Corpus not ingested — `python scripts/ingest.py --all` |
| 401 on every request | Clerk keys missing from `.env`, or the session expired — sign in again |
| Total wifi failure | Play the backup recording. This is why you made one. |
