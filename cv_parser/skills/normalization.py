"""Text normalization for skill matching (section 31, step 1).

Deliberately minimal: `normalize_for_matching` must preserve string
length/character offsets 1:1 against the input so that automaton match
spans can be reused directly for boundary validation and context lookup.
Only case-folding is applied — Unicode NFKC or punctuation stripping could
shift offsets or destroy the very symbols (`+`, `#`, `.`) that symbolic
aliases depend on.
"""
from __future__ import annotations

import re

# section 35: configurable labels that mark a line as an explicit
# structured technology list rather than narrative prose.
_TECH_LIST_LABELS = [
    "technologies",
    "technology",
    "tech stack",
    "stack",
    "tools",
    "tooling",
    "environment",
    "built with",
    "frameworks",
    "programming languages",
    "languages used",
    "databases",
    "cloud",
    "compétences techniques",
    "technologies utilisées",
    "outils",
    "environnement technique",
    "langages",
]
_TECH_LIST_LABEL_RE = re.compile(
    r"^\s*(?:" + "|".join(re.escape(lbl) for lbl in _TECH_LIST_LABELS) + r")\s*[:\-]\s*(.+)$",
    re.IGNORECASE,
)

_SEGMENT_SPLIT_RE = re.compile(r"[,;|•\u2022]|(?:\s-\s)|(?:^-\s)")


def normalize_for_matching(text: str) -> str:
    """Lowercase only — length- and offset-preserving for ASCII/Latin
    text, which covers every alias in the curated lexicon."""
    return text.lower()


def find_tech_list_label(line: str) -> str | None:
    """If `line` starts with a configured technology-list label
    (`Technologies:`, `Stack -`, ...), return the remainder after the
    label; otherwise `None` (section 35)."""
    match = _TECH_LIST_LABEL_RE.match(line)
    if match:
        return match.group(1).strip()
    return None


def find_tech_list_label_span(line: str) -> tuple[str, int, int] | None:
    """Same as `find_tech_list_label`, but also returns the remainder's
    (start, end) offsets within `line` so callers can map it back to a
    larger enclosing text for evidence/overlap bookkeeping."""
    match = _TECH_LIST_LABEL_RE.match(line)
    if not match:
        return None
    raw_start, raw_end = match.span(1)
    remainder = match.group(1)
    stripped = remainder.strip()
    if not stripped:
        return None
    lead = len(remainder) - len(remainder.lstrip())
    start = raw_start + lead
    end = start + len(stripped)
    return stripped, start, end


def split_tech_list(text: str) -> list[tuple[str, int, int]]:
    """Split an already-identified technology-list region into
    (segment_text, start, end) spans by comma/bullet/pipe/semicolon
    (section 35, step 1). Offsets are relative to `text` so callers can
    still map segments back to the original source for evidence.
    """
    segments: list[tuple[str, int, int]] = []
    last = 0
    for m in _SEGMENT_SPLIT_RE.finditer(text):
        chunk = text[last : m.start()]
        _append_trimmed(segments, chunk, last)
        last = m.end()
    _append_trimmed(segments, text[last:], last)
    return segments


def _append_trimmed(segments: list[tuple[str, int, int]], chunk: str, offset: int) -> None:
    stripped = chunk.strip()
    if not stripped:
        return
    start = offset + chunk.index(stripped)
    end = start + len(stripped)
    # Drop a lone trailing period left over from end-of-sentence
    # punctuation ("Data Modeling.") without touching real content.
    if stripped.endswith(".") and not stripped.endswith(".."):
        stripped = stripped[:-1].rstrip()
        end = start + len(stripped)
    if stripped:
        segments.append((stripped, start, end))
