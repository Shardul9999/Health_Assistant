# Corpus Sourcing & Licensing Notes

Companion to `corpus_manifest.json` (50 sources) and `verify_corpus.py`.

---

## Correction to the earlier project plan

**The earlier plan listed MedlinePlus as a safe source. Remove it.**

MedlinePlus is a mix of public-domain and licensed third-party content. Its consumer health encyclopedia comes from A.D.A.M. Inc. and its drug pages from AHFS (American Society of Health-System Pharmacists) — both copyrighted, neither redistributable.

The specific problem: MedlinePlus's own terms state that you may not ingest their copyrighted content into an EHR, patient portal, or other health IT system without licensing it directly from the vendor. A RAG chatbot that embeds their text into a vector database is squarely the kind of system that language is written to cover.

Public-domain areas of MedlinePlus do exist (MedlinePlus Genetics pages, and NLM-produced material), but the encyclopedia pages you'd actually want for a symptom checker are not among them. Not worth the ambiguity — the four sources below cover the same ground with clean terms.

---

## The four sources, and what each is for

| Source                                               | Licence                         | Commercial use | Best for                                                          |
| ---------------------------------------------------- | ------------------------------- | -------------- | ----------------------------------------------------------------- |
| **WHO** fact sheets                                  | CC BY-NC-SA 3.0 IGO             | No             | Global disease overviews, epidemiology, prevention                |
| **CDC**                                              | Public domain (US federal work) | Yes            | Emergency symptom recognition, clinical detail                    |
| **NIH institutes** (NHLBI, NIDDK, NINDS, NIAMS, NEI) | Public domain (US federal work) | Yes            | Condition deep-dives, symptoms and causes                         |
| **NHS** Health A–Z                                   | Open Government Licence v3.0    | Yes            | Plain-language symptom pages — the best reading level of the four |

### WHO — the one with real conditions attached

WHO material is CC BY-NC-SA 3.0 IGO. Three obligations that actually bind you:

1. **Attribution**, in this form: _"[Title]. Geneva: World Health Organization; [Year]. Licence: CC BY-NC-SA 3.0 IGO."_
2. **Non-commercial only.** Fine for a college project. If you ever put this behind a paywall or run ads, the WHO portion has to come out.
3. **ShareAlike.** Adaptations must carry the same or an equivalent licence.

Also: don't use the WHO logo, and don't phrase anything so it implies WHO endorses your app. Your citation UI should read "Source: World Health Organization", never "Verified by WHO".

Whether embedding text into a vector store counts as an "adaptation" triggering ShareAlike is genuinely untested. For an academic project it doesn't matter much, but it's a reason to keep WHO content clearly attributed and separable rather than blended into a single undifferentiated index.

### CDC and NIH — the cleanest option

US federal government works aren't copyrighted under US law. Reproduce and redistribute freely. Attribution is good practice, not a legal requirement.

One caveat: federal sites occasionally host third-party material (a licensed image, a chart from a journal). Text pages are almost always fine; if something is visibly credited to an outside organisation, skip it.

**This is why 18 of the 50 sources are CDC/NIH.** If you have to cut the corpus for time, cut WHO before CDC/NIH — fewer strings.

### NHS — best writing, easiest licence

OGL v3.0 permits commercial and non-commercial reuse with attribution and a link to the licence. Attribution: _"Contains public sector information licensed under the Open Government Licence v3.0."_

NHS Health A–Z is written at roughly a 9th-grade reading level, well below WHO and CDC. For a symptom checker where users are anxious and want a plain answer, these are your best retrieval targets. Twelve are in the manifest; add more if you want.

---

## The 403 problem

`verify_corpus.py` will report HTTP 403 on most of these. **That does not mean the URL is dead** — who.int, cdc.gov, and nhs.uk all block automated requests by default.

For a 50-document corpus, the honest answer is: open each in a browser, save the page, drop it in `data/raw/`. It's one afternoon of work, it sidesteps the bot-blocking entirely, and it gives you a frozen snapshot — which is better for a project you'll demo in December anyway, since a fact sheet that gets rewritten in October won't silently change your answers.

If you'd rather automate it: WHO publishes PDF versions of much of its material through IRIS (`apps.who.int/iris`), which is friendlier to programmatic access. Respect robots.txt and rate limits either way.

---

## Coverage

50 sources: 24 priority-1, 16 priority-2, 10 priority-3. Ingest priority 1 first — that alone (24 docs) is enough for a working demo.

| Category           | Count |
| ------------------ | ----- |
| Common illness     | 16    |
| Chronic condition  | 9     |
| Infectious disease | 7     |
| Prevention         | 6     |
| Emergency          | 4     |
| General wellbeing  | 4     |
| Nutrition          | 2     |
| Mental health      | 2     |

**India-relevant inclusions**: dengue, malaria, tuberculosis, typhoid, snakebite envenoming, heat-related illness. These make the project feel locally grounded rather than transplanted, and evaluators tend to notice.

---

## Three handling rules the corpus imposes

### 1. Mental-health content is context, not an answer path

Two WHO mental-health fact sheets are in the manifest. They exist so the system has vocabulary, not so it can respond to someone in distress via RAG.

Any query touching self-harm, suicidal ideation, or acute crisis must short-circuit to the fixed Tele-MANAS (14416) escalation response — same mechanism as chest pain. Never retrieve, never generate, never ask assessment questions. A fluent, well-cited, on-topic paragraph is the wrong output here, and the fact that it reads well makes it more dangerous rather than less.

### 2. The obesity fact sheet needs a guardrail

WHO's obesity fact sheet contains BMI thresholds and weight categories. Retrieved and rendered plainly, that's a route to the system handing someone numeric weight targets on request.

Rule: no specific calorie targets, no goal weights, no numeric diet or exercise prescriptions, regardless of how the question is phrased. If a query pushes toward restriction, weight goals, or fasting limits, the system explains generally and points to a professional — it does not produce numbers. Consider dropping this source entirely for v1; it's priority 2 for a reason.

### 3. GERD vs cardiac chest pain — do not let the model adjudicate

The NIDDK acid reflux page describes chest discomfort that overlaps with cardiac symptoms. This is exactly the distinction a retrieval system must never attempt.

Chest pain escalates. Every time. Even when reflux is the far more likely explanation, even when the user says they know it's just heartburn. The cost asymmetry is total: an unnecessary "please seek care" is a minor annoyance; a missed cardiac event is not recoverable. Make sure the red-flag layer runs before retrieval so this content can never reach the model on a chest-pain query.

---

## Files

- `corpus_manifest.json` — 50 sources with id, title, org, licence, URL, category, priority
- `verify_corpus.py` — URL checker; run before ingestion, `--priority 1` to check the core set
- `CORPUS_NOTES.md` — this file

Point your ingestion script at the manifest and have it write `licence` and `source_url` into the `documents` table for every row. If anyone asks during evaluation where your medical data came from, that table is your answer.
