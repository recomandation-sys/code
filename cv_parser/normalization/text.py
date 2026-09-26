"""Generic, language-agnostic text-normalization helpers.

These are formal/character-level transforms (unicode normalization,
whitespace collapsing, ligature/bullet cleanup) — not business rules about
how a CV is structured. They run before structure discovery and field
extraction so OCR/PDF artifacts don't degrade downstream pattern matching.
"""
from __future__ import annotations

import re
import unicodedata

_BULLET_CHARS = "•◦▪‣∙·–—-*"
_WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_LEADING_BULLET_RE = re.compile(rf"^[\s{re.escape(_BULLET_CHARS)}]+")


def normalize_unicode(text: str) -> str:
    """NFKC normalization + drop control characters OCR sometimes emits."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in text if ch == "\n" or unicodedata.category(ch)[0] != "C")


def collapse_whitespace(text: str) -> str:
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def strip_leading_bullet(line: str) -> str:
    return _LEADING_BULLET_RE.sub("", line).strip()


def clean_text_block(text: str) -> str:
    text = normalize_unicode(text)
    text = collapse_whitespace(text)
    lines = [strip_leading_bullet(l) for l in text.split("\n")]
    return "\n".join(l for l in lines if l)


def strip_heading_line(text: str, raw_heading: str | None) -> str:
    """`Section.text` includes its own heading line as its first line
    (`raw_heading` is a separate, duplicated copy kept for display) —
    record-bearing sections already drop it during segmentation, but a
    flat section (SKILLS, LANGUAGES, ...) does not, so callers that scan
    a whole section's `.text` for content must strip it themselves first,
    or the heading text itself ("SKILLS", "LANGUAGES", ...) gets scanned
    as if it were real content.
    """
    if not raw_heading:
        return text
    stripped = text.lstrip()
    heading_norm = raw_heading.strip()
    if heading_norm and stripped.startswith(heading_norm):
        return stripped[len(heading_norm) :].lstrip("\n")
    return text
