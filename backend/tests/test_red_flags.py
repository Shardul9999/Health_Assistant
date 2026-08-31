"""Red-flag detection (§10).

False negatives here are the worst possible bug in this system, so the emergency
cases are exhaustive and include the near-miss phrasings people actually type -
understated, misspelled, third-person, buried mid-sentence.

The non-emergency set guards the other direction: if ordinary questions escalate,
users learn to ignore the banner and the whole mechanism stops working.
"""

import pytest

from app.safety.disclaimers import (
    EMERGENCY_NUMBER,
    TELE_MANAS,
    escalation_response,
)
from app.safety.red_flags import RedFlagCategory, detect, is_red_flag

# --------------------------------------------------------------------------- must escalate

EMERGENCIES: list[tuple[str, RedFlagCategory]] = [
    # --- cardiac ---
    ("I have crushing chest pain radiating to my arm", RedFlagCategory.CARDIAC),
    ("my chest feels tight", RedFlagCategory.CARDIAC),  # named in the plan
    ("chest pain", RedFlagCategory.CARDIAC),
    ("Chest  Pain!!!", RedFlagCategory.CARDIAC),
    ("my chest hurts and I feel sick", RedFlagCategory.CARDIAC),
    ("there's a heaviness in my chest since morning", RedFlagCategory.CARDIAC),
    ("pressure in my chest when I walk upstairs", RedFlagCategory.CARDIAC),
    ("dad says he has chest discomfort, is it serious", RedFlagCategory.CARDIAC),
    ("pain spreading to my jaw and left arm", RedFlagCategory.CARDIAC),
    ("feels like an elephant sitting on my chest", RedFlagCategory.CARDIAC),
    ("could this be a heart attack", RedFlagCategory.CARDIAC),
    # --- breathing ---
    ("I can't breathe properly", RedFlagCategory.BREATHING),
    ("cant breathe", RedFlagCategory.BREATHING),
    ("having trouble breathing since last night", RedFlagCategory.BREATHING),
    ("shortness of breath even at rest", RedFlagCategory.BREATHING),
    ("my son is gasping for air", RedFlagCategory.BREATHING),
    ("her lips are turning blue", RedFlagCategory.BREATHING),
    ("he stopped breathing", RedFlagCategory.BREATHING),
    # --- stroke ---
    ("my face is drooping on one side", RedFlagCategory.STROKE),
    ("his speech is slurred suddenly", RedFlagCategory.STROKE),
    ("she can't speak properly all of a sudden", RedFlagCategory.STROKE),
    ("weakness down one side of my body", RedFlagCategory.STROKE),
    ("numbness on my left side and confusion", RedFlagCategory.STROKE),
    ("worst headache of my life came on in seconds", RedFlagCategory.STROKE),
    ("i think my mother is having a stroke", RedFlagCategory.STROKE),
    # --- bleeding ---
    ("severe bleeding from a cut on my leg", RedFlagCategory.BLEEDING),
    ("the bleeding won't stop", RedFlagCategory.BLEEDING),
    ("I'm vomiting blood", RedFlagCategory.BLEEDING),
    ("blood is gushing from the wound", RedFlagCategory.BLEEDING),
    ("black tarry stools for two days", RedFlagCategory.BLEEDING),
    # --- consciousness ---
    ("I passed out this morning", RedFlagCategory.CONSCIOUSNESS),
    ("he lost consciousness after standing up", RedFlagCategory.CONSCIOUSNESS),
    ("she is unresponsive", RedFlagCategory.CONSCIOUSNESS),
    ("my father collapsed", RedFlagCategory.CONSCIOUSNESS),
    ("he won't wake up", RedFlagCategory.CONSCIOUSNESS),
    # --- anaphylaxis ---
    ("my throat is closing up after eating peanuts", RedFlagCategory.ANAPHYLAXIS),
    ("my tongue is swelling", RedFlagCategory.ANAPHYLAXIS),
    ("severe allergic reaction to a bee sting", RedFlagCategory.ANAPHYLAXIS),
    ("I think this is anaphylaxis", RedFlagCategory.ANAPHYLAXIS),
    ("lips swelling up and I feel dizzy", RedFlagCategory.ANAPHYLAXIS),
    # --- seizure ---
    ("my brother is having a seizure", RedFlagCategory.SEIZURE),
    ("she is convulsing", RedFlagCategory.SEIZURE),
    ("he had a fit ten minutes ago", RedFlagCategory.SEIZURE),
    # --- head injury ---
    ("I hit my head and now I'm vomiting", RedFlagCategory.HEAD_INJURY),
    ("he banged his head and passed out", RedFlagCategory.HEAD_INJURY),
    ("head injury with confusion", RedFlagCategory.HEAD_INJURY),
    ("clear fluid leaking from his ear after a fall", RedFlagCategory.HEAD_INJURY),
    # --- self harm ---
    ("I want to kill myself", RedFlagCategory.SELF_HARM),
    ("thinking about suicide", RedFlagCategory.SELF_HARM),
    ("I don't want to be alive anymore", RedFlagCategory.SELF_HARM),
    ("everyone would be better off without me", RedFlagCategory.SELF_HARM),
    ("I've been cutting myself", RedFlagCategory.SELF_HARM),
    ("I took an overdose on purpose", RedFlagCategory.SELF_HARM),
    ("there's no reason to go on", RedFlagCategory.SELF_HARM),
]


