# Demo Script

Six beats, about seven minutes. Rehearse it end to end at least twice — including the
setup — because the failure mode in a live demo is never the software, it is fumbling
a terminal while people watch.

---

## Setup (do this 15 minutes before, not in front of anyone)

The demo runs against the deployed app. Nothing needs to be started locally.

- **App:** https://health-assistant-lake.vercel.app
- **Health:** https://health-assistant-api-3aoy.onrender.com/health

**Wake the backend first.** Render's free tier sleeps after 15 minutes idle and takes
30-60 seconds to wake. Open the health URL and wait for it to return before you present:

```
{"status":"ok","database":{"reachable":true,"pgvector":true},"redis":{"reachable":true}}
```

If you skip this, beat 2 stalls for a minute in front of the room and looks broken. Keep
that tab open and reload it if there is a long gap before you start.

- Sign in **beforehand** so the demo starts on the chat screen, and click **New chat**.
- Browser zoom to ~125%. The citation panel text is small.
- Have `docs/BENCHMARKS.md` open in a second tab.
- Rate-limit windows expire on their own after 60 seconds, so nothing needs clearing -
  just avoid running beat 6 twice in quick succession.
- **Record a backup video of the whole run.** Venue wifi fails; the frontend, backend,
  database and both LLM providers are all remote.

Local dev still works if you would rather demo offline - `docker compose up -d`, then
uvicorn and `npm run dev` as in the README. The deployed app is the better story.

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
> question was embedded and searched against a vector store of 168 passages from WHO, NHS,
> NIH and CDC documents. Only the passages that scored above a similarity threshold were
> put in front of the model."

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

> "Notice it did not stream. The previous answer arrived word by word over several
> seconds; this one was simply there. That's not caching — it's the shape of the pipeline.
> Red-flag detection runs on the raw message before embedding, before retrieval, before the
> model. Nothing downstream executed."

The escalation banner deliberately shows no latency or provider footer — it is an
emergency notice, not a performance readout. If someone asks for the number, the
short-circuit measures sub-millisecond in isolation and about 20 ms over HTTP locally;
`docs/BENCHMARKS.md` has the measured figures. Quote it from there rather than from the
screen.

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

**Option B (live, riskier).** Before the demo, change `GROQ_API_KEY` to a bad value in the
Render dashboard and wait for the restart, roughly a minute. Ask a question — the answer
arrives normally and the footer reads `served by gemini`. Remember to change it back
afterwards; there is no local file to revert.

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

> "50 licence-checked documents, 168 passages, and every answer traceable to one of them.
> The system's most important behaviour is what it refuses to do: it won't answer without
> a source, and it won't try to assess an emergency."

---

## What it can and cannot answer

Three behaviours, and it is worth knowing which is which before someone in the room asks
to try one. Measured against the deployed corpus, not assumed.

### Answers — the 50 documents

| Area | Topics |
|---|---|
| Infectious disease | dengue, malaria, tuberculosis, typhoid, flu, hepatitis B, diarrhoeal disease |
| Chronic conditions | diabetes, high blood pressure, asthma, anaemia, cardiovascular disease, obesity |
| Everyday symptoms | fever (adults and children), cough, sore throat, headache, migraine, dizziness, tiredness, insomnia, back pain, constipation, acid reflux, dehydration, diarrhoea and vomiting, rashes in children |
| Emergency explainers | stroke signs, heart attack symptoms, heat illness, food poisoning |
| Prevention | handwashing, immunisation, physical activity, tobacco, food safety, antibiotic use, eye health |
| Mental health | depression, mental disorders |
| Other | snakebite, sleep deprivation |

Safe to offer if someone asks for a question of their own choosing: dengue, tuberculosis,
typhoid, asthma, diabetes, migraine, back pain.

### Refuses — verified by retrieval, not guessed

**COVID-19** is the one an evaluator is most likely to try. Also cancer, UTI, kidney
stones, acne, burns, thyroid, arthritis, HIV, period pain, appendicitis, broken bones,
hair loss, pregnancy, COPD, panic attack.

Also seizure, anaphylaxis and choking *as questions* — see the asymmetry below.

### Escalates — before retrieval, no LLM call

Nine categories: cardiac, breathing, stroke, bleeding, head injury, loss of
consciousness, anaphylaxis, seizure, self-harm.

These fire on the raw message whatever the corpus holds, which produces a deliberate
asymmetry worth naming if it comes up: *"I am having a seizure"* escalates instantly,
while *"what is a seizure"* refuses. The matcher covers the emergency; the corpus does
not cover the explanation. Safe either way, and honest about the gap.

### Three questions to avoid on stage

They clear the 0.65 floor on a tangential match, so the answer is thin rather than wrong:

| Question | Top similarity | Matches |
|---|---|---|
| "my child has an ear infection" | 0.660 | *About Antibiotic Prescribing and Use* |
| "how much water should I drink" | 0.656 | *Dehydration* |
| "what causes allergies" | 0.675 | *Asthma* |

### If someone asks about COVID

Do not treat it as a gap you forgot. It is a scope decision, and it is the same argument
as beat 3:

> "The corpus is a fixed, licence-checked snapshot, deliberately frozen so that answers
> cannot silently change under us. COVID guidance moves faster than a frozen corpus can
> track, so including it would mean citing sources that may already be out of date. It
> refuses instead. That is the system working, not failing."

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

**"Why is the corpus only 50 documents?"**
Because every one of them is licence-checked — WHO, CDC, NIH and NHS only, with the
attribution each licence requires. Breadth was traded for provenance: the system refuses
more questions than it answers, which is the correct failure for a health tool. Eight of
the fifty sit behind bot protection and had to be saved from a browser by hand, so the
corpus is deliberately a frozen snapshot rather than a live crawl.

**"How do you know the red-flag detection actually works?"**
98 unit tests covering every category plus near-miss phrasings — "my chest feels tight",
third-person, misspelled, buried mid-sentence. Offer to run `pytest tests/test_red_flags.py`
live; it takes under a second.

**"Isn't the LLM still the weak link?"**
Yes, and that's why it's constrained on both sides: it never sees a red-flag message, and
it's never called without retrieved context. It can only paraphrase passages it was handed.

---

## If something breaks

Open the health URL first; it tells you which piece is down instead of leaving you to
guess: https://health-assistant-api-3aoy.onrender.com/health

| Symptom | Fix |
|---|---|
| First message hangs ~1 minute | Render woke from sleep. It is not broken — wait, then carry on. Load the health URL before you present to avoid this. |
| Frontend loads, chat fails immediately | Check the health URL. If it is fine, this is CORS — `ALLOWED_ORIGINS` on Render must be the Vercel origin, `https://` included, no trailing slash. |
| `database: reachable: false` | Neon is down or the connection string changed. Nothing you can fix mid-demo — switch to the recording. |
| `redis: reachable: false` | Upstash is unreachable. The app still works; only the rate limit is off, so skip beat 6 and say so. |
| Everything returns 429 | You ran beat 6 too recently. The window clears itself after 60 seconds. |
| Answers refuse everything | Retrieval is finding nothing — check the health URL for the database. If that is green, you are asking off-corpus questions; see the section above. |
| 401 on every request | Session expired. Sign out and back in. |
| Total wifi failure | Play the backup recording. Everything is remote now — frontend, backend, database, both model providers. This is why you made one. |
