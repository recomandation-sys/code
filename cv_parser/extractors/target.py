"""Desired position extraction (section 22).

Priority order, first match wins:
  1. an explicit target statement anywhere in the document ("Seeking...",
     "Recherche un poste de...")
  2. the headline line immediately under the candidate's name in the
     header region
  3. an explicit target phrase inside the profile/summary section
  4. otherwise empty — the most recent job title is never reused as the
     desired position (that would conflate "what they did" with "what
     they want", which section 4.5 explicitly treats as different).
"""
from __future__ import annotations

import re

from cv_parser.schemas.internal import Document
from cv_parser.schemas.parser_response import DesiredPosition
from cv_parser.structure.section_classifier import Section

# Deliberately strict, explicit forward-looking phrases only — a resume
# that merely *describes past work* must never satisfy these.
_EXPLICIT_TARGET_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\btarget position\b\s*[:\-]?\s*(.+)",
        r"\bdesired position\b\s*[:\-]?\s*(.+)",
        r"\bseeking\b(?:\s+a| an)?\s+(?:position\s+as\s+)?(.+)",
        r"\blooking for\b(?:\s+a| an)?\s+(?:position\s+as\s+|role\s+as\s+)?(.+)",
        r"\bposte souhait[ée]\b\s*[:\-]?\s*(.+)",
        r"\bposte recherch[ée]\b\s*[:\-]?\s*(.+)",
        r"\brecherch[e|é]\s+un\s+poste\s+de\s+(.+)",
        r"\b[àa]\s+la\s+recherche\s+d['e]\s*(?:un poste de\s+)?(.+)",
        r"\bobjectif professionnel\b\s*[:\-]?\s*(.+)",
    ]
]

_MAX_POSITION_WORDS = 8


def _clean_captured(raw: str) -> str | None:
    text = raw.strip(" .:;-–—|\t")
    if not text:
        return None
    words = text.split()
    if len(words) > _MAX_POSITION_WORDS:
        text = " ".join(words[:_MAX_POSITION_WORDS])
    return text


def _find_explicit_statement(text: str) -> str | None:
    for pattern in _EXPLICIT_TARGET_PATTERNS:
        match = pattern.search(text)
        if match:
            captured = _clean_captured(match.group(1))
            if captured:
                return captured
    return None


def _all_lines_text(document: Document) -> list[str]:
    return [line.text for block in document.blocks for line in block.lines if line.text.strip()]


def _headline_from_header(document: Document, sections: list[Section]) -> str | None:
    header = next((s for s in sections if s.section_type == "HEADER"), None)
    if header is None or not header.line_ids:
        return None

    lines_by_id = {line.id: line for block in document.blocks for line in block.lines}
    header_lines = [lines_by_id[lid] for lid in header.line_ids if lid in lines_by_id]
    header_lines = [l for l in header_lines if l.page == 0 and l.text.strip()]
    if len(header_lines) < 2:
        return None

    # The headline is the line right after the (largest/first) name line —
    # approximate the name line as the one with the largest font, since
    # `identity.py` already owns the authoritative name-selection logic
    # and this module must not duplicate or fight with it.
    name_idx = max(range(len(header_lines)), key=lambda i: header_lines[i].median_font_size or 0)
    if name_idx + 1 >= len(header_lines):
        return None

    candidate = header_lines[name_idx + 1].text.strip()
    if not candidate or "@" in candidate or len(candidate.split()) > 8:
        return None
    return candidate


def extract_desired_positions(document: Document, sections: list[Section]) -> list[DesiredPosition]:
    # Priority 1: explicit statement anywhere in the document.
    for text in _all_lines_text(document):
        found = _find_explicit_statement(text)
        if found:
            return [DesiredPosition(raw=found, normalized=None, source_type="EXPLICIT_TARGET", confidence="HIGH")]

    # Priority 2: headline immediately under the candidate's name.
    headline = _headline_from_header(document, sections)
    if headline:
        return [DesiredPosition(raw=headline, normalized=None, source_type="CV_HEADLINE", confidence="MEDIUM")]

    # Priority 3: explicit statement inside the profile/summary section only.
    profile = next((s for s in sections if s.section_type == "PROFILE_SUMMARY"), None)
    if profile is not None:
        found = _find_explicit_statement(profile.text)
        if found:
            return [DesiredPosition(raw=found, normalized=None, source_type="PROFILE_STATEMENT", confidence="MEDIUM")]

    # Priority 4: unknown is valid — never fall back to the latest job title.
    return []
