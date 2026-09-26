"""Country and phone extraction from the header/contact region (section 21).

Scans page-0 contact lines for an explicit country name or a phone prefix that
maps to a country. City names are intentionally not stored.
"""
from __future__ import annotations

import re

from cv_parser.schemas.internal import Document
from cv_parser.schemas.parser_response import ConfidentValue
from cv_parser.structure.section_classifier import Section

_EMAIL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+\-]{0,63}@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().\-]{6,}\d)")
_URL_RE = re.compile(r"(https?://|www\.)\S+|\b[\w\-]+\.(com|net|org|io|dev|co|fr|tn)\b", re.IGNORECASE)

_COUNTRY_NAMES: dict[str, str] = {
    "tunisia": "Tunisia",
    "tunisie": "Tunisia",
    "france": "France",
    "germany": "Germany",
    "allemagne": "Germany",
    "united states": "United States",
    "usa": "United States",
    "canada": "Canada",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "spain": "Spain",
    "espagne": "Spain",
    "italy": "Italy",
    "italie": "Italy",
    "belgium": "Belgium",
    "belgique": "Belgium",
    "morocco": "Morocco",
    "maroc": "Morocco",
    "algeria": "Algeria",
    "algérie": "Algeria",
    "algerie": "Algeria",
}

_PHONE_COUNTRY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("+216", "Tunisia"),
    ("+33", "France"),
    ("+49", "Germany"),
    ("+1", "United States"),
    ("+44", "United Kingdom"),
    ("+34", "Spain"),
    ("+39", "Italy"),
    ("+32", "Belgium"),
    ("+212", "Morocco"),
    ("+213", "Algeria"),
)

_LOCATION_LABELS = (
    "location",
    "address",
    "adresse",
    "based in",
    "basé à",
    "base a",
)


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw.strip())
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+") and len(re.sub(r"\D", "", digits)) >= 8:
        return raw.strip()
    return digits if digits.startswith("+") else raw.strip()


def _is_contact_line(text: str) -> bool:
    lowered = text.lower()
    return (
        "@" in text
        or bool(_PHONE_RE.search(text))
        or "|" in text
        or any(label in lowered for label in _LOCATION_LABELS)
    )


def _header_lines(document: Document, sections: list[Section]) -> list[str]:
    lines: list[str] = []
    header = next((s for s in sections if s.section_type == "HEADER"), None)
    if header is not None:
        lines_by_id = {line.id: line for block in document.blocks for line in block.lines}
        for line_id in header.line_ids:
            line = lines_by_id.get(line_id)
            if line is not None and line.page == 0 and line.text.strip():
                lines.append(line.text.strip())

    if not lines:
        for block in document.blocks:
            for line in block.lines:
                if line.page == 0 and _is_contact_line(line.text):
                    lines.append(line.text.strip())
    return lines


def _contact_lines(document: Document, sections: list[Section]) -> list[str]:
    contact = [line for line in _header_lines(document, sections) if _is_contact_line(line)]
    if contact:
        return contact

    for block in document.blocks:
        for line in block.lines:
            if line.page == 0 and _is_contact_line(line.text):
                text = line.text.strip()
                if text and text not in contact:
                    contact.append(text)
    return contact


def _segment_is_location(segment: str) -> bool:
    text = segment.strip(" .:;-–—|\t")
    if not text or len(text) > 80:
        return False
    if _EMAIL_RE.search(text) or _URL_RE.search(text) or _PHONE_RE.fullmatch(text.strip()):
        return False
    lowered = text.lower()
    if any(label in lowered for label in ("e-mail", "email", "phone", "tel", "mobile", "linkedin")):
        return False
    return True


def _find_country(text: str) -> str | None:
    lowered = text.lower()
    for needle, canonical in sorted(_COUNTRY_NAMES.items(), key=lambda item: -len(item[0])):
        if needle in lowered:
            return canonical
    return None


def _country_from_phone(phone: str) -> str | None:
    normalized = re.sub(r"[\s().\-]", "", phone)
    for prefix, country in sorted(_PHONE_COUNTRY_PREFIXES, key=lambda item: -len(item[0])):
        if normalized.startswith(prefix):
            return country
    return None


def _parse_country_from_segment(segment: str) -> str | None:
    text = segment.strip(" .:;-–—|\t")
    if not text:
        return None

    for label in _LOCATION_LABELS:
        if text.lower().startswith(f"{label}:"):
            text = text.split(":", 1)[1].strip()
            break
        if text.lower().startswith(f"{label} "):
            text = text[len(label) :].strip(" :")
            break

    country = _find_country(text)
    if "," in text:
        _city_part, country_part = [part.strip() for part in text.split(",", 1)]
        return country or _find_country(country_part) or (
            country_part if country_part and country_part[0].isupper() and _find_country(country_part) is None and len(country_part.split()) <= 3 else None
        )

    return country


def extract_phone(document: Document, sections: list[Section]) -> ConfidentValue | None:
    candidates: list[str] = []
    for text in _contact_lines(document, sections):
        for match in _PHONE_RE.finditer(text):
            phone = _normalize_phone(match.group(0))
            if len(re.sub(r"\D", "", phone)) >= 8:
                candidates.append(phone)

    if not candidates:
        return None

    reason_codes = ["MULTIPLE_PHONES_FOUND"] if len(candidates) > 1 else ["HEADER_CONTACT_LINE"]
    return ConfidentValue(
        value=candidates[0],
        confidence="HIGH",
        method="HEADER_PHONE_PATTERN",
        reason_codes=reason_codes,
    )


def extract_country(document: Document, sections: list[Section]) -> ConfidentValue | None:
    country_value: str | None = None
    method = "HEADER_CONTACT_LINE"
    reason_codes: list[str] = []

    for text in _contact_lines(document, sections):
        segments = [text] if "|" not in text else [part.strip() for part in text.split("|")]
        for segment in segments:
            if not _segment_is_location(segment):
                continue
            country = _parse_country_from_segment(segment)
            if country and country_value is None:
                country_value = country

    phone_field = extract_phone(document, sections)
    if country_value is None and phone_field and phone_field.value:
        inferred = _country_from_phone(phone_field.value)
        if inferred:
            country_value = inferred
            method = "PHONE_COUNTRY_PREFIX"
            reason_codes.append("COUNTRY_FROM_PHONE_PREFIX")

    if not country_value:
        return None

    return ConfidentValue(
        value=country_value,
        confidence="HIGH",
        method=method,
        reason_codes=reason_codes,
    )
