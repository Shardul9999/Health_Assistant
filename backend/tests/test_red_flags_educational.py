"""The educational exemption, pinned from both directions.

Context: bare condition-nouns ("stroke", "seizure", "anaphylaxis") were matching
any mention at all, so the system could never explain the very topics the
manifest's four emergency documents exist to cover.

The exemption is narrow by construction and these tests are what keep it narrow:

* A DESCRIPTIVE pattern - one describing what is happening to a person - always
  escalates. There is no phrasing that exempts "chest pain" or "can't breathe".
* A CONDITION_NOUN match is exempt only when the message is unambiguously a
  general question. Anything ambiguous escalates.
* SELF_HARM is excluded from the exemption entirely, at the category level.

If a change to red_flags.py makes any test in the first or third section fail,
the change is wrong, regardless of what it does for precision.
"""

import pytest

from app.safety.red_flags import RedFlagCategory, detect, is_red_flag

# =========================================================================== #
# 1. MUST STILL ESCALATE - descriptive symptom reports.                       #
#    These are non-negotiable. A failure here is a safety regression.         #
# =========================================================================== #

MUST_ESCALATE = [
    # --- the four the user named explicitly ---
    ("I can't breathe", RedFlagCategory.BREATHING),
    ("chest pain now", RedFlagCategory.CARDIAC),
    ("my face is drooping", RedFlagCategory.STROKE),
    ("someone is choking", RedFlagCategory.BREATHING),
    # --- descriptive, first person ---
    ("I have crushing chest pain radiating to my arm", RedFlagCategory.CARDIAC),
    ("my chest feels tight", RedFlagCategory.CARDIAC),
    ("my chest hurts", RedFlagCategory.CARDIAC),
    ("I can't breathe properly", RedFlagCategory.BREATHING),
    ("shortness of breath even at rest", RedFlagCategory.BREATHING),
    ("my throat is closing up", RedFlagCategory.ANAPHYLAXIS),
    ("my tongue is swelling", RedFlagCategory.ANAPHYLAXIS),
    ("the bleeding won't stop", RedFlagCategory.BLEEDING),
    ("I'm vomiting blood", RedFlagCategory.BLEEDING),
    ("I passed out this morning", RedFlagCategory.CONSCIOUSNESS),
    ("I hit my head and now I'm vomiting", RedFlagCategory.HEAD_INJURY),
    ("my speech is slurred", RedFlagCategory.STROKE),
    ("weakness down one side of my body", RedFlagCategory.STROKE),
    # --- third person, present tense: condition nouns in a live report ---
    ("I think my mother is having a stroke", RedFlagCategory.STROKE),
    ("my brother is having a seizure", RedFlagCategory.SEIZURE),
    ("he is having a heart attack", RedFlagCategory.CARDIAC),
    ("she is unresponsive", RedFlagCategory.CONSCIOUSNESS),
    ("my son is gasping for air", RedFlagCategory.BREATHING),
    ("her lips are turning blue", RedFlagCategory.BREATHING),
    ("my father collapsed", RedFlagCategory.CONSCIOUSNESS),
    # --- question-shaped, but reporting a real symptom ---
    ("what should I do, I have chest pain", RedFlagCategory.CARDIAC),
    ("is it serious that my chest hurts", RedFlagCategory.CARDIAC),
    ("what does it mean when I can't breathe", RedFlagCategory.BREATHING),
    ("why is my face drooping", RedFlagCategory.STROKE),
    ("how do I stop bleeding that won't stop", RedFlagCategory.BLEEDING),
    ("do I need a doctor, I think I'm having a heart attack", RedFlagCategory.CARDIAC),
    # --- hedged: uncertainty must never exempt ---
    ("not sure if this is chest pain but it hurts", RedFlagCategory.CARDIAC),
    ("I'm not certain, my chest feels tight though", RedFlagCategory.CARDIAC),
    # --- CORPUS_NOTES rule 3: reflux never wins over chest pain ---
    ("I know it's just my acid reflux but my chest hurts", RedFlagCategory.CARDIAC),
    ("what is chest pain", RedFlagCategory.CARDIAC),
]


@pytest.mark.parametrize("message,expected", MUST_ESCALATE)
def test_descriptive_reports_always_escalate(message: str, expected: RedFlagCategory):
    match = detect(message)
    assert match is not None, f"SAFETY REGRESSION - {message!r} no longer escalates"
    assert match.category is expected, (
        f"{message!r} escalated as {match.category.value}, expected {expected.value}"
    )


