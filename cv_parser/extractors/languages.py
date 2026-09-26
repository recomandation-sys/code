"""Language extraction and proficiency normalization (section 43).

Deterministic and section-scoped: only the `LANGUAGES` section is read (a
stray "Python" or "English" elsewhere in the CV is not a spoken-language
claim). Each list segment is matched against a curated multilingual
language-name lexicon (exact match only — language names are a small,
closed, low-ambiguity set, so no fuzzy matching is needed here); an
optional proficiency phrase or CEFR code attached to the segment is
normalized when confidently recognized, and always preserved raw
otherwise ("do not force qualitative phrases into exact CEFR values when
the mapping is uncertain" — section 43).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from cv_parser.config import RESOURCES_DIR
from cv_parser.normalization.text import strip_heading_line
from cv_parser.schemas.parser_response import CEFRLevel, LanguageEntry
from cv_parser.structure.section_classifier import Section

LANGUAGE_NAMES_PATH = RESOURCES_DIR / "languages" / "language_names.json"

_CEFR_RE = re.compile(r"\b([ABC][12])\b", re.IGNORECASE)
# Deliberately narrower than the skills package's list splitter: a bare
# " - " here is very often the language/level separator itself
# ("Spanish - B2"), not a bullet, so it must NOT be treated as a segment
# boundary the way it is for technology lists.
_LANGUAGE_SEGMENT_SPLIT_RE = re.compile(r"[,;|•\u2022]")

# Proficiency phrase -> canonical CEFR-family level (section 43). Ordered
# longest-phrase-first so e.g. "professional working proficiency" is not
# pre-empted by a shorter, coarser "professional" match.
_PROFICIENCY_PHRASES: list[tuple[str, CEFRLevel]] = [
    ("full professional proficiency", "FLUENT"),
    ("professional working proficiency", "INTERMEDIATE"),
    ("limited working proficiency", "BASIC"),
    ("elementary proficiency", "BASIC"),
    ("native or bilingual", "NATIVE"),
    ("mother tongue", "NATIVE"),
    ("langue maternelle", "NATIVE"),
    ("native speaker", "NATIVE"),
    ("native", "NATIVE"),
    ("bilingual", "NATIVE"),
    ("fluent", "FLUENT"),
    ("courant", "FLUENT"),
    ("avancé", "ADVANCED"),
    ("avance", "ADVANCED"),
    ("advanced", "ADVANCED"),
    ("professional", "INTERMEDIATE"),
    ("professionnel", "INTERMEDIATE"),
    ("intermédiaire", "INTERMEDIATE"),
    ("intermediaire", "INTERMEDIATE"),
    ("intermediate", "INTERMEDIATE"),
    ("working knowledge", "INTERMEDIATE"),
    ("conversational", "INTERMEDIATE"),
    ("notions", "BASIC"),
    ("débutant", "BASIC"),
    ("debutant", "BASIC"),
    ("beginner", "BASIC"),
    ("elementary", "BASIC"),
    ("basic", "BASIC"),
    ("basique", "BASIC"),
]

_LEVEL_SEPARATOR_RE = re.compile(r"[:\-–—]")


@lru_cache(maxsize=1)
def _language_alias_index() -> dict[str, str]:
    """normalized alias (lowercase) -> canonical English language name."""
    raw = json.loads(LANGUAGE_NAMES_PATH.read_text(encoding="utf-8"))
    index: dict[str, str] = {}
    for canonical, aliases in raw.items():
        for alias in aliases:
            index[alias.strip().lower()] = canonical
    return index


def _match_language_name(text: str) -> str | None:
    return _language_alias_index().get(text.strip().lower())


def _normalize_level(raw_level: str) -> CEFRLevel | None:
    """Returns a canonical CEFR-family level for a recognized raw phrase,
    or "UNKNOWN" if *something* was stated but not confidently mapped —
    never silently invents a specific level (section 43)."""
    cefr_match = _CEFR_RE.search(raw_level)
    if cefr_match:
        return cefr_match.group(1).upper()  # type: ignore[return-value]

    lowered = raw_level.strip().lower()
    for phrase, level in _PROFICIENCY_PHRASES:
        if phrase in lowered:
            return level

    return "UNKNOWN"


def _split_language_and_level(segment: str) -> tuple[str, str | None]:
    """One list segment ("English (Native)", "French: C1", "Spanish") ->
    (language_text, raw_level_or_None)."""
    paren_match = re.search(r"\(([^)]+)\)", segment)
    if paren_match:
        level = paren_match.group(1).strip()
        language_text = (segment[: paren_match.start()] + segment[paren_match.end() :]).strip()
        return language_text, level or None

    sep_match = _LEVEL_SEPARATOR_RE.search(segment)
    if sep_match:
        left = segment[: sep_match.start()].strip()
        right = segment[sep_match.end() :].strip()
        # Only treat the right-hand side as a level if the left-hand side
        # alone already resolves to a known language — otherwise a plain
        # hyphenated language name ("Chinese-Mandarin") would be wrongly
        # split into a fake "level".
        if left and right and _match_language_name(left) is not None:
            return left, right

    # Trailing bare CEFR code with no separator: "English C1".
    cefr_match = _CEFR_RE.search(segment)
    if cefr_match:
        language_text = (segment[: cefr_match.start()] + segment[cefr_match.end() :]).strip()
        if language_text:
            return language_text, cefr_match.group(1)

    return segment.strip(), None


def _split_language_segments(line: str) -> list[str]:
    return [s.strip() for s in _LANGUAGE_SEGMENT_SPLIT_RE.split(line) if s.strip()]


def extract_languages(sections: list[Section]) -> list[LanguageEntry]:
    section = next((s for s in sections if s.section_type == "LANGUAGES"), None)
    if section is None:
        return []

    text = strip_heading_line(section.text, section.raw_heading)
    if not text.strip():
        return []

    entries: list[LanguageEntry] = []
    seen: set[str] = set()

    for line in text.split("\n"):
        for segment in _split_language_segments(line):
            language_text, raw_level = _split_language_and_level(segment)
            canonical = _match_language_name(language_text)
            if canonical is None:
                continue
            if canonical in seen:
                continue
            seen.add(canonical)

            normalized_level = _normalize_level(raw_level) if raw_level else None
            entries.append(
                LanguageEntry(
                    language=canonical,
                    raw_level=raw_level,
                    normalized_level=normalized_level,
                    confidence="HIGH",
                )
            )

    return entries
