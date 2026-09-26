"""Compiled, case-insensitive patterns used by the extractor."""
from __future__ import annotations

import re

from .dictionaries import EDUCATION_ALIASES, NO_REQUIREMENT
from .models import EducationLevel


def _phrases(phrases: list[str]) -> re.Pattern[str]:
    # Lookarounds work for punctuation aliases too, unlike wrapping every alias in \b.
    return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(item) for item in sorted(phrases, key=len, reverse=True)) + r")(?!\w)", re.I)


CANDIDATE_PATTERNS: dict[EducationLevel, re.Pattern[str]] = {level: _phrases(phrases) for level, phrases in EDUCATION_ALIASES.items()}

# A generic field degree is useful evidence, but words such as ``specific``
# and ``formal`` are not a subject.  Keeping the guard in the pattern prevents
# the later normalizer from turning "no specific degree" into BACHELOR.
FIELD_DEGREE_PATTERN = re.compile(
    r"(?<!\w)(?<!['’])(?:"
    r"degree\s+in\s+(?P<subject>[A-Za-z][A-Za-z &/-]{1,80})"
    r"|(?!(?:no|any|specific|formal|higher|college|university|academic|"
    r"candidate|candidates|you|we|have|hold|need|require|required|preferred|with|in|"
    r"lieu|equivalent|related|field|of|to|a|an|the)\b)"
    r"(?P<subject_before>[A-Za-z]+(?:[ -][A-Za-z]+){0,3})\s+degree"
    r")(?!\w)",
    re.I,
)
DIPLOMA_IN_PATTERN = re.compile(r"(?<!\w)diploma\s+in\s+[A-Za-z][A-Za-z &/-]{1,80}(?!\w)", re.I)
MODALITY_PATTERNS = {
    "REQUIRED": re.compile(r"\b(must have|must hold|must possess|required|requires|minimum requirement|basic qualifications|qualifications|you hold|you have|should have|need to have|essential)\b", re.I),
    "PREFERRED": re.compile(r"\b(preferred|preferable|desirable|nice to have|a plus|is a plus|would be nice|ideal|bonus|advantageous)\b", re.I),
    "ALTERNATIVE": re.compile(
        r"\b(?:or equivalent|equivalent experience|equivalent degree|or comparable|or similar|"
        r"in lieu of|also\s+welcome|welcome\s+to\s+apply|"
        r"(?:may|will)\s+also\s+be\s+considered|also\s+be\s+considered)\b",
        re.I,
    ),
    "NEGATION": re.compile(
        r"\b(?:not\s+required|not\s+necessary|not\s+needed|no\s+requirement(?:s)?|"
        r"without\s+(?:a\s+)?degree|degree\s+not|explicitly\s+not\s+required|"
        r"no\s+formal\s+education\s+requirements?|education\s+is\s+absolutely\s+not\s+"
        r"a\s+gatekeeper|(?:will|would)\s+not\s+be\s+considered)\b",
        re.I,
    ),
    "BACKGROUND": re.compile(
        r"\b(?:previously|formerly|in the past|during (?:your|their) studies|your degree in|"
        r"background in|studied|earned your|holds a|we['’]ve hired|we have hired|we hire|"
        r"our best|others have|some of our|never finished|holding everything from|ranging from|"
        r"team with backgrounds|diverse team|from a\s+[A-Za-z]+\s+to a\s+[A-Za-z]+)\b",
        re.I,
    ),
}
BOOLEAN_CONNECTOR_PATTERN = re.compile(r"\b(or|and)\b|[;,/]", re.I)
NO_REQUIREMENT_PATTERNS = [_phrases([item]) for item in NO_REQUIREMENT]
BAC_PATTERN = re.compile(r"\b(?:baccalaur[eé]at|baccalaureate|bac)\s*\+\s*(?P<n>\d)\b", re.I)
BAC_RANGE_PATTERN = re.compile(r"\bbac\s*\+\s*(?P<low>\d)\s*(?:to|-|–|until)\s*\+?\s*(?P<high>\d)\b", re.I)
BARE_BAC_PATTERN = re.compile(r"\b(?:baccalaur[eé]at|baccalaureate|bac)\b(?!\s*\+)", re.I)
# Do not include ``degree in engineering`` here: it is normally a field in a
# Bachelor's/Master's phrase.  The explicit engineering-credential forms are
# unambiguous and are handled only for engineering-degree jurisdictions.
ENGINEERING_DEGREE_PATTERN = re.compile(
    r"(?<!\w)(?:engineering degree|engineering diploma|diploma in engineering|"
    r"diploma of engineering|engineer['’]s degree|engineer degree|"
    r"dipl[oô]me d['’]ing[eé]nieur|ing[eé]nieur diploma|"
    r"formation d['’]?ing[eé]nieur|école d['’]ing[eé]nieurs?|"
    r"engineering school|formation sup[eé]rieure|higher education|"
    r"degree\s+in\s+(?:[A-Za-z]+\s+){0,4}engineering)(?!\w)",
    re.I,
)
PARENTHETICAL_BAC_PATTERN = re.compile(r"\(\s*bac\s*\+\s*(?P<n>\d)\s*\)", re.I)
SOFT_NO_REQUIREMENT_PATTERN = re.compile(
    r"\bno\s+(?:specific\s+|formal\s+|academic\s+|college\s+|university\s+)?"
    r"degree(?:s)?\s+(?:is\s+|are\s+)?(?:mandated|required|needed|necessary|"
    r"a\s+requirement)\b",
    re.I,
)
EXPLICIT_NO_REQUIREMENT_PATTERN = re.compile(
    r"\b(?:a\s+)?(?:traditional\s+)?(?:four[- ]year|college|university|formal)?\s*"
    r"degree(?:s)?\s+(?:is\s+|are\s+)?(?:explicitly\s+)?not\s+"
    r"(?:required|necessary|needed)\b",
    re.I,
)
EXPERIENCE_IN_LIEU_PATTERN = re.compile(
    r"(?:\bin\s+lieu\s+of\s+(?:a\s+)?(?:formal\s+)?degree\b|"
    r"\b(?:or|in\s+lieu\s+of)\b\s+(?:(?:with|an?|the)\s+)?"
    r"(?:(?:an?\s+)?equivalent\s+)?(?:(?:\d+[+]?\s+)?years?\s+of\s+)?"
    r"(?:(?:professional|work|field|industry|hands[- ]on|self[- ]taught)\s+)?"
    r"(?:experience|portfolio|background)\b)",
    re.I,
)
# Covers the common ``with equivalent field experience`` branch when the
# conjunction is separated from the word ``or`` by a credential phrase.
EQUIVALENT_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:equivalent|comparable)\s+(?:(?:professional|work|field|industry|hands[- ]on)\s+)?experience\b",
    re.I,
)
EXCLUSION_PATTERNS = [
    re.compile(r"\b(?:education benefits|education stipend|education allowance|tuition reimbursement)\b", re.I),
    re.compile(r"\b(?:degree of|to a high degree)\b", re.I),
    re.compile(r"\b(?:high degree|your degree|their degree|the degree of)\b", re.I),
    re.compile(r"\bms\s+(?:office|word|excel|powerpoint|outlook|sql)\b", re.I),
]