# =========================================================================== #
# 2. MAY PASS THROUGH - general questions about a condition, no symptom report. #
# =========================================================================== #

MAY_PASS_THROUGH = [
    # --- the three the user named explicitly ---
    "what is a seizure",
    "how does anaphylaxis work",
    "what are the warning signs of a stroke",
    # --- same shape, other categories ---
    "what causes a seizure",
    "what is a heart attack",
    "what causes fainting",
    "how do I prevent choking in toddlers",
    "how do I recognise anaphylaxis in a child",
    "how can I reduce my risk of stroke",
    "how does high blood pressure lead to stroke",
    "what are the symptoms of a stroke",
    "explain what happens during a seizure",
    "describe the signs of anaphylaxis",
    "why do people faint",
    "what is cardiac arrest",
    "tell me about epilepsy",
]


@pytest.mark.parametrize("message", MAY_PASS_THROUGH)
def test_general_questions_reach_retrieval(message: str):
    match = detect(message)
    assert match is None, (
        f"{message!r} still escalates as {match.category.value} "
        f"on {match.matched_phrase!r} - it is a general question, not a report"
    )


# =========================================================================== #
# 3. SELF-HARM IS EXCLUDED FROM THE EXEMPTION ENTIRELY.                       #
#    Educational phrasing must not open a path around Tele-MANAS.             #
# =========================================================================== #

SELF_HARM_ALWAYS = [
    # --- first person ---
    "I want to kill myself",
    "I don't want to be alive anymore",
    "I've been cutting myself",
    "I want to end my life",
    "there's no reason to go on",
    # --- third person: someone reporting on another person.
    #     A genuine false negative before this change - the patterns matched only
    #     "my"/"it", so every he/she/they phrasing walked straight past. Asking on
    #     behalf of a friend is common and high-stakes, and it silently missed.
    "he wants to end his life",
    "she doesn't want to live anymore",
    "my brother wants to end his life",
    "they don't want to be alive",
    "she talked about killing herself",
    "he has been hurting himself",
    "my friend is thinking about suicide",
    "she said she wants to die",
    "my sister has been cutting herself",
    "they want to kill themselves",
    # --- educational phrasing must NOT open a path around Tele-MANAS ---
    "what is suicide",
    "how does self-harm work",
    "tell me about suicidal ideation",
    "explain why people self harm",
    "what are the warning signs of suicide",
    "describe suicidal thoughts",
    "why do people want to end their life",
    "how common is self-harm",
    "what causes suicidal thoughts",
]


@pytest.mark.parametrize("message", SELF_HARM_ALWAYS)
def test_self_harm_escalates_regardless_of_phrasing(message: str):
    match = detect(message)
    assert match is not None, f"SAFETY REGRESSION - {message!r} did not escalate"
    assert match.category is RedFlagCategory.SELF_HARM
    from app.safety.disclaimers import TELE_MANAS, escalation_response

    assert TELE_MANAS in escalation_response(match.category)


# =========================================================================== #
# 4. AMBIGUITY RESOLVES TOWARD ESCALATION.                                    #
# =========================================================================== #

AMBIGUOUS_MUST_ESCALATE = [
    # A question in form, but someone is described as affected right now.
    "what should I do if someone is having a seizure right now",
    "my friend is having a stroke what do I do",
    "he's choking what should I do",
    "someone has collapsed, what now",
    # No interrogative opener at all - not a general question.
    "stroke",
    "seizure",
    "anaphylaxis help me",
    "heart attack",
    # Mixed: an educational frame wrapped around a live report.
    "what is a stroke, I think I'm having one",
    "how does anaphylaxis work, my throat is closing",
]


@pytest.mark.parametrize("message", AMBIGUOUS_MUST_ESCALATE)
def test_ambiguous_messages_escalate(message: str):
    assert is_red_flag(message), (
        f"{message!r} is ambiguous and must escalate - the exemption is too broad"
    )


# =========================================================================== #
# 5. The exemption must not resurrect the original false-negative risk.       #
# =========================================================================== #

def test_a_descriptive_match_later_in_the_message_still_wins():
    """An educational opener must not exempt a report that follows it."""
    match = detect("what are the warning signs of a stroke, my face is drooping")
    assert match is not None
    assert match.category is RedFlagCategory.STROKE


