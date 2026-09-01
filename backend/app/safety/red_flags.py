"""Emergency symptom detection (§6).

This runs on the raw user message BEFORE retrieval. On a match the whole pipeline
short-circuits: no embedding, no retrieval, no LLM call, no follow-up questions.
The response is fixed text written in advance.

Design notes, because the shape of this file is deliberate:

* **Recall beats precision here, by a lot.** An unnecessary "please seek care" is
  a minor annoyance. A missed cardiac event is not recoverable. Where a phrase is
  ambiguous, it matches. `CORPUS_NOTES.md` rule 3 is the concrete case: chest pain
  escalates every time, even though reflux is the likelier explanation and the
  corpus contains a GERD page describing exactly that overlap.

* **Matching is on normalised text with word boundaries**, so "chest pain" fires
  on "Chest  Pain!!" and "my chest pains" but "breastbone" does not accidentally
  fire something. Negation is handled narrowly (see `_NEGATION`) - only for
  clear-cut denials like "no chest pain", never for hedges like "not sure if".

* **No triage questions, ever.** Asking "how severe is it?" delays a call to 112
  and implies the system can adjudicate. It cannot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RedFlagCategory(str, Enum):
    CARDIAC = "cardiac"
    BREATHING = "breathing"
    STROKE = "stroke"
    BLEEDING = "bleeding"
    # Ahead of CONSCIOUSNESS deliberately. These patterns require an impact *and*
    # a symptom, so on "hit my head and passed out" this is the more specific
    # match, and the advice it carries is the more useful of the two.
    HEAD_INJURY = "head_injury"
    CONSCIOUSNESS = "consciousness"
    ANAPHYLAXIS = "anaphylaxis"
    SEIZURE = "seizure"
    SELF_HARM = "self_harm"


class PatternKind(str, Enum):
    """Whether a pattern describes a person's state or merely names a condition.

    DESCRIPTIVE patterns say something is happening to someone right now
    ("chest pain", "can't breathe", "face drooping"). They always escalate.

    CONDITION_NOUN patterns are just the name of a condition ("stroke",
    "seizure", "anaphylaxis"). Those appear as often in a question about the
    topic as in a report of it, and only these are eligible for the educational
    exemption below.
    """

    DESCRIPTIVE = "descriptive"
    CONDITION_NOUN = "condition_noun"


@dataclass(frozen=True)
class RedFlagMatch:
    category: RedFlagCategory
    matched_phrase: str


# Each entry is a regex fragment matched case-insensitively against normalised text.
# Keep them phrase-shaped: single words like "pain" or "bleeding" alone are far too
# broad and would swallow ordinary questions.
_PATTERNS: dict[RedFlagCategory, tuple[str, ...]] = {
    RedFlagCategory.CARDIAC: (
        r"chest (?:pain|pains|pressure|tightness|tight|discomfort|heaviness|hurt\w*)",
        r"(?:pain|pressure|tightness|tight|heavy|heaviness|ache|aching|discomfort|burning|crushing|squeez\w+)\b[^.?!]{0,30}\bin my chest",
        r"my chest (?:feels|is|hurts|aches)\b[^.?!]{0,25}\b(?:tight|heavy|painful|crushing|pressure|squeez\w+|hurt\w*|ach\w*)",
        r"my chest hurts",
        r"crushing (?:pain|sensation|feeling)",
        r"(?:pain|ache|aching|numbness|tingling)\b[^.?!]{0,40}\b(?:radiat\w+|spread\w+|shoot\w+|going|travel\w+)\b[^.?!]{0,30}\b(?:arm|jaw|neck|shoulder|back)",
        r"radiat\w+\b[^.?!]{0,25}\b(?:to|down|into)\b[^.?!]{0,20}\b(?:arm|jaw|neck|shoulder)",
        r"heart attack",
        r"cardiac arrest",
        r"elephant\b[^.?!]{0,20}\bmy chest",
        r"angina",
    ),
    RedFlagCategory.BREATHING: (
        r"(?:can'?t|cannot|can not|couldn'?t|unable to|struggling to|difficulty|trouble|hard to)\b[^.?!]{0,20}\bbreath\w*",
        r"(?:difficulty|trouble|struggling|problems?)\b[^.?!]{0,15}\bbreathing",
        r"short(?:ness)? of breath",
        r"gasping for (?:air|breath)",
        r"choking",
        r"turning blue",
        r"(?:lips|fingers|face)\b[^.?!]{0,15}\bblue",
        r"stopped breathing",
        r"not breathing",
        r"suffocat\w+",
    ),
    RedFlagCategory.STROKE: (
        r"(?:face|facial|mouth)\b[^.?!]{0,20}\b(?:droop\w*|drooping|sagging|numb|paralys\w+)",
        r"droop\w*\b[^.?!]{0,20}\b(?:face|mouth|eye|smile)",
        r"slurr\w+\b[^.?!]{0,15}\bspeech",
        r"speech\b[^.?!]{0,15}\bslurr\w+",
        r"(?:can'?t|cannot|unable to|trouble|difficulty)\b[^.?!]{0,20}\b(?:speak|talk|form words|find words)",
        r"(?:weak\w*|numb\w*|paralys\w+)\b[^.?!]{0,30}\b(?:one side|left side|right side|down one)",
        r"one side of (?:my|the|his|her|their)\b[^.?!]{0,20}\b(?:body|face)\b[^.?!]{0,20}\b(?:weak|numb|droop\w*|paralys\w+)",
        r"sudden\w*\b[^.?!]{0,20}\b(?:confus\w+|vision loss|blurred vision|can'?t see)",
        r"\bstroke\b",
        r"\bf\.?a\.?s\.?t\.? test\b",
        r"worst headache of my life",
        r"thunderclap headache",
    ),
    RedFlagCategory.BLEEDING: (
        r"(?:severe|heavy|profuse|uncontrolled|won'?t stop|can'?t stop|massive)\b[^.?!]{0,20}\bbleed\w*",
        r"bleeding\b[^.?!]{0,25}\b(?:won'?t stop|will not stop|heavily|uncontrollably|profusely)",
        r"blood (?:is )?(?:gushing|spurting|pouring|pumping)",
        r"lost a lot of blood",
        r"(?:vomiting|coughing up|throwing up)\b[^.?!]{0,15}\bblood",
        r"blood in (?:my )?(?:vomit|stool|stools)",
        r"(?:black|tarry) stools?",
        r"haemorrhag\w+|hemorrhag\w+",
    ),
    RedFlagCategory.CONSCIOUSNESS: (
        r"(?:lost|loss of|losing)\b[^.?!]{0,15}\bconsciousness",
        r"(?:passed|passing|blacked|blacking)\s+out",
        r"faint(?:ed|ing)\b",
        r"unconscious|unresponsive",
        r"(?:won'?t|will not|can'?t|cannot)\b[^.?!]{0,15}\bwake\b[^.?!]{0,10}\bup",
        r"collaps\w+",
        r"\bcoma\b",
    ),
    RedFlagCategory.ANAPHYLAXIS: (
        r"anaphyla\w+",
        r"(?:throat|tongue|lips|face|mouth)\b[^.?!]{0,20}\bswell\w*",
        r"swell\w*\b[^.?!]{0,20}\b(?:throat|tongue|lips|face|mouth)",
        r"throat (?:is )?(?:closing|tightening|closing up)",
        r"(?:allergic reaction|allergy)\b[^.?!]{0,30}\b(?:severe|breath\w*|swell\w*|throat)",
        r"severe allergic reaction",
        r"epipen|epi-pen|adrenaline auto",
        r"(?:hives|rash)\b[^.?!]{0,30}\b(?:breath\w*|swell\w*|throat|dizzy)",
    ),
    RedFlagCategory.SEIZURE: (
        r"seizure|seizing|convuls\w+",
        r"\bfit(?:s|ting)?\b[^.?!]{0,25}\b(?:having|had|shaking|jerking|collaps\w+)",
        r"(?:having|had|is having)\b[^.?!]{0,15}\ba fit\b",
        r"(?:body|arms|legs)\b[^.?!]{0,20}\b(?:jerking|shaking uncontrollably|twitching uncontrollably)",
        r"epilep\w+\b[^.?!]{0,25}\b(?:attack|episode|now|happening)",
        r"status epilepticus",
    ),
    RedFlagCategory.HEAD_INJURY: (
        r"(?:hit|banged|struck|knocked)\b[^.?!]{0,15}\b(?:my|his|her|their|the)?\s*head\b[^.?!]{0,40}\b(?:vomit\w*|confus\w*|unconscious|passed out|blood|bleeding|dizzy|drowsy|can'?t remember)",
        r"head (?:injury|trauma|wound)\b[^.?!]{0,40}\b(?:vomit\w*|confus\w*|unconscious|passed out|bleeding|seizure|drowsy)",
        r"(?:severe|serious|bad|major)\b[^.?!]{0,10}\bhead (?:injury|trauma)",
        r"skull fracture",
        r"(?:clear )?fluid (?:leaking|coming)\b[^.?!]{0,20}\b(?:from|out of)\b[^.?!]{0,15}\b(?:ear|nose)",
        r"(?:fell|fall)\b[^.?!]{0,30}\bhead\b[^.?!]{0,30}\b(?:unconscious|passed out|vomit\w*|confus\w*)",
    ),
    RedFlagCategory.SELF_HARM: (
        # Third-person phrasings are as important as first-person: someone
        # asking on behalf of a friend or sibling is common, and every one of
        # these missed before the reflexive/possessive alternatives were widened.
        r"(?:kill|killing|hurt|hurting|harm|harming)\s+(?:my|your|him|her|them|our|it)sel(?:f|ves)",
        r"suicid\w+",
        r"end(?:ing)? (?:my|his|her|their|your|our|its|it|the) (?:own )?life",
        r"(?:want|wants|wanting|going|plan|plans|planning|thinking about)\b[^.?!]{0,30}\bto die\b",
        r"(?:do|does|did)(?:n'?t| not) want to (?:be alive|live|wake up|go on|carry on)",
        r"better off (?:dead|without me|without him|without her|without them)",
        r"self[- ]harm\w*|self harming|cutting (?:my|him|her|them|your)sel(?:f|ves)",
        r"no reason to (?:live|go on|carry on)",
        r"overdos\w+\b[^.?!]{0,25}\b(?:took|taken|on purpose|deliberately)",
        r"(?:took|taken)\b[^.?!]{0,25}\boverdos\w+",
    ),
}

# Patterns that merely name a condition. Listed explicitly rather than inferred,
# so adding a new pattern defaults to DESCRIPTIVE - the safe direction.
_CONDITION_NOUN_PATTERNS: frozenset[str] = frozenset({
    r"heart attack",
    r"cardiac arrest",
    r"angina",
    r"choking",
    r"suffocat\w+",
    r"\bstroke\b",
    r"\bf\.?a\.?s\.?t\.? test\b",
    r"anaphyla\w+",
    r"epipen|epi-pen|adrenaline auto",
    r"seizure|seizing|convuls\w+",
    r"status epilepticus",
    r"faint(?:ed|ing)\b",
    r"\bcoma\b",
    r"haemorrhag\w+|hemorrhag\w+",
    r"skull fracture",
})


def _kind(pattern: str) -> PatternKind:
    return (
        PatternKind.CONDITION_NOUN
        if pattern in _CONDITION_NOUN_PATTERNS
        else PatternKind.DESCRIPTIVE
    )


_COMPILED: dict[RedFlagCategory, tuple[tuple[re.Pattern[str], PatternKind], ...]] = {
    category: tuple((re.compile(p, re.IGNORECASE), _kind(p)) for p in patterns)
    for category, patterns in _PATTERNS.items()
}

# Self-harm is excluded from the exemption entirely. An educational-sounding
# question about suicide still routes to Tele-MANAS: the cost of being wrong is
# not symmetrical with the cost of withholding a definition.
_EXEMPT_CATEGORIES: frozenset[RedFlagCategory] = frozenset(
    set(RedFlagCategory) - {RedFlagCategory.SELF_HARM}
)

# Conditions whose pass-through answer must carry its own escalation line: if
# someone reaches an explanation while actually witnessing the emergency, the
# answer has to tell them to call for help.
EMERGENCY_TOPIC_CATEGORIES: frozenset[RedFlagCategory] = frozenset({
    RedFlagCategory.CARDIAC,
    RedFlagCategory.STROKE,
    RedFlagCategory.ANAPHYLAXIS,
    RedFlagCategory.SEIZURE,
    RedFlagCategory.BREATHING,
})

# Opens like a general question about a topic rather than a report.
_EDUCATIONAL_OPENER = re.compile(
    r"^\s*(?:what|what'?s|how|why|when|which|who|whom|"
    r"tell me|explain|describe|define|list|"
    r"is|are|does|do|can you|could you)\b"
)

# If any of these appear the message is a personal report, whatever it opens
# with. Two deliberate narrownesses: "my" only counts beside a body part or a
# person, so "reduce my risk of stroke" is a question while "my chest hurts" is
# not; and bare "I" is not enough - the verb decides, so "how do I prevent
# choking" is a question while "I can't breathe" is a report.
_PERSONAL_REPORT = re.compile(
    r"\b(?:i|we)\s*(?:'m|'ve|am|have|has|had|feel|felt|got|think i|"
    r"can'?t|cannot|couldn'?t|keep|started|experienced)\b"
    r"|\bmy\s+(?:chest|throat|tongue|lips|face|mouth|head|arm|leg|hand|"
    r"speech|vision|breathing|heart|body|son|daughter|mother|father|wife|"
    r"husband|child|baby|brother|sister|friend|mum|mom|dad)\b"
    r"|\b(?:he|she|they|someone|somebody)\s*(?:'s|is|are|has|have|had|was|were)\b"
    r"|\bis having\b|\bare having\b|\bhaving (?:a|an|one)\b"
    r"|\bright now\b|\bjust now\b|\bjust happened\b|\bhelp me\b|\bhelp\b"
    r"|\bthis morning\b|\bminutes ago\b|\bsince (?:this|last|yesterday)\b"
)


def _is_educational(text: str) -> bool:
    """True only when the message is unambiguously a general question.

    Every ambiguous case resolves to False, i.e. toward escalation.
    """
    if not _EDUCATIONAL_OPENER.match(text):
        return False
    return not _PERSONAL_REPORT.search(text)

# Narrow, explicit denials only. "I have no chest pain" must not escalate, but
# anything hedged ("not sure if this is chest pain") absolutely must.
_NEGATION = re.compile(
    r"\b(?:no|not|without|never had|haven'?t had|don'?t have|doesn'?t have|denies|deny)\b"
)

# These contain a negation word but express uncertainty rather than denial, so
# they are stripped from the window before the denial check runs. The asymmetry
# is the entire point: "no chest pain" is exempt, "not sure if it's chest pain"
# escalates. Someone hedging about a cardiac symptom is exactly who must reach a
# doctor, and they are also the likeliest to phrase it tentatively.
_HEDGE = re.compile(
    r"\bno idea\b"
    r"|\bnot\s+(?:sure|certain|positive|convinced|entirely|really|totally|quite)\b"
)

# Normalisation: collapse whitespace and strip punctuation that breaks phrases
# apart, so "chest-pain" and "chest  pain!!!" both match "chest pain".
_PUNCT = re.compile(r"[^\w\s'?.!]+")
_WS = re.compile(r"\s+")


def normalise(message: str) -> str:
    text = _PUNCT.sub(" ", message.lower())
    return _WS.sub(" ", text).strip()


def _is_negated(text: str, start: int) -> bool:
    """True if a denial appears in the ~40 characters before the match."""
    window = text[max(0, start - 40) : start]
    # A sentence boundary resets the window - "I had no fever. Chest pain now."
    window = re.split(r"[.?!]", window)[-1]
    window = _HEDGE.sub(" ", window)
    return bool(_NEGATION.search(window))


@dataclass(frozen=True)
class Assessment:
    """The full result of scanning one message.

    `match` set  -> escalate, and nothing downstream runs.
    `exempted`   -> a condition was named but only in a general question. The
                    pipeline answers normally and, for the emergency conditions,
                    appends a fixed escalation line to the answer.
    """

    match: RedFlagMatch | None = None
    exempted: RedFlagCategory | None = None


def assess(message: str) -> Assessment:
    """Scan a message for red flags, applying the educational exemption.

    Categories are checked in the declaration order of RedFlagCategory, which puts
    the time-critical ones (cardiac, breathing, stroke) first. A message mentioning
    several concerns escalates on the most urgent.
    """
    text = normalise(message)
    educational = _is_educational(text)
    exempted: RedFlagCategory | None = None

    # Iterate the enum, not _COMPILED: the enum's declaration order is the
    # priority order, and driving it from the dict literal would silently
    # re-prioritise categories whenever someone reordered the patterns.
    for category in RedFlagCategory:
        for pattern, kind in _COMPILED[category]:
            for match in pattern.finditer(text):
                if _is_negated(text, match.start()):
                    continue
                if (
                    kind is PatternKind.CONDITION_NOUN
                    and educational
                    and category in _EXEMPT_CATEGORIES
                ):
                    # Remember it, but keep scanning: a descriptive match later
                    # in the same message still escalates. "what is a stroke, I
                    # think I'm having one" must not pass.
                    exempted = exempted or category
                    continue
                return Assessment(
                    match=RedFlagMatch(category=category, matched_phrase=match.group(0))
                )

    return Assessment(exempted=exempted)


def detect(message: str) -> RedFlagMatch | None:
    """Return the first red-flag match, or None."""
    return assess(message).match


def is_red_flag(message: str) -> bool:
    return detect(message) is not None


def educational_topic(message: str) -> RedFlagCategory | None:
    """The emergency condition a general question asked about, if any.

    Returns None unless the message was exempted *and* names one of the
    conditions whose answer must carry its own escalation line. A question about
    fainting or a haemorrhage is exempt but does not get the 112 footer - the
    line only stays readable if it is rare.
    """
    exempted = assess(message).exempted
    return exempted if exempted in EMERGENCY_TOPIC_CATEGORIES else None