@pytest.mark.parametrize("message,expected", EMERGENCIES)
def test_emergency_messages_escalate(message: str, expected: RedFlagCategory):
    match = detect(message)
    assert match is not None, f"FALSE NEGATIVE - {message!r} did not escalate"
    assert match.category is expected, (
        f"{message!r} escalated as {match.category.value}, expected {expected.value}"
    )


def test_every_category_is_reachable():
    """No category may exist without a test proving it fires."""
    covered = {category for _, category in EMERGENCIES}
    missing = set(RedFlagCategory) - covered
    assert not missing, f"categories with no passing test: {[c.value for c in missing]}"


# --------------------------------------------------------------------------- must not escalate

NON_EMERGENCIES = [
    "what causes iron deficiency anaemia",
    "how is dengue transmitted",
    "what are the symptoms of typhoid",
    "how much water should I drink daily",
    "is paracetamol safe with food",
    "what is the difference between a cold and the flu",
    "how do I prevent mosquito bites",
    "my ankle is sore after running",
    "I have a mild headache and a runny nose",
    "what foods are high in iron",
    "how long does a common cold last",
    "tell me about tuberculosis prevention",
    "what is BMI",
    "I've had a sore throat for two days",
    "can I exercise with a mild fever",
    "how do I fix my laptop keyboard",
    "what does haemoglobin do",
    "my child has a rash on their arm",
    "is it normal to feel tired in the afternoon",
    "what vaccines are recommended for adults",
]


@pytest.mark.parametrize("message", NON_EMERGENCIES)
def test_ordinary_questions_do_not_escalate(message: str):
    match = detect(message)
    assert match is None, (
        f"FALSE POSITIVE - {message!r} escalated as {match.category.value} "
        f"on {match.matched_phrase!r}"
    )


# --------------------------------------------------------------------------- negation

def test_clear_denials_do_not_escalate():
    assert not is_red_flag("I have a cough but no chest pain")
    assert not is_red_flag("fever without difficulty breathing")
    assert not is_red_flag("I don't have chest pain, just heartburn")


def test_hedged_phrasing_still_escalates():
    """Only clear-cut denials are exempt. Uncertainty must escalate."""
    assert is_red_flag("not sure if this counts as chest pain but it hurts")
    assert is_red_flag("I'm not certain, my chest feels tight though")


def test_denial_does_not_carry_across_a_sentence_boundary():
    assert is_red_flag("I had no fever yesterday. Now I have crushing chest pain.")


# --------------------------------------------------------------------------- CORPUS_NOTES rule 3

def test_chest_pain_escalates_even_when_user_blames_reflux():
    """CORPUS_NOTES.md rule 3: the system never adjudicates GERD vs cardiac.

    The cost asymmetry is total, so this escalates even when the user is probably
    right and explicitly says so.
    """
    for message in (
        "I know it's just my acid reflux but my chest hurts",
        "heartburn again, chest pain after eating",
        "GERD flare up, chest pressure, nothing serious right",
    ):
        assert is_red_flag(message), f"{message!r} must escalate regardless of user's own theory"


# --------------------------------------------------------------------------- response content

@pytest.mark.parametrize("category", list(RedFlagCategory))
def test_every_category_has_an_escalation_response(category: RedFlagCategory):
    text = escalation_response(category)
    assert text and len(text) > 80
    # Must route somewhere real.
    assert EMERGENCY_NUMBER in text or TELE_MANAS in text


@pytest.mark.parametrize("category", list(RedFlagCategory))
def test_escalations_ask_no_triage_questions(category: RedFlagCategory):
    """§6: no follow-up triage questions. Asking delays the call."""
    text = escalation_response(category)
    assert "?" not in text, f"{category.value} escalation contains a question"


def test_self_harm_response_routes_to_tele_manas():
    text = escalation_response(RedFlagCategory.SELF_HARM)
    assert TELE_MANAS in text
    # Warm, and free of assessment language or anything method-adjacent.
    lowered = text.lower()
    for banned in ("how many", "have you planned", "on a scale", "method", "pills", "rate your"):
        assert banned not in lowered, f"self-harm response contains {banned!r}"