def test_exemption_does_not_apply_to_chest_pain_in_any_form():
    """Highest-stakes category: no phrasing exempts it."""
    for message in (
        "what is chest pain",
        "explain chest pain",
        "tell me about chest pain",
        "what causes chest tightness",
    ):
        assert is_red_flag(message), f"{message!r} must escalate"


def test_original_suite_still_passes_unchanged():
    """Sanity: the pre-existing corpus of emergencies is unaffected."""
    from tests.test_red_flags import EMERGENCIES

    for message, expected in EMERGENCIES:
        match = detect(message)
        assert match is not None, f"SAFETY REGRESSION - {message!r} no longer escalates"
        assert match.category is expected


# =========================================================================== #
# 6. A PASS-THROUGH ANSWER FOR AN EMERGENCY CONDITION CARRIES ITS OWN WARNING. #
#                                                                             #
#    Letting "what are the warning signs of a stroke" through means someone    #
#    who IS watching a stroke can now reach an explanatory answer instead of   #
#    the banner. The exemption is only safe if the answer itself says to call  #
#    112 when the signs are present now - so the notice is appended by the     #
#    pipeline as fixed text, not left to the model to remember.                #
# =========================================================================== #

EMERGENCY_TOPICS = [
    ("what are the warning signs of a stroke", RedFlagCategory.STROKE),
    ("what are the symptoms of a stroke", RedFlagCategory.STROKE),
    ("what is a heart attack", RedFlagCategory.CARDIAC),
    ("what is cardiac arrest", RedFlagCategory.CARDIAC),
    ("how does anaphylaxis work", RedFlagCategory.ANAPHYLAXIS),
    ("describe the signs of anaphylaxis", RedFlagCategory.ANAPHYLAXIS),
    ("what is a seizure", RedFlagCategory.SEIZURE),
    ("what causes a seizure", RedFlagCategory.SEIZURE),
    ("how do I prevent choking in toddlers", RedFlagCategory.BREATHING),
]


@pytest.mark.parametrize("message,category", EMERGENCY_TOPICS)
def test_exempted_topic_reports_its_category(message: str, category: RedFlagCategory):
    """The exemption must say which condition it let through, so the pipeline
    knows which escalation notice to append."""
    from app.safety.red_flags import educational_topic

    assert educational_topic(message) is category


@pytest.mark.parametrize("message,category", EMERGENCY_TOPICS)
def test_every_emergency_topic_has_an_escalation_notice(
    message: str, category: RedFlagCategory
):
    from app.safety.disclaimers import EMERGENCY_NUMBER, educational_notice

    notice = educational_notice(category)
    assert notice, f"no escalation notice defined for {category.value}"
    assert EMERGENCY_NUMBER in notice
    assert "right now" in notice.lower() or "immediately" in notice.lower()


def test_non_emergency_pass_through_gets_no_notice():
    """Only the emergency conditions carry the line; it is not a global footer."""
    from app.safety.red_flags import educational_topic

    assert educational_topic("what causes iron deficiency anaemia") is None
    assert educational_topic("how is dengue spread") is None


async def test_pass_through_answer_ends_with_the_escalation_line(monkeypatch):
    """End to end: an exempted emergency question produces a normal grounded
    answer with the fixed escalation line appended."""
    import uuid

    from app.api import chat as chat_api
    from app.core.rate_limit import RateLimitResult
    from app.db.session import AsyncSessionLocal
    from app.rag.retriever import RetrievedChunk
    from app.safety.disclaimers import EMERGENCY_NUMBER, educational_notice
    from app.schemas.chat import ChatRequest

    class FakeUser:
        user_id = f"test_edu_{uuid.uuid4().hex[:8]}"
        session_id = None

    async def allow(_uid):
        return RateLimitResult(allowed=True, count=1, limit=10, retry_after_s=0)

    async def fake_retrieve(*a, **k):
        return [
            RetrievedChunk(
                id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                content="A stroke happens when blood flow to part of the brain is cut off.",
                title="Stroke",
                source_url="https://www.nhs.uk/conditions/stroke/",
                source_org="NHS",
                license="ogl-v3",
                similarity=0.8,
            )
        ]

    async def fake_complete(messages, result=None, **k):
        if result is not None:
            result.provider = "groq"
        return "A stroke happens when blood flow to the brain is interrupted [Stroke]."

    monkeypatch.setattr(chat_api, "check_rate_limit", allow)
    monkeypatch.setattr(chat_api, "retrieve", fake_retrieve)
    monkeypatch.setattr(chat_api.llm, "complete", fake_complete)

    try:
        async with AsyncSessionLocal() as db:
            response = await chat_api.chat(
                ChatRequest(message="what are the warning signs of a stroke"),
                FakeUser(),
                db,
            )
    except Exception:
        pytest.skip("Postgres unavailable - run `docker compose up -d`")

    assert response.red_flag is False, "this should be a normal answer, not an escalation"
    assert response.sources, "the answer must still be grounded"
    assert response.content.endswith(educational_notice(RedFlagCategory.STROKE))
    assert EMERGENCY_NUMBER in response.content


