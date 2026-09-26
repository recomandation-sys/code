"""Experience records and union-duration calculation (sections 24, 26).

Records come straight from Phase C's `RecordSpan`s inside
PROFESSIONAL_EXPERIENCE / INTERNSHIP / ALTERNANCE sections — this module
only attaches a parsed date range and a cleaned title to each one. Overlap
handling is the whole point of section 26: two overlapping records of the
*different* types are never summed together, and even same-type
overlapping records are unioned, never double-counted.
"""
from __future__ import annotations

from collections import defaultdict

from cv_parser.config import settings
from cv_parser.normalization.dates import current_month_index, find_date_range, month_index
from cv_parser.schemas.parser_response import Confidence, ExperienceRecord, ExperienceSection, ExperienceType
from cv_parser.structure.section_classifier import Section

_SECTION_TYPE_TO_EXPERIENCE_TYPE: dict[str, ExperienceType] = {
    "PROFESSIONAL_EXPERIENCE": "PROFESSIONAL",
    "INTERNSHIP": "INTERNSHIP",
    "ALTERNANCE": "ALTERNANCE",
}


def _clean_title(anchor_text: str, date_raw_text: str | None) -> str | None:
    text = anchor_text.strip()
    if date_raw_text and date_raw_text in text:
        text = text.replace(date_raw_text, "").strip(" -–—|,:\t")
    return text or None


def _has_meaningful_title(title: str | None) -> bool:
    return bool(title) and len(title.split()) >= settings.record_meaningful_title_min_words


def _has_body(raw_text: str, anchor_text: str) -> bool:
    """More substance than just the anchor/title line itself (section 46:
    coherence, not merely "segmentation code ran successfully")."""
    lines = [l for l in raw_text.split("\n") if l.strip()]
    non_anchor_lines = [l for l in lines if l.strip() != anchor_text.strip()]
    return len(lines) >= settings.record_meaningful_body_min_lines and bool(non_anchor_lines)


def _record_signals(has_date: bool, has_title: bool, has_body: bool) -> tuple[Confidence, bool]:
    """(confidence, is_degenerate). A record is degenerate — and must not
    exist at all — only when *none* of date/title/body carry any real
    evidence (section 46: "a section heading alone with no title/date/body
    MUST NOT become an experience record"). Otherwise, confidence reflects
    how many of the three signals actually support it; a parsed date alone
    is never enough for HIGH on its own — coherence needs corroborating
    title or body content too.
    """
    if not (has_date or has_title or has_body):
        return "LOW", True
    if has_date and (has_title or has_body):
        return "HIGH", False
    return "MEDIUM", False


def extract_experience_records(sections: list[Section]) -> list[ExperienceRecord]:
    records: list[ExperienceRecord] = []
    for section in sections:
        experience_type = _SECTION_TYPE_TO_EXPERIENCE_TYPE.get(section.section_type)
        if experience_type is None:
            continue
        for i, record_span in enumerate(section.records):
            date_range = find_date_range(record_span.raw_text)
            title = _clean_title(record_span.anchor_text, date_range.raw_text if date_range else None)

            confidence, is_degenerate = _record_signals(
                has_date=date_range is not None and date_range.start is not None,
                has_title=_has_meaningful_title(title),
                has_body=_has_body(record_span.raw_text, record_span.anchor_text),
            )
            if is_degenerate:
                continue

            records.append(
                ExperienceRecord(
                    id=f"{section.id}_{i:03d}",
                    type=experience_type,
                    title=title,
                    start_date=date_range.start if date_range else None,
                    end_date=None if (date_range and date_range.is_current) else (date_range.end if date_range else None),
                    is_current=bool(date_range and date_range.is_current),
                    raw_text=record_span.raw_text,
                    technologies=[],  # populated by the IT Skill Engine (Phase E)
                    confidence=confidence,
                )
            )
    return records


def _effective_month_range(record: ExperienceRecord) -> tuple[int, int] | None:
    start_idx = month_index(record.start_date, end_of_period=False)
    if start_idx is None:
        return None

    if record.is_current:
        # Only an explicit "Present/current" signal extends a record to
        # today for duration purposes. A record that simply has no parsed
        # end date is *unknown*, not necessarily ongoing — extending it to
        # "now" would fabricate months that were never actually claimed.
        end_idx = current_month_index()
    elif record.end_date is not None:
        end_idx = month_index(record.end_date, end_of_period=True)
        if end_idx is None:
            end_idx = start_idx
    else:
        end_idx = start_idx

    if end_idx < start_idx:
        end_idx = start_idx
    return start_idx, end_idx


def union_duration_months(records: list[ExperienceRecord]) -> dict[ExperienceType, int]:
    """Union of intervals *per type* (section 26): overlapping records of
    the same type are merged before summing; different types are always
    kept in separate totals, however much their date ranges overlap."""
    by_type: dict[ExperienceType, list[tuple[int, int]]] = defaultdict(list)
    for record in records:
        span = _effective_month_range(record)
        if span is not None:
            by_type[record.type].append(span)

    totals: dict[ExperienceType, int] = {}
    for experience_type, spans in by_type.items():
        spans.sort()
        merged: list[list[int]] = []
        for start, end in spans:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        totals[experience_type] = sum(end - start + 1 for start, end in merged)
    return totals


def extract_experience(sections: list[Section]) -> ExperienceSection:
    records = extract_experience_records(sections)
    durations = union_duration_months(records)
    return ExperienceSection(
        professional_months=durations.get("PROFESSIONAL", 0),
        internship_months=durations.get("INTERNSHIP", 0),
        alternance_months=durations.get("ALTERNANCE", 0),
        freelance_months=durations.get("FREELANCE", 0),
        records=records,
    )
