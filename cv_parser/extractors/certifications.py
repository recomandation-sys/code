"""Certification grouping and technology evidence (section 44).

Certifications come from Phase C's `RecordSpan`s inside the
`CERTIFICATIONS` section, same as experience records. Each one gets: a
cleaned name, an issuer *only* when a well-known certification body is
explicitly named (never guessed), a single issue date when one is
present, and technology evidence from the same deterministic skill
matcher used everywhere else — never "infer many AWS subskills from one
AWS certification" (section 44), just whatever technologies are actually
named in the certification's own text.
"""
from __future__ import annotations

import re

from cv_parser.normalization.dates import find_date_range
from cv_parser.schemas.parser_response import CertificationEntry
from cv_parser.skills.matcher import match_text
from cv_parser.structure.section_classifier import Section

# Curated, deliberately small: well-known certification-issuing bodies.
# A substring match here is safe (proper nouns, low ambiguity) — this is
# not an attempt to be exhaustive, just to avoid ever fabricating an
# issuer that was not actually named.
_KNOWN_ISSUERS: list[tuple[str, str]] = [
    ("amazon web services", "AWS"),
    ("aws", "AWS"),
    ("microsoft", "Microsoft"),
    ("google cloud", "Google"),
    ("google", "Google"),
    ("cisco", "Cisco"),
    ("comptia", "CompTIA"),
    ("oracle", "Oracle"),
    ("ibm", "IBM"),
    ("pmi", "PMI"),
    ("project management institute", "PMI"),
    ("scrum.org", "Scrum.org"),
    ("scrum alliance", "Scrum Alliance"),
    ("scaled agile", "Scaled Agile"),
    ("istqb", "ISTQB"),
    ("linux foundation", "Linux Foundation"),
    ("hashicorp", "HashiCorp"),
    ("salesforce", "Salesforce"),
    ("sap", "SAP"),
    ("adobe", "Adobe"),
    ("coursera", "Coursera"),
    ("udemy", "Udemy"),
    ("edx", "edX"),
    ("meta", "Meta"),
    ("databricks", "Databricks"),
    ("snowflake", "Snowflake"),
    ("red hat", "Red Hat"),
    ("vmware", "VMware"),
    ("juniper", "Juniper"),
    ("fortinet", "Fortinet"),
    ("palo alto networks", "Palo Alto Networks"),
    ("ec-council", "EC-Council"),
    ("isaca", "ISACA"),
    ("axelos", "AXELOS"),
    ("itil", "AXELOS"),
    ("cncf", "CNCF"),
]

_TRAILING_PUNCT_RE = re.compile(r"^[\s\-\u2013\u2014|,:]+|[\s\-\u2013\u2014|,:]+$")


def _detect_issuer(text: str) -> str | None:
    lowered = text.lower()
    for needle, canonical in _KNOWN_ISSUERS:
        if needle in lowered:
            return canonical
    return None


def _clean_name(anchor_text: str, date_raw_text: str | None) -> str:
    text = anchor_text.strip()
    if date_raw_text and date_raw_text in text:
        text = text.replace(date_raw_text, "")
    return _TRAILING_PUNCT_RE.sub("", text).strip() or anchor_text.strip()


def extract_certifications(sections: list[Section]) -> list[CertificationEntry]:
    certifications: list[CertificationEntry] = []

    for section in sections:
        if section.section_type != "CERTIFICATIONS":
            continue

        for i, record in enumerate(section.records):
            date_range = find_date_range(record.raw_text)
            name = _clean_name(record.anchor_text, date_range.raw_text if date_range else None)
            issuer = _detect_issuer(record.raw_text)
            technology_evidence = list(
                dict.fromkeys(m.canonical_name for m in match_text(record.raw_text, in_skills_section=False))
            )

            certifications.append(
                CertificationEntry(
                    id=f"{section.id}_{i:03d}",
                    name=name,
                    issuer=issuer,
                    date=date_range.start if date_range else None,
                    technology_evidence=technology_evidence,
                )
            )

    return certifications