async def test_ordinary_answer_does_not_get_the_escalation_line(monkeypatch):
    """The notice must not leak onto every answer - it would stop being read."""
    import uuid

    from app.api import chat as chat_api
    from app.core.rate_limit import RateLimitResult
    from app.db.session import AsyncSessionLocal
    from app.rag.retriever import RetrievedChunk
    from app.schemas.chat import ChatRequest

    class FakeUser:
        user_id = f"test_edu_{uuid.uuid4().hex[:8]}"
        session_id = None

    async def allow(_uid):
        return RateLimitResult(allowed=True, count=1, limit=10, retry_after_s=0)

    async def fake_retrieve(*a, **k):
        return [
            RetrievedChunk(
                id=uuid.uuid4(), document_id=uuid.uuid4(),
                content="Iron deficiency anaemia is caused by low iron.",
                title="Iron deficiency anaemia",
                source_url="https://www.nhs.uk/conditions/iron-deficiency-anaemia/",
                source_org="NHS", license="ogl-v3", similarity=0.8,
            )
        ]

    async def fake_complete(messages, result=None, **k):
        if result is not None:
            result.provider = "groq"
        return "Low iron causes it [Iron deficiency anaemia]."

    monkeypatch.setattr(chat_api, "check_rate_limit", allow)
    monkeypatch.setattr(chat_api, "retrieve", fake_retrieve)
    monkeypatch.setattr(chat_api.llm, "complete", fake_complete)

    try:
        async with AsyncSessionLocal() as db:
            response = await chat_api.chat(
                ChatRequest(message="what causes iron deficiency anaemia"), FakeUser(), db
            )
    except Exception:
        pytest.skip("Postgres unavailable - run `docker compose up -d`")

    assert "112" not in response.content


async def test_no_context_answer_for_an_emergency_topic_still_escalates(monkeypatch):
    """The corpus gap is ours; the emergency is real either way.

    "what are the warning signs of a stroke" currently retrieves nothing,
    because cdc-stroke-signs is one of the CDC pages blocked by bot protection.
    Someone asking because they are watching a stroke must not be left with a
    bare "I don't have material on that".
    """
    import uuid

    from app.api import chat as chat_api
    from app.core.rate_limit import RateLimitResult
    from app.db.session import AsyncSessionLocal
    from app.safety.disclaimers import (
        NO_CONTEXT_RESPONSE,
        EMERGENCY_NUMBER,
        educational_notice,
    )
    from app.schemas.chat import ChatRequest

    class FakeUser:
        user_id = f"test_edu_{uuid.uuid4().hex[:8]}"
        session_id = None

    async def allow(_uid):
        return RateLimitResult(allowed=True, count=1, limit=10, retry_after_s=0)

    async def nothing_retrieved(*a, **k):
        return []

    called = {"llm": 0}

    async def never_called(*a, **k):
        called["llm"] += 1
        return "should not happen"

    monkeypatch.setattr(chat_api, "check_rate_limit", allow)
    monkeypatch.setattr(chat_api, "retrieve", nothing_retrieved)
    monkeypatch.setattr(chat_api.llm, "complete", never_called)

    try:
        async with AsyncSessionLocal() as db:
            response = await chat_api.chat(
                ChatRequest(message="what are the warning signs of a stroke"),
                FakeUser(),
                db,
            )
    except Exception:
        pytest.skip("Postgres unavailable - run `docker compose up -d`")

    assert called["llm"] == 0, "grounding must still be enforced"
    assert NO_CONTEXT_RESPONSE in response.content
    assert response.content.endswith(educational_notice(RedFlagCategory.STROKE))
    assert EMERGENCY_NUMBER in response.content
