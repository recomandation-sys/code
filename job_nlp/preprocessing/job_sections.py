"""Lightweight generic section zoning — offsets into DESCRIPTION."""
from __future__ import annotations

import re
from dataclasses import dataclass

SectionType = str  # TITLE | ROLE | RESPONSIBILITIES | REQUIREMENTS | ...

_HEADINGS: list[tuple[str, re.Pattern[str]]] = [
    ("REQUIREMENTS", re.compile(r"^(?:requirements|what you.?ll need|what we.?re looking for|must have)\b", re.I)),
    ("QUALIFICATIONS", re.compile(r"^(?:qualifications|profile|who you are)\b", re.I)),
    ("EDUCATION", re.compile(r"^(?:education|academic|diplomas?)\b", re.I)),
    ("EXPERIENCE", re.compile(r"^(?:experience|professional experience)\b", re.I)),
    ("LANGUAGES", re.compile(r"^(?:languages?|language requirements)\b", re.I)),
    ("EMPLOYMENT_TERMS", re.compile(r"^(?:contract|employment|offer|working conditions|compensation)\b", re.I)),
    ("LOCATION", re.compile(r"^(?:location|where you.?ll work|workplace)\b", re.I)),
    ("RESPONSIBILITIES", re.compile(r"^(?:responsibilities|your role|what you.?ll do|duties|missions?)\b", re.I)),
    ("BENEFITS", re.compile(r"^(?:benefits|perks|we offer)\b", re.I)),
    ("COMPANY", re.compile(r"^(?:about us|about the company|who we are|the company)\b", re.I)),
]


@dataclass(frozen=True)
class SectionSpan:
    section_type: SectionType
    start: int
    end: int


def zone_description(description: str) -> list[SectionSpan]:
    """Split description by generic headings. Offsets relative to description."""
    text = description or ""
    if not text.strip():
        return []
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(keepends=True)):
        # compute line start
        pass
    # Line-based scan with absolute offsets
    pos = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip().strip(":").strip()
        for stype, pat in _HEADINGS:
            if stripped and pat.match(stripped) and len(stripped) < 80:
                hits.append((pos, stype))
                break
        pos += len(line)
    if not hits:
        return [SectionSpan("OTHER", 0, len(text))]
    spans: list[SectionSpan] = []
    if hits[0][0] > 0:
        spans.append(SectionSpan("OTHER", 0, hits[0][0]))
    for i, (start, stype) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        spans.append(SectionSpan(stype, start, end))
    return spans


def section_at(zones: list[SectionSpan], offset: int) -> str:
    for z in zones:
        if z.start <= offset < z.end:
            return z.section_type
    return "OTHER"
