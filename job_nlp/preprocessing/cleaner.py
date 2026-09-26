"""Deterministic text cleaning for title/description (training == production)."""
from __future__ import annotations

import html
import re
import unicodedata

_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WS_RE = re.compile(r"[ \t\f\v]+")
_NL_RE = re.compile(r"\n{3,}")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().\-]{7,}\d(?!\w)")


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def clean_text(text: str | None) -> str:
    if text is None:
        return ""
    text = str(text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = normalize_unicode(text)
    text = _CONTROL_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return text.strip()


def clean_title(title: str | None) -> str:
    return clean_text(title)


def clean_description(description: str | None) -> str:
    return clean_text(description)


def clean_display_description(description: str | None) -> str:
    """Make a readable display string without contact details or markup."""
    text = clean_text(description)
    text = text.replace("\\n", " ").replace("\n", " ")
    text = _EMAIL_RE.sub("", text)
    text = _PHONE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()
