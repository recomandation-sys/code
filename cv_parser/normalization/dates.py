"""Guarded date extraction (section 25).

Never let a fuzzy parser roam over arbitrary text. Candidate date
expressions are found with deterministic regex patterns first; only the
matched substrings are ever normalized. Precision is preserved exactly as
written — a bare year never gets a fabricated month, a month-year never
gets a fabricated day.
"""
from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel

from cv_parser.schemas.parser_response import PartialDate

_MONTH_LOOKUP: dict[str, int] = {
    "jan": 1, "january": 1, "janv": 1, "janvier": 1,
    "feb": 2, "february": 2, "fevr": 2, "févr": 2, "fevrier": 2, "février": 2,
    "mar": 3, "march": 3, "mars": 3,
    "apr": 4, "april": 4, "avr": 4, "avril": 4,
    "may": 5, "mai": 5,
    "jun": 6, "june": 6, "juin": 6,
    "jul": 7, "july": 7, "juil": 7, "juillet": 7,
    "aug": 8, "august": 8, "aout": 8, "août": 8,
    "sep": 9, "sept": 9, "september": 9, "septembre": 9,
    "oct": 10, "october": 10, "octobre": 10,
    "nov": 11, "november": 11, "novembre": 11,
    "dec": 12, "december": 12, "dec.": 12, "décembre": 12, "decembre": 12, "déc": 12,
}
# Longest-first so e.g. "septembre" isn't shadowed by a shorter prefix
# alternative when the regex engine tries alternatives left to right.
_MONTH_NAMES = sorted(_MONTH_LOOKUP.keys(), key=len, reverse=True)
_MONTH_PATTERN = "|".join(re.escape(m) for m in _MONTH_NAMES)

_CURRENT_TOKENS = [
    "present", "current", "now", "ongoing", "to date", "to present",
    "actuellement", "à ce jour", "en cours", "aujourd'hui", "à présent", "a present",
]
_CURRENT_PATTERN = "|".join(re.escape(t) for t in _CURRENT_TOKENS)

_YEAR = r"(19|20)\d{2}"
_SINGLE_DATE = (
    rf"(?:(?:0?[1-9]|1[0-2])[/.\-]{_YEAR})"  # 01/2022, 1-2022
    rf"|(?:(?:{_MONTH_PATTERN})\.?\s+{_YEAR})"  # Jan 2023, Novembre 2024
    rf"|(?:{_YEAR})"  # 2024
)
_RANGE_SEPARATOR = r"\s*(?:-|–|—|to|au|à)\s*"
# The start side also accepts a bare month name with no year of its own —
# "July - August 2024" is a common shared-year range where only the end
# carries the year; `find_date_range` borrows it for the start below.
_BARE_MONTH = rf"(?:{_MONTH_PATTERN})\.?"
_RANGE_RE = re.compile(
    rf"(?P<start>{_SINGLE_DATE}|{_BARE_MONTH})\s*{_RANGE_SEPARATOR}(?P<end>{_SINGLE_DATE}|{_CURRENT_PATTERN})",
    re.IGNORECASE,
)
_SINGLE_RE = re.compile(_SINGLE_DATE, re.IGNORECASE)
_CURRENT_ONLY_RE = re.compile(_CURRENT_PATTERN, re.IGNORECASE)


class DateRange(BaseModel):
    start: PartialDate | None = None
    end: PartialDate | None = None
    is_current: bool = False
    raw_text: str


def parse_single_date_token(token: str) -> PartialDate | None:
    """Normalize one already-isolated date token, preserving precision."""
    text = token.strip().lower().rstrip(".")

    m = re.fullmatch(r"(0?[1-9]|1[0-2])[/.\-]((?:19|20)\d{2})", text)
    if m:
        return PartialDate(year=int(m.group(2)), month=int(m.group(1)), precision="MONTH")

    m = re.fullmatch(rf"({_MONTH_PATTERN})\.?\s+((?:19|20)\d{{2}})", text, re.IGNORECASE)
    if m:
        month = _MONTH_LOOKUP.get(m.group(1).lower())
        if month is not None:
            return PartialDate(year=int(m.group(2)), month=month, precision="MONTH")

    m = re.fullmatch(r"((?:19|20)\d{2})", text)
    if m:
        return PartialDate(year=int(m.group(1)), precision="YEAR")

    return None


def find_date_range(text: str) -> DateRange | None:
    """Find the first plausible date expression in `text` (section 25).

    Tries a full range first ("2022 - 2024", "Jan 2023 - Present"); falls
    back to a single bare date (common for certifications: just "2024").
    Returns `None` rather than guessing when nothing matches — an absent
    date is always safer than an invented one (section 4.4).
    """
    if not text:
        return None

    match = _RANGE_RE.search(text)
    if match:
        start_raw = match.group("start")
        end_raw = match.group("end")
        is_current = bool(_CURRENT_ONLY_RE.fullmatch(end_raw.strip()))
        end = None if is_current else parse_single_date_token(end_raw)

        start = parse_single_date_token(start_raw)
        if start is None and end is not None and end.year is not None:
            # Bare month name on the start side, borrowing the end's year
            # (e.g. "July - August 2024" -> July shares August's 2024).
            month = _MONTH_LOOKUP.get(start_raw.strip().rstrip(".").lower())
            if month is not None:
                start = PartialDate(year=end.year, month=month, precision="MONTH")

        if start is not None:
            return DateRange(start=start, end=end, is_current=is_current, raw_text=match.group(0))

    match = _SINGLE_RE.search(text)
    if match:
        start = parse_single_date_token(match.group(0))
        if start is not None:
            return DateRange(start=start, end=None, is_current=False, raw_text=match.group(0))

    return None


def month_index(partial: PartialDate | None, *, end_of_period: bool) -> int | None:
    """Absolute month index (`year * 12 + month`) used only for internal
    duration arithmetic (section 26) — never surfaced as a fabricated
    field. Year-only precision is bounded to Jan (start) / Dec (end) *for
    this calculation alone*; the record's own `precision` is untouched.
    """
    if partial is None or partial.year is None:
        return None
    month = partial.month if partial.month is not None else (12 if end_of_period else 1)
    return partial.year * 12 + (month - 1)


def current_month_index(today: date | None = None) -> int:
    d = today or date.today()
    return d.year * 12 + (d.month - 1)
