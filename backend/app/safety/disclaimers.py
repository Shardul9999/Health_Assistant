"""Fixed response text (§6).

Everything here is written in advance and returned verbatim. None of it is
generated, and none of it should ever be passed through an LLM to be "improved" -
the guarantee this project makes is that these exact words appear on these exact
paths.

Emergency numbers are India-specific per the plan: 112 (all emergencies),
108 (ambulance), 14416 (Tele-MANAS, national mental health helpline).
"""

from __future__ import annotations

from app.safety.red_flags import RedFlagCategory

EMERGENCY_NUMBER = "112"
AMBULANCE_NUMBER = "108"
TELE_MANAS = "14416"

# Shown persistently in the UI (DisclaimerBar) and appended to the API response
# so a curl user sees it too.
STANDARD_DISCLAIMER = (
    "This is general information from published health references, not medical advice, "
    "and not a substitute for diagnosis by a qualified professional. If your symptoms are "
    "severe, persistent, or getting worse, please see a doctor."
)

# Returned when retrieval finds nothing above the similarity floor. This is the
# visible proof that grounding is enforced - the model is never asked to fill the
# gap from its own knowledge.
NO_CONTEXT_RESPONSE = (
    "I don't have reliable reference material on that, so I can't give you a grounded answer.\n\n"
    "I only answer from a small library of verified health sources (WHO, CDC, NIH and NHS), "
    "and nothing in it covers your question closely enough for me to be confident.\n\n"
    "If this is a health concern, please speak to a doctor or pharmacist - they can ask the "
    "follow-up questions I can't."
)

_CARE_LINE = (
    f"Call **{EMERGENCY_NUMBER}** now, or an ambulance on **{AMBULANCE_NUMBER}**, "
    "or get to the nearest emergency department."
)

# One entry per category. Each names the concern plainly, directs to emergency
# care, and stops. No causes, no probabilities, no triage questions.
_ESCALATIONS: dict[RedFlagCategory, str] = {
    RedFlagCategory.CARDIAC: (
        "**Chest pain needs emergency assessment right now.**\n\n"
        f"{_CARE_LINE}\n\n"
        "Don't drive yourself. If you're with someone, ask them to stay with you. "
        "I'm not able to tell you what's causing this, and it isn't safe to wait and see."
    ),
    RedFlagCategory.BREATHING: (
        "**Difficulty breathing needs emergency assessment right now.**\n\n"
        f"{_CARE_LINE}\n\n"
        "Try to stay upright and as calm as you can while help is on the way. "
        "Don't wait to see whether it settles."
    ),
    RedFlagCategory.STROKE: (
        "**What you're describing can be a sign of a stroke. This is a medical emergency.**\n\n"
        f"{_CARE_LINE}\n\n"
        "Note the time the symptoms started and tell the emergency team - it affects "
        "the treatment they can give. Every minute matters here."
    ),
    RedFlagCategory.BLEEDING: (
        "**Heavy or uncontrolled bleeding needs emergency care right now.**\n\n"
        f"{_CARE_LINE}\n\n"
        "While you wait, press firmly on the wound with a clean cloth and keep the "
        "pressure on. If you can, raise the injured area."
    ),
    RedFlagCategory.CONSCIOUSNESS: (
        "**Loss of consciousness needs emergency assessment.**\n\n"
        f"{_CARE_LINE}\n\n"
        "If someone is unresponsive but breathing, put them on their side. "
        "Stay with them until help arrives."
    ),
    RedFlagCategory.ANAPHYLAXIS: (
        "**This may be a severe allergic reaction, which is life-threatening.**\n\n"
        f"{_CARE_LINE}\n\n"
        "If an adrenaline auto-injector (EpiPen) has been prescribed, use it now, then "
        "still call for emergency help - a second reaction can follow."
    ),
    RedFlagCategory.SEIZURE: (
        "**A seizure needs emergency assessment.**\n\n"
        f"{_CARE_LINE}\n\n"
        "Don't restrain the person or put anything in their mouth. Move hard objects "
        "away, cushion their head, and put them on their side once the movements stop."
    ),
    RedFlagCategory.HEAD_INJURY: (
        "**A head injury with these symptoms needs emergency assessment.**\n\n"
        f"{_CARE_LINE}\n\n"
        "Don't let the person be alone, and don't wait to see if it improves overnight."
    ),
    # Warm and brief, per §6. No methods, no assessment questions, no risk scoring.
    RedFlagCategory.SELF_HARM: (
        "**I'm really glad you told me, and I want you to talk to someone who can help properly.**\n\n"
        f"Please call **Tele-MANAS on {TELE_MANAS}** - it's India's national mental health "
        "helpline, free, confidential, and available in many languages, day or night. "
        f"If you're in immediate danger, call **{EMERGENCY_NUMBER}**.\n\n"
        "If there's someone you trust - a friend, a family member, anyone - reaching out to "
        "them right now would help too. You don't have to sit with this by yourself.\n\n"
        "I'm not the right kind of support for this, but the people on that line are."
    ),
}


def escalation_response(category: RedFlagCategory) -> str:
    """The fixed text for a red-flag category. Never generated, never varied."""
    return _ESCALATIONS[category]
