"""Top-level CV Skill Engine — Nesta + Tech Taxonomy V2 across CV sections.

Walks classified sections (skills, experience, projects, education, …),
runs the same ``EnSkillStack`` used for job offers on each text blob, and
aggregates grounded evidence. Optional lexicon hybrid can merge legacy
exact tech matches.
"""
from __future__ import annotations

from cv_parser.config import settings
from cv_parser.normalization.text import strip_heading_line
from cv_parser.schemas.parser_response import SkillEvidenceSourceType, SkillsSection
from cv_parser.skills.candidates import resolve_tech_list_candidates
from cv_parser.skills.evidence import SkillHit, UnmappedHit, aggregate_known_skills, aggregate_unmapped
from cv_parser.skills.matcher import match_text
from cv_parser.skills.models import RawSkillMatch
from cv_parser.skills.nesta_tech_v2 import extract_blob_skills
from cv_parser.skills.normalization import find_tech_list_label_span
from cv_parser.structure.section_classifier import Section

# Every CV part that can carry skill evidence (including education / other).
# LANGUAGES / CONTACT-like types stay out — spoken languages are not skills.
_SECTION_TO_SOURCE_TYPE: dict[str, SkillEvidenceSourceType] = {
    "SKILLS": "SKILLS_SECTION",
    "PROFESSIONAL_EXPERIENCE": "PROFESSIONAL_EXPERIENCE",
    "INTERNSHIP": "INTERNSHIP",
    "ALTERNANCE": "ALTERNANCE",
    "PROJECTS": "PROJECT",
    "CERTIFICATIONS": "CERTIFICATION",
    "PROFILE_SUMMARY": "PROFILE",
    "EDUCATION": "EDUCATION",
    "UNKNOWN": "OTHER",
}
_RECORD_BEARING_TYPES = {
    "PROFESSIONAL_EXPERIENCE",
    "INTERNSHIP",
    "ALTERNANCE",
    "PROJECTS",
    "CERTIFICATIONS",
    "EDUCATION",
}

_SOURCE_TYPE_LABELS: dict[SkillEvidenceSourceType, str] = {
    "SKILLS_SECTION": "Skills section",
    "PROFESSIONAL_EXPERIENCE": "Professional experience",
    "INTERNSHIP": "Internship",
    "ALTERNANCE": "Alternance",
    "PROJECT": "Project",
    "CERTIFICATION": "Certification",
    "PROFILE": "Profile summary",
    "EDUCATION": "Education",
    "OTHER": "Other section",
}

_RECORD_PREFIX: dict[SkillEvidenceSourceType, str] = {
    "PROFESSIONAL_EXPERIENCE": "Experience",
    "INTERNSHIP": "Internship",
    "ALTERNANCE": "Alternance",
    "PROJECT": "Project",
    "CERTIFICATION": "Certification",
    "EDUCATION": "Education",
}


def _clean_record_label(raw: str, *, max_len: int = 72) -> str:
    line = raw.split("\n", 1)[0].strip(" •|-–—\t")
    if len(line) > max_len:
        line = line[:max_len].rsplit(" ", 1)[0]
    return line


def _source_label(section: Section, source_type: SkillEvidenceSourceType, source_id: str) -> str:
    if section.section_type == "SKILLS":
        return "Skills section"
    if section.section_type == "PROFILE_SUMMARY":
        return "Profile summary"
    if section.section_type == "UNKNOWN":
        return "Other section"

    for record in section.records:
        if record.id != source_id:
            continue
        label = _clean_record_label(record.anchor_text or record.raw_text)
        prefix = _RECORD_PREFIX.get(source_type)
        if prefix and label:
            return f"{prefix}: {label}"
        return label or _SOURCE_TYPE_LABELS[source_type]

    return _SOURCE_TYPE_LABELS.get(source_type, source_type.replace("_", " ").title())


def _text_blobs(section: Section) -> list[tuple[str, str]]:
    """(text, source_id) pairs — one per record when segmented, else full section."""
    if section.section_type in _RECORD_BEARING_TYPES and section.records:
        return [(record.raw_text, record.id) for record in section.records if record.raw_text.strip()]
    text = strip_heading_line(section.text, section.raw_heading)
    if text.strip():
        return [(text, section.id)]
    return []


