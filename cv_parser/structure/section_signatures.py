"""Structural section signatures — Layer C of section classification
(section 18).

Used only when a heading's text didn't match any known alias (exactly or
via strict fuzzy matching): look at the section's *content shape* instead.
Every signal here is a formal/structural pattern (date-year tokens,
CEFR-like level tokens, punctuation density) — never a semantic guess
about meaning, and never a rule tuned against one specific CV's wording.
"""
from __future__ import annotations

import re
from typing import Literal

SectionType = Literal[
    "HEADER",
    "PROFILE_SUMMARY",
    "SKILLS",
    "PROFESSIONAL_EXPERIENCE",
    "INTERNSHIP",
    "ALTERNANCE",
    "PROJECTS",
    "CERTIFICATIONS",
    "LANGUAGES",
    "EDUCATION",
    "CONTACT",
    # Recognized but deliberately out of the schema's field-producing scope
    # (declaration boilerplate, hobbies, references, ...) — classifying
    # these correctly, instead of leaving them "UNKNOWN", keeps
    # `section_coverage` (section 47) truthful and stops their content
    # from ever being scanned by an unrelated extractor.
    "IGNORED",
    "UNKNOWN",
]

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_CEFR_RE = re.compile(r"\b[ABC][12]\b", re.IGNORECASE)
_LANGUAGE_PROFICIENCY_WORDS = re.compile(
    r"\b(native|fluent|advanced|intermediate|basic|beginner|"
    r"natif|natale|courant|avancé|intermédiaire|débutant|notions)\b",
    re.IGNORECASE,
)
_COMMON_LANGUAGE_NAMES = re.compile(
    r"\b(english|french|arabic|spanish|german|italian|portuguese|chinese|"
    r"anglais|français|arabe|espagnol|allemand|italien|portugais|chinois)\b",
    re.IGNORECASE,
)
_CERT_VOCAB_RE = re.compile(
    r"\b(certified|certificate|certification|certifi[ée]|attestation)\b", re.IGNORECASE
)
_LIST_SEPARATOR_RE = re.compile(r"[,•|;/·]")
_SENTENCE_END_RE = re.compile(r"[.!?]\s")


def _skills_score(text: str) -> float:
    tokens = [t.strip() for t in _LIST_SEPARATOR_RE.split(text) if t.strip()]
    if len(tokens) < 4:
        return 0.0
    avg_words = sum(len(t.split()) for t in tokens) / len(tokens)
    sentence_ratio = len(_SENTENCE_END_RE.findall(text)) / max(len(text.split("\n")), 1)
    score = 0.0
    if avg_words <= 3.0:
        score += 2.0
    if sentence_ratio < 0.1:
        score += 1.0
    if len(tokens) >= 8:
        score += 1.0
    return score


def _experience_score(text: str) -> float:
    """Dates alone are not enough (a certification list is also full of
    years); real experience prose additionally has narrative-length
    description lines, not just short "title / date" pairs."""
    lines = [l for l in text.split("\n") if l.strip()]
    if not lines:
        return 0.0
    date_lines = sum(1 for l in lines if _YEAR_RE.search(l))
    long_narrative_lines = sum(1 for l in lines if len(l.split()) >= 8)

    score = 0.0
    if date_lines >= 2 and long_narrative_lines >= 1:
        score += 2.0
    elif date_lines >= 2:
        score += 0.75
    elif date_lines == 1:
        score += 0.5
    if long_narrative_lines >= 1:
        score += 0.5
    return score


def _languages_score(text: str) -> float:
    score = 0.0
    if _CEFR_RE.search(text):
        score += 2.0
    if _LANGUAGE_PROFICIENCY_WORDS.search(text):
        score += 1.0
    if _COMMON_LANGUAGE_NAMES.search(text):
        score += 1.0
    lines = [l for l in text.split("\n") if l.strip()]
    short_lines = sum(1 for l in lines if len(l.split()) <= 4)
    if lines and short_lines / len(lines) > 0.6:
        score += 0.5
    return score


def _certifications_score(text: str) -> float:
    score = 0.0
    if _CERT_VOCAB_RE.search(text):
        score += 2.0
    if _YEAR_RE.search(text):
        score += 0.5
    return score


def classify_by_signature(text: str) -> tuple[SectionType, float] | None:
    """Return the best-scoring structural signature above a confidence
    margin, or `None` if the content is genuinely ambiguous (stays
    `UNKNOWN` per section 4.4 — unknown is safer than a forced mapping).
    """
    if not text.strip():
        return None

    scores: dict[SectionType, float] = {
        "SKILLS": _skills_score(text),
        "PROFESSIONAL_EXPERIENCE": _experience_score(text),
        "LANGUAGES": _languages_score(text),
        "CERTIFICATIONS": _certifications_score(text),
    }
    best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score < 2.0:
        return None

    # Require a clear margin over the runner-up so genuinely ambiguous
    # content (could plausibly be either) stays UNKNOWN rather than being
    # forced into whichever signature happened to score marginally higher.
    remaining = sorted((s for t, s in scores.items() if t != best_type), reverse=True)
    if remaining and (best_score - remaining[0]) < 0.75:
        return None

    return best_type, best_score
