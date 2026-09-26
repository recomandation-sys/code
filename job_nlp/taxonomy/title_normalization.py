"""Conservative occupation-title normalization for retrieval only.

The raw title remains part of the public evidence.  This helper is used only
when building a semantic query, so removing hiring metadata cannot erase the
title shown to users or alter deterministic field extraction.
"""
from __future__ import annotations

import html
import re
import unicodedata


_SENIORITY = re.compile(
    r"\b(?:senior|sr\.?|junior|jr\.?|mid[- ]level|midlevel|entry[- ]level|associate)\b",
    re.I,
)
_HIRING_METADATA = re.compile(
    r"\b(?:full[- ]?time|part[- ]?time|permanent|fixed[- ]term|temporary|freelance|contractor|"
    r"remote|hybrid|on[- ]?site|onsite|work from home|m/f|f/m|equal opportunity)\b",
    re.I,
)
_JOB_ID = re.compile(r"\b(?:job|req|requisition|vacancy|ref(?:erence)?)[ _:#-]*[A-Z0-9][A-Z0-9._-]{2,}\b", re.I)
_SALARY = re.compile(r"(?:[$€£]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:k|eur|usd|gbp))\b", re.I)
_HTML = re.compile(r"<[^>]+>")
_LOCATION = re.compile(
    r"\b(?:remote|hybrid|onsite|on-site|worldwide|europe|eu|uk|usa|united states|united kingdom|"
    r"france|germany|spain|italy|belgium|netherlands|tunisia|morocco|london|paris|barcelona|"
    r"brussels|amsterdam|berlin|madrid|casablanca|tunis)\b",
    re.I,
)


def normalize_occupation_title(title: str) -> str:
    """Return a retrieval-only title with hiring metadata removed.

    The operation is intentionally conservative: role nouns and technology
    tokens are preserved, while seniority, work arrangement, IDs, salary
    fragments, and known location suffixes are discarded.
    """
    text = html.unescape(unicodedata.normalize("NFKC", title or ""))
    text = _HTML.sub(" ", text)
    text = _JOB_ID.sub(" ", text)
    text = _SALARY.sub(" ", text)
    text = _SENIORITY.sub(" ", text)
    text = _HIRING_METADATA.sub(" ", text)
    # A location suffix after a separator is marketing metadata, not role
    # identity.  Only remove it when the suffix contains a known location.
    parts = re.split(r"\s*[|—–]\s*", text)
    if len(parts) > 1 and _LOCATION.search(parts[-1]):
        text = " ".join(parts[:-1])
    text = re.sub(r"\s*[,;/]\s*", " ", text)
    text = re.sub(r"[^\w+#.\- ]+", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" -|—–,;:/")
