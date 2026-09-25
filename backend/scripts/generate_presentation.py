#!/usr/bin/env python3
"""Generate the executive evaluation presentation for the AI Health Symptom-Checker.
Produces a 16:9 modern, professionally designed PowerPoint file with speaker notes,
including comprehensive database design, schema models, and API endpoints.
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def create_presentation(output_path=None):
    if output_path is None:
        output_path = PROJECT_ROOT / "docs" / "Health_Assistant_Evaluation.pptx"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette (Modern Executive Health Tech)
    COLOR_BG_DARK = RGBColor(15, 23, 42)        # Slate 900
    COLOR_BG_LIGHT = RGBColor(248, 250, 252)    # Slate 50
    COLOR_CARD_BG = RGBColor(255, 255, 255)     # Pure White
    COLOR_CARD_BORDER = RGBColor(226, 232, 240) # Slate 200
    COLOR_PRIMARY = RGBColor(2, 132, 199)       # Sky 600
    COLOR_SECONDARY = RGBColor(14, 116, 144)    # Cyan 700
    COLOR_ACCENT_RED = RGBColor(225, 29, 72)    # Rose 600 (Emergency)
    COLOR_ACCENT_GREEN = RGBColor(16, 185, 129) # Emerald 500 (Safety)
    COLOR_TEXT_DARK = RGBColor(30, 41, 59)      # Slate 800
    COLOR_TEXT_MUTED = RGBColor(100, 116, 139)  # Slate 500
    COLOR_TEXT_LIGHT = RGBColor(241, 245, 249)  # Slate 100

    def add_bg(slide, dark=False):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = COLOR_BG_DARK if dark else COLOR_BG_LIGHT
        shape.line.color.rgb = COLOR_BG_DARK if dark else COLOR_BG_LIGHT
        return shape

    def add_header(slide, title_text, category_text="HEALTH ASSISTANT · PROJECT EVALUATION"):
        tag_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_tag = tag_box.text_frame
        tf_tag.word_wrap = True
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = category_text.upper()
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = COLOR_PRIMARY

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.7))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_TEXT_DARK

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.5)
        return card

    def set_notes(slide, notes_text):
        notes_slide = slide.notes_slide
        text_frame = notes_slide.notes_text_frame
        text_frame.text = notes_text

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Theme)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    add_bg(s1, dark=True)

    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.2), Inches(2.2), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_PRIMARY
    bar.line.fill.background()

    tbox = s1.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(2.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "Grounded AI Health Assistant & Emergency Triage"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_TEXT_LIGHT

    p2 = tf1.add_paragraph()
    p2.text = "An Auditable Retrieval-Augmented Assistant with Rule-Based Emergency Escalation"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(148, 163, 184)
    p2.space_before = Pt(12)

    c1 = add_card(s1, Inches(0.8), Inches(4.3), Inches(3.6), Inches(2.2), bg_color=RGBColor(30, 41, 59), border_color=RGBColor(51, 65, 85))
    t1 = s1.shapes.add_textbox(Inches(1.0), Inches(4.5), Inches(3.2), Inches(1.8))
    tf_c1 = t1.text_frame
    tf_c1.word_wrap = True
    p = tf_c1.paragraphs[0]
    p.text = "UN SDG ALIGNMENT"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT_GREEN
    p_b = tf_c1.add_paragraph()
    p_b.text = "Goal 3: Good Health & Well-being\nTarget 3.8: Access to safe, verified health information without medical misinformation."
    p_b.font.size = Pt(12)
    p_b.font.color.rgb = COLOR_TEXT_LIGHT
    p_b.space_before = Pt(8)

    c2 = add_card(s1, Inches(4.8), Inches(4.3), Inches(3.6), Inches(2.2), bg_color=RGBColor(30, 41, 59), border_color=RGBColor(51, 65, 85))
    t2 = s1.shapes.add_textbox(Inches(5.0), Inches(4.5), Inches(3.2), Inches(1.8))
    tf_c2 = t2.text_frame
    tf_c2.word_wrap = True
    p = tf_c2.paragraphs[0]
    p.text = "CORE PARADIGM"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY
    p_b = tf_c2.add_paragraph()
    p_b.text = "Strict Negative Constraints\nRefuses to guess without verified sources. Bypasses AI in medical emergencies (< 20 ms short-circuit)."
    p_b.font.size = Pt(12)
    p_b.font.color.rgb = COLOR_TEXT_LIGHT
    p_b.space_before = Pt(8)

    c3 = add_card(s1, Inches(8.8), Inches(4.3), Inches(3.7), Inches(2.2), bg_color=RGBColor(30, 41, 59), border_color=RGBColor(51, 65, 85))
    t3 = s1.shapes.add_textbox(Inches(9.0), Inches(4.5), Inches(3.3), Inches(1.8))
    tf_c3 = t3.text_frame
    tf_c3.word_wrap = True
    p = tf_c3.paragraphs[0]
    p.text = "PROJECT EVALUATION"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(245, 158, 11)
    p_b = tf_c3.add_paragraph()
    p_b.text = "Date: September 26, 2026\nStatus: Full Stack Deployed & Running\nTech: FastAPI · PostgreSQL (pgvector) · React · Clerk"
    p_b.font.size = Pt(12)
    p_b.font.color.rgb = COLOR_TEXT_LIGHT
    p_b.space_before = Pt(8)

    set_notes(s1, "SPEAKER NOTES:\nGood morning evaluators. Today I am presenting our Grounded AI Health Assistant.\n"
                  "While general AI models like ChatGPT are fluent, fluent fabrication in medicine can be fatal. "
                  "Our system is designed around auditable medical provenance (WHO, NHS, NIH, CDC), strict negative "
                  "constraints, and sub-millisecond emergency short-circuiting.")

    # =========================================================================
    # SLIDE 2: Problem Statement & Motivation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_bg(s2)
    add_header(s2, "The Critical Problem: Fluent Fabrication in Healthcare AI")

    card_data = [
        ("1. The Danger of Fluent Fabrication", 
         "General LLMs are trained to always generate an answer. A confident, well-structured, completely fabricated paragraph about chest pain is more dangerous than an obvious typo because patients trust it blindly.",
         COLOR_ACCENT_RED, Inches(0.8)),
        ("2. Total Lack of Provenance",
         "Standard chatbots synthesize knowledge across unvetted internet forums (Reddit, WebMD, blogs). They cannot point to the legal document, paragraph, or clinical body behind a claim.",
         COLOR_SECONDARY, Inches(4.8)),
        ("3. Emergency Neglect",
         "General LLMs engage in conversational chit-chat ('I understand your chest hurts; have you tried resting?'). In acute crises (stroke, heart attack), every minute lost to AI generation can be fatal.",
         COLOR_ACCENT_RED, Inches(8.8)),
    ]

    for title, desc, border_col, left in card_data:
        add_card(s2, left, Inches(1.6), Inches(3.7), Inches(5.0), border_color=border_col)
        tb = s2.shapes.add_textbox(left + Inches(0.25), Inches(1.8), Inches(3.2), Inches(4.5))
        tf = tb.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(16)
        p_t.font.bold = True
        p_t.font.color.rgb = border_col
        
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(13)
        p_d.font.color.rgb = COLOR_TEXT_DARK
        p_d.space_before = Pt(14)

    set_notes(s2, "SPEAKER NOTES:\nEvaluators often ask why we don't just use standard chatbots. "
                  "The answer is cost asymmetry. In code, a 95% accurate model gives a compiler error. "
                  "In medicine, a 5% hallucination rate or a 3-second delay in acute cardiac arrest is catastrophic. "
                  "General chatbots lack provenance and fail to prioritize urgent triage.")

    # =========================================================================
    # SLIDE 3: System Philosophy & 4 Key Guardrails
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_bg(s3)
    add_header(s3, "System Philosophy: Four Architectural Guardrails")

    guardrails = [
        ("Guardrail 1: Explain, Never Diagnose",
         "The system only explains verified medical literature. It has no capability to diagnose, prescribe medications, or suggest dosages, preventing liability and clinical drift.",
         Inches(0.8), Inches(1.6)),
        ("Guardrail 2: 100% Auditable Provenance",
         "Every factual statement carries an inline citation chip linking directly to a specific passage in a published document from WHO, NHS, NIH, or CDC with its legal license.",
         Inches(6.8), Inches(1.6)),
        ("Guardrail 3: Structural Refusal (0.65 Cosine Floor)",
         "If retrieved document similarity is below 0.65, the system refuses to answer. The LLM is never called. This structurally prevents the model from hallucinating outside verified data.",
         Inches(0.8), Inches(4.3)),
        ("Guardrail 4: Emergency Short-Circuit (< 20 ms)",
         "Emergency symptoms (crushing chest pain, stroke, breathing failure) are caught by rule-based pre-filters on raw input, instantly routing to 112/108 without touching the LLM.",
         Inches(6.8), Inches(4.3)),
    ]

    for title, desc, left, top in guardrails:
        add_card(s3, left, top, Inches(5.7), Inches(2.4), border_color=COLOR_PRIMARY)
        tb = s3.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), Inches(5.2), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(15)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(13)
        p_d.font.color.rgb = COLOR_TEXT_DARK
        p_d.space_before = Pt(8)

    set_notes(s3, "SPEAKER NOTES:\nPoint out Guardrail 3 and 4 in detail.\n"
                  "Guardrail 3 is the negative constraint: if someone asks 'what is the capital of France', "
                  "it refuses because no medical chunk matches. That proves grounding.\n"
                  "Guardrail 4 guarantees deterministic response time for life-threatening emergencies.")

    # =========================================================================
    # SLIDE 4: Architecture & Pipeline Data Flow
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_bg(s4)
    add_header(s4, "System Architecture: End-to-End Pipeline")

    steps = [
        ("Step 1: Auth & Rate Limit", "Clerk JWT (RS256 JWKS)\nRedis Lua Sliding Window\n10 req/min per user (Fails open)", Inches(0.8)),
        ("Step 2: Red-Flag Triage", "In-Process Regex (< 1 ms)\nEmergency Match -> Fixed 112/108\n(No Embedding, No LLM)", Inches(3.2)),
        ("Step 3: Vector Search", "Gemini 768d Embeddings\nPostgres 16 + pgvector HNSW\nCosine similarity floor >= 0.65", Inches(5.6)),
        ("Step 4: Dual LLM Fallback", "Primary: Groq (Llama/GPT-OSS)\nFallback: Gemini 2.5 Flash\nZero broken streams on error", Inches(8.0)),
        ("Step 5: SSE Streaming UI", "React 18 + Vite + Tailwind\nServer-Sent Events streaming\nInteractive Citation Chips", Inches(10.4)),
    ]

    for title, desc, left in steps:
        add_card(s4, left, Inches(1.8), Inches(2.1), Inches(4.8), border_color=COLOR_SECONDARY)
        tb = s4.shapes.add_textbox(left + Inches(0.15), Inches(2.0), Inches(1.8), Inches(4.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_SECONDARY
        
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = COLOR_TEXT_DARK
        p_d.space_before = Pt(12)

    set_notes(s4, "SPEAKER NOTES:\nWalk through the 5 steps left to right.\n"
                  "Emphasize the pipeline ordering: Red-flag check happens before embedding. "
                  "Why? Because embedding takes 700 ms, whereas regex takes 0.1 ms. We do not waste 700 ms "
                  "when someone is having a heart attack.")

    # =========================================================================
    # SLIDE 5: Database Schema & Vector Indexing (NEW SLIDE)
    # =========================================================================
    s5_db = prs.slides.add_slide(blank_layout)
    add_bg(s5_db)
    add_header(s5_db, "Database Design: Relational Schema & pgvector HNSW Index", category_text="DATA ARCHITECTURE & PERSISTENCE")

    db_tables = [
        ("documents (Corpus Metadata)",
         "• id: UUID (Primary Key)\n"
         "• title: Text (Published article title)\n"
         "• source_url: Text (Original reference link)\n"
         "• source_org: Text (WHO | NHS | NIH | CDC)\n"
         "• license: Text (OGL-v3 | CC BY-NC-SA | Public)\n"
         "• content_hash: String(64) UNIQUE (SHA-256 for idempotent re-ingestion)\n"
         "• ingested_at: DateTime(timezone=True)",
         Inches(0.8), Inches(1.6), Inches(5.6), Inches(2.7)),

        ("chunks (Vector Store)",
         "• id: UUID (Primary Key)\n"
         "• document_id: UUID (FK -> documents.id CASCADE)\n"
         "• content: Text (Semantic chunk passage)\n"
         "• embedding: Vector(768) (Gemini 768-dim vector)\n"
         "• chunk_index: Integer (0-based chunk order)\n"
         "• token_count: Integer (~300 to ~650 tokens)\n"
         "★ INDEX: HNSW on embedding (vector_cosine_ops, m=16, ef_construction=64)",
         Inches(6.8), Inches(1.6), Inches(5.7), Inches(2.7)),

        ("sessions (User Chat Context)",
         "• id: UUID (Primary Key)\n"
         "• clerk_user_id: Text (Indexed, user scope)\n"
         "• title: Text (Auto-generated from query)\n"
         "• deleted_at: DateTime (Nullable, soft delete)\n"
         "• created_at: DateTime(timezone=True)",
         Inches(0.8), Inches(4.5), Inches(5.6), Inches(2.2)),

        ("messages (Audit Trail & Tracking)",
         "• id: UUID (Primary Key)\n"
         "• session_id: UUID (FK -> sessions.id CASCADE)\n"
         "• role: Text ('user' | 'assistant')\n"
         "• content: Text (Message body or response)\n"
         "• retrieved_chunk_ids: UUID[] (Audit trail)\n"
         "• llm_provider: Text ('groq' | 'gemini')\n"
         "• latency_ms: Integer | was_red_flag: Boolean",
         Inches(6.8), Inches(4.5), Inches(5.7), Inches(2.2)),
    ]

    for title, desc, left, top, width, height in db_tables:
        add_card(s5_db, left, top, width, height, border_color=COLOR_SECONDARY)
        tb = s5_db.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), height - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_SECONDARY
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10.5)
        p_d.font.color.rgb = COLOR_TEXT_DARK
        p_d.space_before = Pt(4)

    set_notes(s5_db, "SPEAKER NOTES:\nExplain the database design:\n"
                     "1. We run PostgreSQL 16 with the pgvector extension.\n"
                     "2. The chunks table contains 768-dimensional embeddings indexed using HNSW (Hierarchical Navigable Small World) "
                     "with vector_cosine_ops for ultra-fast nearest-neighbor search.\n"
                     "3. The messages table maintains full auditability by storing an array of retrieved_chunk_ids, provider name, "
                     "and latency_ms for every generated message.\n"
                     "4. Documents use SHA-256 content hashing to ensure idempotent ingestion.")

    # =========================================================================
    # SLIDE 6: API Architecture & Endpoints (NEW SLIDE)
    # =========================================================================
    s6_api = prs.slides.add_slide(blank_layout)
    add_bg(s6_api)
    add_header(s6_api, "API Architecture: REST & Server-Sent Events (SSE) Endpoints", category_text="FASTAPI SERVICE INTERFACE")

    # Table of Endpoints
    add_card(s6_api, Inches(0.8), Inches(1.6), Inches(11.7), Inches(3.2))
    tb_api = s6_api.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(11.3), Inches(3.0))
    tf_api = tb_api.text_frame
    tf_api.word_wrap = True

    p = tf_api.paragraphs[0]
    p.text = "CORE API SPECIFICATION"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    endpoints = [
        ("POST /api/chat/stream", "Bearer <JWT>", "{session_id, content}", "SSE stream with event types: token, citation, escalation, done"),
        ("GET  /api/sessions", "Bearer <JWT>", "None", "Returns 200 OK with list of active user chat sessions [SessionOut]"),
        ("GET  /api/sessions/{id}/messages", "Bearer <JWT>", "session_id", "Returns 200 OK with full conversation history & citation IDs [MessageOut]"),
        ("DELETE /api/sessions/{id}", "Bearer <JWT>", "session_id", "Soft-deletes session (sets deleted_at); returns 204 No Content"),
        ("GET  /api/me", "Bearer <JWT>", "None", "Returns 200 OK with authenticated Clerk user ID & email (401 if missing/invalid)"),
        ("GET  /health", "Public", "None", "Returns 200 OK: {status, database: {reachable, pgvector}, redis: {reachable}}"),
    ]

    for ep, auth, payload, desc in endpoints:
        p_ep = tf_api.add_paragraph()
        p_ep.text = f"• {ep}  [{auth}]"
        p_ep.font.size = Pt(11)
        p_ep.font.bold = True
        p_ep.font.color.rgb = COLOR_TEXT_DARK
        p_ep.space_before = Pt(4)
        
        p_det = tf_api.add_paragraph()
        p_det.text = f"   Payload: {payload}  ➔  {desc}"
        p_det.font.size = Pt(10)
        p_det.font.color.rgb = COLOR_TEXT_MUTED

    # Bottom Cards: Middleware & Streaming Protocol
    add_card(s6_api, Inches(0.8), Inches(5.0), Inches(5.6), Inches(1.9), border_color=COLOR_SECONDARY)
    tb_m = s6_api.shapes.add_textbox(Inches(1.0), Inches(5.1), Inches(5.2), Inches(1.7))
    tf_m = tb_m.text_frame
    tf_m.word_wrap = True
    p_mt = tf_m.paragraphs[0]
    p_mt.text = "Security & Middleware Layer"
    p_mt.font.size = Pt(13)
    p_mt.font.bold = True
    p_mt.font.color.rgb = COLOR_SECONDARY
    p_mb = tf_m.add_paragraph()
    p_mb.text = "• RequestContextMiddleware: Injects unique X-Request-ID across all logs.\n• Clerk JWKS Authenticator: Validates RS256 JWT tokens cryptographically.\n• Redis Sliding Window: Enforces 10 req/min rate limit per user."
    p_mb.font.size = Pt(11)
    p_mb.font.color.rgb = COLOR_TEXT_DARK
    p_mb.space_before = Pt(4)

    add_card(s6_api, Inches(6.8), Inches(5.0), Inches(5.7), Inches(1.9), border_color=COLOR_PRIMARY)
    tb_s = s6_api.shapes.add_textbox(Inches(7.0), Inches(5.1), Inches(5.3), Inches(1.7))
    tf_s = tb_s.text_frame
    tf_s.word_wrap = True
    p_st = tf_s.paragraphs[0]
    p_st.text = "SSE Streaming Protocol (ReadableStream)"
    p_st.font.size = Pt(13)
    p_st.font.bold = True
    p_st.font.color.rgb = COLOR_PRIMARY
    p_sb = tf_s.add_paragraph()
    p_sb.text = "• Uses fetch + ReadableStream instead of native EventSource to support Authorization headers.\n• Dispatches real-time structured JSON chunks to React frontend.\n• Automatically cleans up DB sessions and logs response latency."
    p_sb.font.size = Pt(11)
    p_sb.font.color.rgb = COLOR_TEXT_DARK
    p_sb.space_before = Pt(4)

    set_notes(s6_api, "SPEAKER NOTES:\nWalk through the API design:\n"
                      "1. Highlight POST /api/chat/stream: It uses Server-Sent Events over HTTP POST with fetch ReadableStream. "
                      "Native EventSource cannot send Authorization headers, so we used a custom fetch streaming reader in React.\n"
                      "2. Point out GET /health: It verifies PostgreSQL connection, pgvector extension, and Redis in one call.\n"
                      "3. All endpoints enforce Clerk JWKS RS256 token verification.")

    # =========================================================================
    # SLIDE 7: Medical Reference Corpus & Provenance
    # =========================================================================
    s7_corp = prs.slides.add_slide(blank_layout)
    add_bg(s7_corp)
    add_header(s7_corp, "The Medical Reference Corpus: Quality Over Unvetted Breadth")

    add_card(s7_corp, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.0))
    tb_l = s7_corp.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "Curated & License-Checked Repository"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY
    
    bullets = [
        "42+ Vetted Source Documents: Covering infectious diseases (dengue, malaria, TB), chronic conditions (diabetes, hypertension, asthma), everyday symptoms, and prevention.",
        "Strict Licensing Compliance: Every source explicitly mapped in corpus_manifest.json:\n  • WHO: CC BY-NC-SA 3.0 IGO\n  • UK NHS: Open Government Licence (OGL v3.0)\n  • US NIH / CDC: US Federal Public Domain",
        "Deterministic Extraction: Handled via PyMuPDF and Trafilatura, stripping boilerplate, headers, and footers.",
        "Semantic Chunking: 153 chunks bounded between ~300 to ~650 tokens to ensure clinical coherence."
    ]
    for b in bullets:
        p_b = tf_l.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    add_card(s7_corp, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.0))
    tb_r = s7_corp.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "High Priority for Indian Healthcare"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    bullets_r = [
        "High-Relevance Infectious Disease Focus: Extensive coverage for Dengue, Malaria, Tuberculosis, Typhoid, and Diarrhoeal diseases.",
        "Everyday Family Symptoms: High fever in adults & children, cough, dehydration, vomiting, paediatric skin rashes.",
        "Deliberate Frozen Corpus: Frozen snapshot prevents silent data corruption or unvetted web drift. If a condition isn't verified, it safely refuses.",
        "Auditable Citations: Every answer references the exact source document title, URL, and medical authority."
    ]
    for b in bullets_r:
        p_b = tf_r.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    set_notes(s7_corp, "SPEAKER NOTES:\nEvaluators often ask: 'Why only 42-50 documents? Why not index Wikipedia or the entire web?'\n"
                       "Answer: Breadth was traded for legal and clinical provenance. You cannot verify 10,000 scraped blog posts. "
                       "Every document here is from WHO, NHS, NIH, or CDC, with legally tracked licenses.")

    # =========================================================================
    # SLIDE 8: Safety Engineering: Red-Flag Emergency Triage
    # =========================================================================
    s8_safe = prs.slides.add_slide(blank_layout)
    add_bg(s8_safe)
    add_header(s8_safe, "Safety Engineering: Deterministic Emergency Short-Circuit", category_text="CRITICAL SAFETY ARCHITECTURE")

    c_speed = add_card(s8_safe, Inches(0.8), Inches(1.6), Inches(11.7), Inches(1.6), bg_color=RGBColor(255, 241, 242), border_color=COLOR_ACCENT_RED)
    tb_sp = s8_safe.shapes.add_textbox(Inches(1.0), Inches(1.7), Inches(11.3), Inches(1.4))
    tf_sp = tb_sp.text_frame
    tf_sp.word_wrap = True
    p = tf_sp.paragraphs[0]
    p.text = "PERFORMANCE ASYMMETRY: EMERGENCY TRIAGE vs GENERATION"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT_RED

    p_num = tf_sp.add_paragraph()
    p_num.text = "Red-Flag Matcher: < 1 ms in-process (~20 ms HTTP)   vs   LLM Generation: ~2,512 ms"
    p_num.font.size = Pt(20)
    p_num.font.bold = True
    p_num.font.color.rgb = COLOR_TEXT_DARK
    p_num.space_before = Pt(4)

    p_exp = tf_sp.add_paragraph()
    p_exp.text = "Short-circuits immediately before embedding, retrieval, and LLM generation. Eliminates latency and non-deterministic risks."
    p_exp.font.size = Pt(12)
    p_exp.font.color.rgb = COLOR_TEXT_MUTED
    p_exp.space_before = Pt(4)

    add_card(s8_safe, Inches(0.8), Inches(3.5), Inches(5.6), Inches(3.2))
    tb_cat = s8_safe.shapes.add_textbox(Inches(1.0), Inches(3.6), Inches(5.2), Inches(3.0))
    tf_cat = tb_cat.text_frame
    tf_cat.word_wrap = True
    p = tf_cat.paragraphs[0]
    p.text = "9 Critical Emergency Categories"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = COLOR_TEXT_DARK
    p_sub = tf_cat.add_paragraph()
    p_sub.text = "1. Cardiac (crushing chest pain, arm radiation)\n2. Breathing Distress (choking, severe asthma)\n3. Stroke Signs (BE-FAST: facial droop, arm weakness)\n4. Uncontrolled Severe Bleeding\n5. Acute Head Injury with altered mental state\n6. Loss of Consciousness / Unresponsiveness\n7. Anaphylaxis (throat swelling, severe allergy)\n8. Seizures / Convulsions\n9. Mental Health Crisis / Self-Harm"
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = COLOR_TEXT_DARK
    p_sub.space_before = Pt(6)

    add_card(s8_safe, Inches(6.8), Inches(3.5), Inches(5.7), Inches(3.2))
    tb_help = s8_safe.shapes.add_textbox(Inches(7.0), Inches(3.6), Inches(5.3), Inches(3.0))
    tf_help = tb_help.text_frame
    tf_help.word_wrap = True
    p = tf_help.paragraphs[0]
    p.text = "Emergency Helplines & Asymmetric Cost"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT_RED
    p_sub2 = tf_help.add_paragraph()
    p_sub2.text = "Integrated Indian Emergency Services:\n  • 112: All-in-One National Emergency Helpline\n  • 108: Emergency Ambulance Response\n  • 14416: Tele-MANAS (Mental Health Helpline)\n\nThe 'Cost Asymmetry' Rule:\nIf a user says 'I know it's just acid reflux, but my chest feels tight', the system still escalates. An unnecessary emergency checkup is an annoyance; a missed heart attack is fatal."
    p_sub2.font.size = Pt(11)
    p_sub2.font.color.rgb = COLOR_TEXT_DARK
    p_sub2.space_before = Pt(6)

    set_notes(s8_safe, "SPEAKER NOTES:\nHighlight the 20 ms vs 2500 ms speedup. Evaluators will appreciate that emergency triage "
                       "is deterministic regex, not an LLM guess. Mention the cost asymmetry: we deliberately escalate "
                       "chest pain even when the user suspects reflux.")

    # =========================================================================
    # SLIDE 9: High Availability & Resilience
    # =========================================================================
    s9_res = prs.slides.add_slide(blank_layout)
    add_bg(s9_res)
    add_header(s9_res, "High Availability & Operational Resilience")

    add_card(s9_res, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.0))
    tb_fb = s9_res.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.5))
    tf_fb = tb_fb.text_frame
    tf_fb.word_wrap = True
    p = tf_fb.paragraphs[0]
    p.text = "Dual-Provider Automatic LLM Fallback"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    bullets_fb = [
        "Primary Provider: Groq (Llama / GPT-OSS 120B) for ultra-fast token streaming (~1,800 ms median latency).",
        "Automatic Fallback: Gemini 2.5 Flash triggers automatically if Groq hits rate limits (TPM) or connection timeouts (8s limit).",
        "Clean Stream Recovery: If the primary fails mid-generation, the client cleanly discards the partial buffer and resumes from the fallback. No broken hybrid text.",
        "Measured Fallback Rate: 44% under heavy testing due to free-tier token budgets, proving the fallback is actively exercised."
    ]
    for b in bullets_fb:
        p_b = tf_fb.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    add_card(s9_res, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.0))
    tb_rl = s9_res.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.5))
    tf_rl = tb_rl.text_frame
    tf_rl.word_wrap = True
    p = tf_rl.paragraphs[0]
    p.text = "Redis Sliding-Window Rate Limiting"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    bullets_rl = [
        "Per-User Sliding Window: 10 requests per minute enforced per authenticated Clerk User ID.",
        "Atomic Lua Script: Trims old timestamps, counts active requests, records timestamp, and sets TTL in a single atomic Redis round-trip.",
        "Eliminates Race Conditions: Traditional read-then-write approaches permit concurrent limit bypass. Atomic execution prevents this.",
        "Fail-Open Resiliency: If Redis is unavailable, rate limiting is bypassed. A rate-limiter failure never takes down critical health access."
    ]
    for b in bullets_rl:
        p_b = tf_rl.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    set_notes(s9_res, "SPEAKER NOTES:\nExplain why resilience matters. Free tier APIs have strict rate limits. "
                      "Our system handles API exhaustion gracefully by switching providers on the fly, "
                      "and uses atomic Redis Lua scripts so rate limits can't be circumvented by concurrent requests.")

    # =========================================================================
    # SLIDE 10: Current Implementation Status & Tech Stack
    # =========================================================================
    s10_stat = prs.slides.add_slide(blank_layout)
    add_bg(s10_stat)
    add_header(s10_stat, "Current Implementation Status: Production Ready")

    stack_cards = [
        ("Backend & Database", "FastAPI (Python 3.11, async)\nSQLAlchemy 2.0 + asyncpg\nPostgreSQL 16 + pgvector (HNSW)\nRedis 7 Ephemeral Cache\nAlembic Database Migrations", Inches(0.8), Inches(1.6)),
        ("Frontend & UX", "React 18 + TypeScript + Vite\nTailwind CSS modern styling\nServer-Sent Events (SSE) Reader\nInteractive Citation Inspector\nEmergency Visual Escalation", Inches(4.8), Inches(1.6)),
        ("Security & Auth", "Clerk Authentication\nJWKS Cryptographic Verification\nRS256 JWT validation on all API calls\nNo browser-side credential trust\nStrict CORS & rate limit headers", Inches(8.8), Inches(1.6)),
    ]

    for title, desc, left, top in stack_cards:
        add_card(s10_stat, left, top, Inches(3.7), Inches(3.0))
        tb = s10_stat.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), Inches(3.3), Inches(2.6))
        tf = tb.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(15)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = COLOR_TEXT_DARK
        p_d.space_before = Pt(8)

    c_test = add_card(s10_stat, Inches(0.8), Inches(4.9), Inches(11.7), Inches(1.8), bg_color=RGBColor(240, 253, 244), border_color=COLOR_ACCENT_GREEN)
    tb_t = s10_stat.shapes.add_textbox(Inches(1.0), Inches(5.0), Inches(11.3), Inches(1.5))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    p = tf_t.paragraphs[0]
    p.text = "RIGOROUS AUTOMATED TEST SUITE: 282 UNIT TESTS (100% PASSING)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT_GREEN
    p_sub = tf_t.add_paragraph()
    p_sub.text = "Comprehensive test coverage executed in 4.46 seconds:\n• 98 tests for red-flag emergency detection & phrasing variants    • 38 tests for vector retriever & floor filtering\n• 31 tests for document extraction & chunking bounds             • 21 tests for authentication & rate limiting"
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = COLOR_TEXT_DARK
    p_sub.space_before = Pt(4)

    set_notes(s10_stat, "SPEAKER NOTES:\nHighlight that the application is fully functional end-to-end today. "
                        "Mention the 282 passing unit tests. Most student projects have zero automated tests; "
                        "having 282 tests passing in 4.4 seconds demonstrates production-grade engineering.")

    # =========================================================================
    # SLIDE 11: Empirical Benchmark Results
    # =========================================================================
    s11_bm = prs.slides.add_slide(blank_layout)
    add_bg(s11_bm)
    add_header(s11_bm, "Empirical Benchmark Results: Grounding & Latency")

    add_card(s11_bm, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.0))
    tb_bm1 = s11_bm.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.5))
    tf_bm1 = tb_bm1.text_frame
    tf_bm1.word_wrap = True
    p = tf_bm1.paragraphs[0]
    p.text = "Retrieval & Grounding Precision"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    bullets_bm1 = [
        "In-Corpus Retrieval Hit Rate: 90% (27/30 in-corpus medical queries retrieved relevant passages).",
        "Out-of-Corpus False Hit Rate: 0.0% (0/8 non-medical or off-topic queries cleared the 0.65 threshold).",
        "Top Similarity Separation: In-corpus median: 0.727 vs Out-of-corpus max: 0.555 (Wide 0.172 margin).",
        "Citation Validity: 100% (129 of 129 generated citations mechanically verified to match retrieved source text).",
        "Mean Citations: 4.8 verified sources cited per response."
    ]
    for b in bullets_bm1:
        p_b = tf_bm1.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(8)

    add_card(s11_bm, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.0))
    tb_bm2 = s11_bm.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.5))
    tf_bm2 = tb_bm2.text_frame
    tf_bm2.word_wrap = True
    p = tf_bm2.paragraphs[0]
    p.text = "System Latency Profile"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    bullets_bm2 = [
        "Red-Flag Escalation: ~0.1 ms in-process matcher (HTTP round-trip ~20 ms).",
        "Query Embedding (Gemini): Median 714 ms (p95: 950 ms).",
        "Vector Retrieval (pgvector HNSW): Median 46 ms (p95: 48 ms).",
        "Time to First Token (TTFT): Median 1,129 ms.",
        "Total End-to-End Generation: Median 2,512 ms (Groq p50: 1,843 ms, Gemini fallback p50: 3,605 ms).",
        "Safety Short-Circuit: 100% of red-flag queries prevented from reaching the LLM."
    ]
    for b in bullets_bm2:
        p_b = tf_bm2.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(8)

    set_notes(s11_bm, "SPEAKER NOTES:\nExplain the numbers on this slide.\n"
                      "The most critical statistic is 'False-Hit Rate on Out-of-Corpus: 0%'. "
                      "When tested with questions outside the corpus, not a single one cleared the 0.65 threshold. "
                      "This proves that the system never invents facts when it doesn't know the answer.")

    # =========================================================================
    # SLIDE 12: Live Demonstration Overview
    # =========================================================================
    s12_demo = prs.slides.add_slide(blank_layout)
    add_bg(s12_demo)
    add_header(s12_demo, "Live Demonstration: Four Key Evaluation Beats")

    beats = [
        ("Beat 1: Grounded Answer", "Query: 'What causes iron deficiency anaemia?'\n\nShows: Real-time SSE streaming, inline citation chips, and source inspector panel displaying NHS/WHO origin.", Inches(0.8)),
        ("Beat 2: Grounding Proof", "Query: 'What is the capital of France?'\n\nShows: Immediate refusal. Proves the model is structurally blocked without verified medical context.", Inches(3.8)),
        ("Beat 3: Emergency Short-Circuit", "Query: 'Crushing chest pain radiating to arm'\n\nShows: Instant red emergency banner (~20 ms). Directs to 112/108 without waiting for LLM tokens.", Inches(6.8)),
        ("Beat 4: Cost Asymmetry", "Query: 'I think it's acid reflux but chest hurts'\n\nShows: Still escalates. Proves safety priority: false alarms are minor; missed heart attacks are fatal.", Inches(9.8)),
    ]

    for title, desc, left in beats:
        add_card(s12_demo, left, Inches(1.8), Inches(2.7), Inches(4.8), border_color=COLOR_PRIMARY)
        tb = s12_demo.shapes.add_textbox(left + Inches(0.15), Inches(2.0), Inches(2.4), Inches(4.3))
        tf = tb.text_frame
        tf.word_wrap = True
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(14)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_PRIMARY
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = COLOR_TEXT_DARK
        p_d.space_before = Pt(12)

    set_notes(s12_demo, "SPEAKER NOTES:\nTransition to the live demo here.\n"
                        "Say: 'I will now demonstrate these four beats live in our running application.'\n"
                        "Remember: If demoing on Render, wake the backend 5 minutes beforehand by hitting /health.")

    # =========================================================================
    # SLIDE 13: Competitive Defense (Why Not ChatGPT?)
    # =========================================================================
    s13_def = prs.slides.add_slide(blank_layout)
    add_bg(s13_def)
    add_header(s13_def, "Defense: Why Use This Over Frontier AI Models (ChatGPT/Gemini)?")

    add_card(s13_def, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.0), border_color=COLOR_ACCENT_RED)
    tb_llm = s13_def.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.5))
    tf_llm = tb_llm.text_frame
    tf_llm.word_wrap = True
    p = tf_llm.paragraphs[0]
    p.text = "Frontier AI Models (ChatGPT, Claude)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT_RED

    bullets_cf = [
        "Unconstrained Intelligence: Trained to be helpful and conversational. They will speculate on symptoms and suggest unverified home remedies.",
        "Opaque Sourcing: Synthesize text from internet scrapings (Reddit, forums, blogs). Zero legal traceability or document-level citations.",
        "Dangerous Latency in Crises: Take 2-5 seconds over HTTP to chat conversationally when a user is experiencing cardiac arrest or stroke.",
        "Prompt Drift & Jailbreaks: System prompts ('Act like a doctor') can be bypassed or ignored by creative user queries."
    ]
    for b in bullets_cf:
        p_b = tf_llm.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    add_card(s13_def, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.0), border_color=COLOR_ACCENT_GREEN)
    tb_us = s13_def.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.5))
    tf_us = tb_us.text_frame
    tf_us.word_wrap = True
    p = tf_us.paragraphs[0]
    p.text = "Our Grounded Assistant Architecture"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_ACCENT_GREEN

    bullets_us = [
        "Enforced Negative Constraints: Architecturally incapable of hallucinating without verified medical context (0.65 similarity floor).",
        "100% Chain-of-Custody: Every claim links to an exact legal document chunk from WHO, NHS, NIH, or CDC.",
        "Deterministic Emergency Speed: Rule-based regex evaluates raw message in < 1 ms (~20 ms HTTP) and routes to 112/108 immediately.",
        "Zero Diagnosis Liability: Strictly explains literature; cannot prescribe medication or suggest dosages by design."
    ]
    for b in bullets_us:
        p_b = tf_us.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    set_notes(s13_def, "SPEAKER NOTES:\nThis slide directly answers the faculty's #1 question: 'Why not just use ChatGPT?'\n"
                       "Deliver the punchline: 'Raw intelligence without architectural constraints is dangerous in medicine. "
                       "Our system is not an unconstrained conversational chatbot; it is a safety-engineered, legally auditable clinical information system.'")

    # =========================================================================
    # SLIDE 14: Limitations & Future Scope
    # =========================================================================
    s14_lim = prs.slides.add_slide(blank_layout)
    add_bg(s14_lim)
    add_header(s14_lim, "Engineering Boundaries & Future Roadmap")

    add_card(s14_lim, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.0))
    tb_lim = s14_lim.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.5))
    tf_lim = tb_lim.text_frame
    tf_lim.word_wrap = True
    p = tf_lim.paragraphs[0]
    p.text = "Current Engineering Boundaries"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_SECONDARY

    bullets_lim = [
        "Curated Frozen Corpus: Limited to 42-50 vetted documents. Questions outside this scope (e.g. rare diseases, COVID-19) are refused.",
        "Informational Only: Built strictly as an informational tool. Cannot replace physical medical exams, diagnostics, or clinical triage.",
        "English Language: Currently trained and indexed for English medical literature.",
        "Manual Page Extraction for Bot-Protected Sites: 8 CDC articles require manual saving due to strict anti-scraping Cloudflare blocks."
    ]
    for b in bullets_lim:
        p_b = tf_lim.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    add_card(s14_lim, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.0))
    tb_fut = s14_lim.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.5))
    tf_fut = tb_fut.text_frame
    tf_fut.word_wrap = True
    p = tf_fut.paragraphs[0]
    p.text = "Future Technical Roadmap"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY

    bullets_fut = [
        "Automated LLM-as-a-Judge Verification: Adding real-time claim-to-passage entailment verification (NLI) before streaming.",
        "Indian Regional Language Support: Expanding ingestion and queries to Hindi, Tamil, Telugu, and Bengali.",
        "National Health Authority Ingestion: Expanding corpus to include official publications from ICMR (Indian Council of Medical Research) and AIIMS.",
        "Offline Edge Deployment: Exploring quantized on-device embeddings and small language models for remote rural health clinics."
    ]
    for b in bullets_fut:
        p_b = tf_fut.add_paragraph()
        p_b.text = "• " + b
        p_b.font.size = Pt(12)
        p_b.font.color.rgb = COLOR_TEXT_DARK
        p_b.space_before = Pt(10)

    set_notes(s14_lim, "SPEAKER NOTES:\nEvaluators appreciate candidates who honestly know their system's boundaries. "
                       "State clearly that the corpus is frozen on purpose, and outline practical next steps like Indian "
                       "regional language support and ICMR integration.")

    # =========================================================================
    # SLIDE 15: Conclusion & Q&A (Dark Theme)
    # =========================================================================
    s15_end = prs.slides.add_slide(blank_layout)
    add_bg(s15_end, dark=True)

    tbox_end = s15_end.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(2.0))
    tf_end = tbox_end.text_frame
    tf_end.word_wrap = True
    p1 = tf_end.paragraphs[0]
    p1.text = "Summary: An Assistant You Can Audit and Trust"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_TEXT_LIGHT

    p2 = tf_end.add_paragraph()
    p2.text = "Safety-Critical AI requires architectural constraints, deterministic triage, and legal provenance."
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(148, 163, 184)
    p2.space_before = Pt(12)

    stat_boxes = [
        ("100%", "Grounded Citation Validity (Verified against retrieved chunks)"),
        ("< 20 ms", "Emergency Triage Short-Circuit to 112 / 108"),
        ("282", "Passing Automated Unit Tests covering all safety layers"),
    ]
    for i, (stat, label) in enumerate(stat_boxes):
        left = Inches(0.8 + i * 4.0)
        c = add_card(s15_end, left, Inches(3.8), Inches(3.7), Inches(2.4), bg_color=RGBColor(30, 41, 59), border_color=COLOR_PRIMARY)
        tb = s15_end.shapes.add_textbox(left + Inches(0.2), Inches(4.0), Inches(3.3), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True
        p_s = tf.paragraphs[0]
        p_s.text = stat
        p_s.font.size = Pt(36)
        p_s.font.bold = True
        p_s.font.color.rgb = COLOR_PRIMARY
        p_l = tf.add_paragraph()
        p_l.text = label
        p_l.font.size = Pt(12)
        p_l.font.color.rgb = COLOR_TEXT_LIGHT
        p_l.space_before = Pt(8)

    set_notes(s15_end, "SPEAKER NOTES:\nConclude with confidence: 'Thank you. Our codebase is fully tested with 282 unit tests, "
                       "and deployed live. I am now open to any questions.'")

    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == "__main__":
    create_presentation()
