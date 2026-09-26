"""Parse-quality scoring (sections 47-48).

Two related but distinct uses:
  - `score_parse_candidate` is a cheap, comparable score used only to pick
    the better of two candidate parses during adaptive retry (section 48)
    — it never leaves the pipeline.
  - `compute_parse_quality` builds the actual `ParseQuality` diagnostics
    object returned to the client, from the *final*, already-chosen parse.

Both intentionally avoid fake precision (section 45): every number here
is a simple, documented ratio, never a calibrated probability.
"""
from __future__ import annotations

import re

from cv_parser.config import settings
from cv_parser.schemas.internal import Document
from cv_parser.schemas.parser_response import (
    ExperienceSection,
    IdentitySection,
    ParseQuality,
    SkillsSection,
)
from cv_parser.structure.section_classifier import Section

_EXPERIENCE_RECORD_BEARING_TYPES = {"PROFESSIONAL_EXPERIENCE", "INTERNSHIP", "ALTERNANCE"}
_ALL_RECORD_BEARING_TYPES = _EXPERIENCE_RECORD_BEARING_TYPES | {"PROJECTS", "CERTIFICATIONS"}
_YEAR_TOKEN_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def count_year_like_tokens(document: Document) -> int:
    return sum(len(_YEAR_TOKEN_RE.findall(line.text)) for block in document.blocks for line in block.lines)


def score_parse_candidate(sections: list[Section]) -> float:
    """Higher is better. Rewards sections actually being classified and
    successfully segmented into records; penalizes leftover `UNKNOWN`
    sections — a rough proxy for "headings detected but no coherent
    sections" (section 48) so two reading-order attempts can be compared
    on more than just the column-interleaving metric alone.
    """
    if not sections:
        return 0.0

    classified = [s for s in sections if s.section_type not in ("HEADER", "UNKNOWN")]
    unknown = [s for s in sections if s.section_type == "UNKNOWN"]
    coverage = len(classified) / len(sections)
    unknown_ratio = len(unknown) / len(sections)
    record_bearing_with_records = sum(
        1 for s in sections if s.section_type in _ALL_RECORD_BEARING_TYPES and s.records
    )
    return coverage * 2.0 - unknown_ratio + 0.1 * record_bearing_with_records


def needs_adaptive_retry(document: Document, sections: list[Section], layout_status: str, experience: ExperienceSection) -> bool:
    """Retry triggers (section 48): interleaved columns, headings found
    but nothing coherent resulted, or a strong "many dates, zero
    experience records" mismatch that suggests reading order scrambled
    the experience section rather than the CV genuinely lacking one."""
    if layout_status == "POOR":
        return True
    if len(sections) <= 1:  # nothing beyond HEADER was ever segmented
        return True
    if not any(s.section_type not in ("HEADER", "UNKNOWN") for s in sections):
        return True
    if count_year_like_tokens(document) >= settings.adaptive_retry_min_year_tokens and not experience.records:
        return True
    return False


def compute_parse_quality(
    *,
    document: Document,
    sections: list[Section],
    layout_status: str,
    reading_strategy: str,
    identity: IdentitySection,
    experience: ExperienceSection,
    skills: SkillsSection,
    base_warnings: list[str],
) -> ParseQuality:
    warnings = list(base_warnings)

    classified = [s for s in sections if s.section_type not in ("HEADER", "UNKNOWN")]
    unknown = [s for s in sections if s.section_type == "UNKNOWN"]
    section_coverage = len(classified) / len(sections) if sections else None
    unknown_ratio = len(unknown) / len(sections) if sections else None

    # Orphan ratio (section 47): share of document words that landed in a
    # section we could not classify at all — words are "real" but
    # structurally orphaned, the closest deterministic analogue to a
    # semantic "orphan text ratio" this architecture can measure.
    total_words = len(document.words)
    orphan_words = sum(len(line.words) for s in unknown for line in _section_lines(document, s))
    orphan_ratio = round(orphan_words / total_words, 4) if total_words else None

    # Record coherence (section 46/47): fraction of raw record spans
    # (experience-type sections only, where confidence is tracked) that
    # survived as real, non-degenerate experience records.
    total_spans = sum(len(s.records) for s in sections if s.section_type in _EXPERIENCE_RECORD_BEARING_TYPES)
    record_coherence = round(len(experience.records) / total_spans, 4) if total_spans else None

    if unknown:
        warnings.append(f"UNKNOWN_SECTIONS_{len(unknown)}")
    if identity.full_name is None:
        warnings.append("MISSING_FULL_NAME")
    if identity.email is None:
        warnings.append("MISSING_EMAIL")
    if len(skills.known) > settings.quality_suspicious_skill_count:
        warnings.append("SUSPICIOUS_SKILL_COUNT")
    if _has_duplicate_records(experience):
        warnings.append("DUPLICATE_EXPERIENCE_RECORDS")
    if _has_incoherent_dates(experience):
        warnings.append("DATE_INCOHERENT_RECORD")

    is_empty_result = (
        identity.full_name is None
        and identity.email is None
        and not experience.records
        and not skills.known
    )
    if is_empty_result:
        warnings.append("EMPTY_PARSE_RESULT")

    status = "GOOD"
    if (
        is_empty_result
        or layout_status == "POOR"
        or document.overall_page_state != "DIGITAL_GOOD"
        or (section_coverage is not None and section_coverage < settings.quality_min_section_coverage_good)
        or (unknown_ratio is not None and unknown_ratio > settings.quality_max_unknown_ratio_good)
    ):
        status = "FAIR"
    if is_empty_result or (section_coverage is not None and section_coverage == 0):
        status = "POOR"

    return ParseQuality(
        status=status,
        section_coverage=round(section_coverage, 4) if section_coverage is not None else None,
        orphan_ratio=orphan_ratio,
        record_coherence=record_coherence,
        warnings=warnings,
    )


def _section_lines(document: Document, section: Section):
    lines_by_id = {line.id: line for block in document.blocks for line in block.lines}
    return [lines_by_id[lid] for lid in section.line_ids if lid in lines_by_id]


def _has_duplicate_records(experience: ExperienceSection) -> bool:
    seen: set[tuple[str, str | None]] = set()
    for record in experience.records:
        key = (record.type, (record.raw_text or "").strip().lower())
        if key in seen:
            return True
        seen.add(key)
    return False


def _has_incoherent_dates(experience: ExperienceSection) -> bool:
    for record in experience.records:
        if record.is_current or record.start_date is None or record.end_date is None:
            continue
        if record.start_date.year is None or record.end_date.year is None:
            continue
        start = (record.start_date.year, record.start_date.month or 1)
        end = (record.end_date.year, record.end_date.month or 12)
        if end < start:
            return True
    return False
