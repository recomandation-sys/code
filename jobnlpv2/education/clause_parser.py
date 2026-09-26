"""Small deterministic clause splitter and requirement-modality classifier."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Modality
from .patterns import MODALITY_PATTERNS

# Keep clause boundaries deterministic and offsets in the original text.  A
# clause boundary at an em dash/``but`` is important because job ads commonly
# put a required statement next to an anecdote in one long sentence.
_SPLIT = re.compile(
    r"(?:[;\n]|[—–]|\uFFFD|(?<!\w)--(?!\w)|\bbut\b|\bhowever\b|\bthough\b|"
    r"(?<!\be)(?<!\bi)(?<!\be\.g)(?<!\bi\.e)\.(?!\w)|"
    r"(?<=:)\s+(?=[A-Z]))+",
    re.I,
)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
_HEADERS = {"requirements": "REQUIRED", "qualifications": "REQUIRED", "education": "REQUIRED", "what you'll need": "REQUIRED", "must have": "REQUIRED", "nice to have": "PREFERRED", "preferred qualifications": "PREFERRED"}


@dataclass(frozen=True)
class Clause:
    text: str
    start: int
    end: int
    index: int
    modality: Modality
    is_header: bool = False
    header_type: str | None = None


def _header(text: str) -> str | None:
    cleaned = text.strip().rstrip(":").casefold()
    words = cleaned.split()
    titleish = text.strip().endswith(":") and len(words) < 6
    if cleaned in _HEADERS:
        return _HEADERS[cleaned]
    return "REQUIRED" if titleish and (text.strip().isupper() or text.strip().istitle()) else None


def _modality(text: str, inherited: str | None) -> Modality:
    # Negation and background are hard boundaries.  They must not inherit a
    # section's REQUIRED/PREFERRED label or leak a historical degree mention.
    if MODALITY_PATTERNS["NEGATION"].search(text):
        return Modality.NEGATED
    if MODALITY_PATTERNS["BACKGROUND"].search(text):
        return Modality.BACKGROUND_ONLY
    if MODALITY_PATTERNS["ALTERNATIVE"].search(text):
        return Modality.ACCEPTED_ALTERNATIVE
    if MODALITY_PATTERNS["PREFERRED"].search(text):
        return Modality.PREFERRED
    if MODALITY_PATTERNS["REQUIRED"].search(text):
        return Modality.REQUIRED
    return Modality(inherited) if inherited else Modality.UNKNOWN


def parse_clauses(text: str) -> list[Clause]:
    """Split while retaining original offsets and section-header inheritance."""
    clauses: list[Clause] = []
    inherited: str | None = None
    position = 0
    for match in _SPLIT.finditer(text):
        end = match.start()
        raw = text[position:end]
        position = match.end()
        clauses.extend(_make_clause(raw, position - len(raw) - len(match.group()), len(clauses), inherited))
        if clauses and clauses[-1].is_header:
            inherited = clauses[-1].header_type
    raw = text[position:]
    clauses.extend(_make_clause(raw, position, len(clauses), inherited))
    # Re-index after empty segments were discarded.
    return [Clause(c.text, c.start, c.end, i, c.modality, c.is_header, c.header_type) for i, c in enumerate(clauses)]


def _make_clause(raw: str, start: int, index: int, inherited: str | None) -> list[Clause]:
    stripped = _BULLET.sub("", raw).strip()
    if not stripped:
        return []
    offset = raw.find(stripped)
    actual_start = start + max(offset, 0)
    header_type = _header(stripped)
    if header_type:
        return [Clause(stripped, actual_start, actual_start + len(stripped), index, Modality.UNKNOWN, True, header_type)]
    return [Clause(stripped, actual_start, actual_start + len(stripped), index, _modality(stripped, inherited))]
