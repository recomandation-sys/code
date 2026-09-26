"""Identity extraction: email and full name (section 21).

Email is a simple validated-pattern scan of the whole document. Full name
deliberately does **not** use generic NER — candidates are generated only
from the header/preamble region (section 21: "first structural header
region"), filtered by formal evidence (short line, plausible name-shaped
tokens, not contact info, not a known occupation word, not a real section
heading), and scored by relative font size/boldness.
"""
from __future__ import annotations

import re

from cv_parser.schemas.internal import Document
from cv_parser.extractors.location import extract_country, extract_phone
from cv_parser.schemas.parser_response import Confidence, ConfidentValue, IdentitySection
from cv_parser.structure.heading_detector import compute_baseline_font_size
from cv_parser.structure.section_classifier import Section, classify_heading_text

_EMAIL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+\-]{0,63}@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

_URL_RE = re.compile(r"(https?://|www\.)\S+|\b[\w\-]+\.(com|net|org|io|dev|co|fr|tn)\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(\+?\d[\d\s().\-]{6,}\d)")
# A "name token" is a single alphabetic word, optionally with an
# apostrophe/hyphen, and optionally ending in a period (common for
# abbreviated middle names/initials, e.g. "SYED ABUTHAHEER. N"). Casing
# is deliberately NOT required to be capitalized-first: some CV design
# templates render a header name with unconventional casing per word
# (e.g. "Agin sathiya"), and this check already only ever runs on a
# short line already chosen as the header's single largest/boldest
# candidate, having already passed the contact-line, occupation-phrase,
# and real-section-heading filters below — so it does not need to also
# carry the "is this shaped like a name" burden alone.
_NAME_TOKEN_RE = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'\-]*\.?$")

# A curated (not exhaustive) list of common IT/generic occupation words,
# used only to reject header lines that are clearly a job-title headline
# rather than a name (section 21: "not obvious IT occupation phrase").
_OCCUPATION_WORDS = {
    "developer", "engineer", "manager", "analyst", "designer", "consultant", "architect",
    "student", "intern", "specialist", "administrator", "scientist", "technician", "director",
    "full-stack", "frontend", "backend", "devops", "freelance", "freelancer",
    "développeur", "développeuse", "ingénieur", "ingénieure", "stagiaire",
    "étudiant", "étudiante", "analyste", "responsable", "technicien", "technicienne",
}


def _is_valid_email(candidate: str) -> bool:
    if ".." in candidate:
        return False
    local, _, domain = candidate.partition("@")
    if not local or not domain:
        return False
    if local.startswith(".") or local.endswith("."):
        return False
    if domain.startswith("-") or domain.startswith("."):
        return False
    return True


def extract_email(document: Document) -> ConfidentValue | None:
    found: list[str] = []
    for block in document.blocks:
        for line in block.lines:
            for match in _EMAIL_RE.finditer(line.text):
                candidate = match.group(0).strip(".,;:()<>[]")
                if _is_valid_email(candidate):
                    found.append(candidate)

    if not found:
        return None

    deduped: list[str] = []
    seen_lower: set[str] = set()
    for candidate in found:
        if candidate.lower() not in seen_lower:
            seen_lower.add(candidate.lower())
            deduped.append(candidate)

    reason_codes = ["MULTIPLE_EMAILS_FOUND"] if len(deduped) > 1 else []
    return ConfidentValue(
        value=deduped[0], confidence="HIGH", method="VALIDATED_EMAIL_PATTERN", reason_codes=reason_codes
    )


def _looks_like_contact_line(text: str) -> bool:
    return "@" in text or bool(_URL_RE.search(text)) or bool(_PHONE_RE.search(text))


def _looks_like_occupation_phrase(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in _OCCUPATION_WORDS)


def _looks_like_name_tokens(tokens: list[str]) -> bool:
    if not (1 <= len(tokens) <= 5):
        return False
    return all(_NAME_TOKEN_RE.match(t) for t in tokens)


def extract_full_name(document: Document, sections: list[Section]) -> ConfidentValue | None:
    header = next((s for s in sections if s.section_type == "HEADER"), None)
    if header is None or not header.line_ids:
        return None

    baseline = compute_baseline_font_size(document)
    lines_by_id = {line.id: line for block in document.blocks for line in block.lines}

    best_text: str | None = None
    best_score = -1.0
    for line_id in header.line_ids:
        line = lines_by_id.get(line_id)
        if line is None or line.page != 0:
            continue
        text = line.text.strip()
        if not text or _looks_like_contact_line(text) or _looks_like_occupation_phrase(text):
            continue
        tokens = text.split()
        if not _looks_like_name_tokens(tokens):
            continue
        _section_type, method, _score = classify_heading_text(text)
        if method != "UNKNOWN":
            continue  # a real (if coincidentally short/bold) section heading, not a name

        relative_size = (line.median_font_size or baseline) / baseline if baseline else 1.0
        score = relative_size + (0.5 if line.bold_ratio >= 0.5 else 0.0)
        if score > best_score:
            best_score = score
            best_text = text

    if best_text is None:
        return None

    reason_codes = ["HEADER_REGION"]
    if best_score >= 1.3:
        confidence: Confidence = "HIGH"
        reason_codes.append("LARGEST_HEADER_LINE")
    else:
        confidence = "MEDIUM"
    return ConfidentValue(
        value=best_text, confidence=confidence, method="HEADER_REGION_CANDIDATE", reason_codes=reason_codes
    )


def extract_identity(document: Document, sections: list[Section]) -> IdentitySection:
    country = extract_country(document, sections)
    return IdentitySection(
        full_name=extract_full_name(document, sections),
        email=extract_email(document),
        phone=extract_phone(document, sections),
        country=country,
    )