def _tech_list_regions(text: str, *, whole_text_is_list: bool) -> list[tuple[int, int]]:
    regions: list[tuple[int, int]] = []
    offset = 0
    for line in text.split("\n"):
        found = find_tech_list_label_span(line)
        if found is not None:
            _remainder, local_start, local_end = found
            regions.append((offset + local_start, offset + local_end))
        elif whole_text_is_list and line.strip():
            regions.append((offset, offset + len(line)))
        offset += len(line) + 1
    return regions


def _matches_overlapping(matches: list[RawSkillMatch], start: int, end: int) -> list[RawSkillMatch]:
    local: list[RawSkillMatch] = []
    for m in matches:
        if m.start < end and start < m.end:
            local.append(
                RawSkillMatch(
                    skill_id=m.skill_id,
                    canonical_name=m.canonical_name,
                    category=m.category,
                    alias_text=m.alias_text,
                    policy=m.policy,
                    start=max(0, m.start - start),
                    end=min(end - start, m.end - start),
                )
            )
    return local


def _lexicon_hits(
    text: str,
    *,
    source_type: SkillEvidenceSourceType,
    source_id: str,
    source_label: str,
    in_skills_section: bool,
) -> tuple[list[SkillHit], list[UnmappedHit]]:
    known_hits: list[SkillHit] = []
    unmapped_hits: list[UnmappedHit] = []
    exact_matches = match_text(text, in_skills_section=in_skills_section)
    for m in exact_matches:
        known_hits.append(
            SkillHit(
                skill_id=m.skill_id,
                canonical_name=m.canonical_name,
                category=m.category,
                raw_text=text[m.start : m.end],
                source_type=source_type,
                source_id=source_id,
                source_label=source_label,
            )
        )
    for region_start, region_end in _tech_list_regions(text, whole_text_is_list=in_skills_section):
        region_text = text[region_start:region_end]
        local_matches = _matches_overlapping(exact_matches, region_start, region_end)
        recovered, unmapped_raw = resolve_tech_list_candidates(region_text, local_matches)
        for rec in recovered:
            known_hits.append(
                SkillHit(
                    skill_id=rec.skill_id,
                    canonical_name=rec.canonical_name,
                    category=rec.category,
                    raw_text=rec.raw_text,
                    source_type=source_type,
                    source_id=source_id,
                    source_label=source_label,
                )
            )
        for raw_name in unmapped_raw:
            unmapped_hits.append(
                UnmappedHit(
                    raw_name=raw_name,
                    source_type=source_type,
                    source_id=source_id,
                    source_label=source_label,
                )
            )
    return known_hits, unmapped_hits


def extract_skills(sections: list[Section]) -> SkillsSection:
    """Extract skills from every relevant CV section via Nesta+Tech V2 (default)."""
    known_hits: list[SkillHit] = []
    unmapped_hits: list[UnmappedHit] = []
    mode = (settings.skill_engine or "nesta_tech_v2").strip().lower()

    for section in sections:
        source_type = _SECTION_TO_SOURCE_TYPE.get(section.section_type)
        if source_type is None:
            continue
        in_skills_section = section.section_type == "SKILLS"

        for text, source_id in _text_blobs(section):
            source_label = _source_label(section, source_type, source_id)

            if mode in ("nesta_tech_v2", "hybrid"):
                known_hits.extend(
                    extract_blob_skills(
                        text,
                        source_type=source_type,
                        source_id=source_id,
                        source_label=source_label,
                    )
                )

            if mode in ("lexicon", "hybrid"):
                lex_known, lex_unmapped = _lexicon_hits(
                    text,
                    source_type=source_type,
                    source_id=source_id,
                    source_label=source_label,
                    in_skills_section=in_skills_section,
                )
                known_hits.extend(lex_known)
                unmapped_hits.extend(lex_unmapped)

    return SkillsSection(
        known=aggregate_known_skills(known_hits),
        unmapped_technology_candidates=aggregate_unmapped(unmapped_hits),
    )


    )
