"""Section classification (section 18) and boundary resolution (section 19).

Three layers, tried in order, on each detected heading:

  A. exact multilingual alias match (resource-driven, no code change to add
     a language pack)
  B. strict RapidFuzz match against the same alias list, high cutoff only
  C. structural content signature, only when A and B both fail

A section spans from one heading line (inclusive) up to the next heading
line (exclusive) in the already-linearized reading order — so "the next
peer heading" never depends on section order (section 19). Boundaries are
resolved at the *line* level, not the block level: Phase A/B's paragraph
builder is deliberately conservative about splitting blocks, so on many
real CVs a whole run of sections (e.g. "Profile" body text immediately
followed by an "Education" heading) ends up inside a single block. Only
looking at block boundaries would make every non-first heading in such a
block invisible.
"""
from __future__ import annotations

import functools
import json
import re
import unicodedata

from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from cv_parser.config import RESOURCES_DIR, settings
from cv_parser.document.models import Line
from cv_parser.schemas.internal import Document
from cv_parser.structure.heading_detector import (
    HeadingCandidate,
    compute_baseline_font_size,
    detect_headings,
    style_signature,
)
from cv_parser.structure.record_segmenter import RecordSpan, segment_records
from cv_parser.structure.section_signatures import SectionType, classify_by_signature

_RECORD_BEARING_TYPES = {"PROFESSIONAL_EXPERIENCE", "INTERNSHIP", "ALTERNANCE", "PROJECTS", "CERTIFICATIONS"}
# Education entries (degree titles) are just as heading-shaped as
# experience/project titles, so they need the same "fold, don't fragment"
# treatment at section-boundary time — even though education content
# itself is intentionally not turned into structured records (section
# 2.2: full education history is out of scope).
_FOLD_ELIGIBLE_TYPES = _RECORD_BEARING_TYPES | {"EDUCATION"}
_HEADER_RECLASSIFY_LINE_THRESHOLD = 6

# A curated (not exhaustive) list of record-internal sub-headings —
# extremely common inside a single experience/project/education entry
# ("Responsibilities:", "Key Result Areas", ...) — that must never split
# a fold-eligible section into a new top-level section just because they
# happen to share the section's confirmed heading style (section 46: a
# record's own sub-heading is not a document-level section boundary).
# Some of these (achievements, strengths, references, declaration) are
# ALSO legitimate standalone top-level headings elsewhere in the same CV
# (see the "IGNORED" alias pack) — this set only wins when the line
# occurs *inside* a fold-eligible section, so an exact alias match still
# applies everywhere else.
_RECORD_SUBHEADING_DENYLIST = {
    "responsibilities", "roles and responsibilities", "roles & responsibilities",
    "key responsibilities", "job responsibilities", "duties", "job profile",
    "key result areas", "kra", "role", "roles", "highlights", "project details",
    "responsibility", "job description", "description",
    "achievements", "achievement", "strengths", "strength", "references", "reference", "declaration",
}

# A short "Label : already-filled-in value" line (e.g. "Nationality :
# Indian", "Marital Status : Single") is a personal-detail data row, not
# a heading, however bold/short its style looks — a real section heading
# is a bare label, never an already-answered field. Both label and value
# must stay short (config-driven) so a genuine inline list heading like
# "Skills: Python, Java, C++, Django, React" is never caught by this.
_KEY_VALUE_LINE_RE = re.compile(r"^(?P<label>[^:：]{1,60}?)\s*[:：]\s*(?P<value>\S.*)$")


def _looks_like_filled_personal_detail_line(text: str) -> bool:
    match = _KEY_VALUE_LINE_RE.match(text.strip())
    if not match:
        return False
    label_words = match.group("label").split()
    value_words = match.group("value").split()
    return (
        1 <= len(label_words) <= settings.personal_detail_line_max_label_words
        and 1 <= len(value_words) <= settings.personal_detail_line_max_value_words
    )


class Section(BaseModel):
    id: str
    section_type: SectionType
    raw_heading: str | None = None
    method: str
    heading_score: float | None = None
    page_start: int
    block_ids: list[str] = Field(default_factory=list)
    line_ids: list[str] = Field(default_factory=list)
    text: str = ""
    records: list[RecordSpan] = Field(default_factory=list)


def _normalize_heading_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip().rstrip(":：").strip()
    return text.casefold()


@functools.lru_cache(maxsize=1)
def _load_alias_index() -> tuple[dict[str, SectionType], list[str]]:
    """Build (alias -> section_type) and the flat alias list once, cached
    per worker process (section 53: never rebuild shared resources per
    request)."""
    path = RESOURCES_DIR / "sections" / "aliases.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    alias_to_type: dict[str, SectionType] = {}
    for section_type, per_language in raw.items():
        for _lang, aliases in per_language.items():
            for alias in aliases:
                alias_to_type[_normalize_heading_text(alias)] = section_type  # type: ignore[assignment]
    return alias_to_type, list(alias_to_type.keys())


def classify_heading_text(text: str) -> tuple[SectionType, str, float | None]:
    alias_to_type, alias_list = _load_alias_index()
    normalized = _normalize_heading_text(text)

    if normalized in alias_to_type:
        return alias_to_type[normalized], "ALIAS_EXACT", 100.0

    if len(normalized.split()) > settings.heading_classification_max_words:
        return "UNKNOWN", "UNKNOWN", None

    # Plain `fuzz.ratio` (whole-string Levenshtein), not `WRatio`: WRatio's
    # partial-ratio component happily scores a long sentence that merely
    # *contains* an alias as a near-perfect match, which is the opposite
    # of "strict cutoffs only" (section 18).
    match = process.extractOne(
        normalized, alias_list, scorer=fuzz.ratio, score_cutoff=settings.heading_fuzzy_cutoff
    )
    if match is not None:
        matched_alias, score, _ = match
        return alias_to_type[matched_alias], "FUZZY_HEADING", float(score)

    return "UNKNOWN", "UNKNOWN", None


def _new_section(section_id: str, section_type: SectionType, raw_heading: str | None, method: str,
                  score: float | None, page: int, block_id: str, line: Line) -> Section:
    return Section(
        id=section_id,
        section_type=section_type,
        raw_heading=raw_heading,
        method=method,
        heading_score=score,
        page_start=page,
        block_ids=[block_id],
        line_ids=[line.id],
        text=line.text,
    )


def classify_sections(document: Document) -> list[Section]:
    headings = detect_headings(document)
    heading_by_line_id: dict[str, HeadingCandidate] = {h.line_id: h for h in headings}
    baseline_font = compute_baseline_font_size(document)

    # Pre-classify every heading candidate once so repeated lookups in the
    # loop below don't re-run RapidFuzz for the same text.
    heading_classification = {h.line_id: classify_heading_text(h.text) for h in headings}

    sections: list[Section] = []
    current: Section | None = None
    seen_confident_heading = False
    # Style signatures of section headings confirmed *so far*. Built up
    # incrementally (not precomputed over the whole document) so that one
    # early confidently-classified heading can inform later ambiguous
    # ones, without a later heading — genuine or a stray fuzzy false
    # positive — retroactively reclassifying content that came before it.
    confirmed_signatures: set[tuple[int, bool, bool]] = set()

    for block in document.blocks:
        for line in block.lines:
            if not line.text.strip():
                continue

            heading = heading_by_line_id.get(line.id)
            section_type = method = None
            score: float | None = None
            if heading is not None:
                section_type, method, score = heading_classification[line.id]

            in_fold_eligible_section = current is not None and current.section_type in _FOLD_ELIGIBLE_TYPES
            is_record_subheading = (
                heading is not None
                and in_fold_eligible_section
                and _normalize_heading_text(heading.text) in _RECORD_SUBHEADING_DENYLIST
            )
            is_confident_boundary = method in ("ALIAS_EXACT", "FUZZY_HEADING") and not is_record_subheading
            # A heading-shaped line (big/bold/short) seen *before* the
            # first confidently classified section is folded into the
            # header/preamble region instead of becoming its own
            # micro-section. Otherwise the candidate's name — almost
            # always the single largest/boldest line on the page — would
            # itself be misread as an unknown section (section 21: the
            # name comes from the header region, never from
            # section-heading classification).
            #
            # Inside a record-bearing section (experience/projects/...), a
            # heading-shaped line is almost always a record's own title
            # (bold, short — indistinguishable from a section heading by
            # style alone) rather than the start of a new top-level
            # section, UNLESS it shares its exact style with the
            # already-confirmed section headings (a real, if unrecognized,
            # section almost always reuses that same heading style; a
            # record title's style usually differs from it).
            # `record_segmenter` is what turns a folded-in title into a
            # record boundary, one stage later.
            matches_confirmed_heading_style = heading is not None and style_signature(heading) in confirmed_signatures
            is_filled_personal_detail_line = heading is not None and _looks_like_filled_personal_detail_line(heading.text)
            is_unresolved_heading_after_start = (
                heading is not None
                and method == "UNKNOWN"
                and seen_confident_heading
                and not is_record_subheading
                and not is_filled_personal_detail_line
                and (not in_fold_eligible_section or matches_confirmed_heading_style)
            )

            if is_confident_boundary or is_unresolved_heading_after_start:
                if current is not None:
                    sections.append(current)
                current = _new_section(
                    f"section_{len(sections):03d}", section_type, heading.text, method, score,
                    block.page, block.id, line,
                )
                if is_confident_boundary:
                    seen_confident_heading = True
                    confirmed_signatures.add(style_signature(heading))
            elif current is None:
                current = _new_section("section_header", "HEADER", None, "HEADER", None, block.page, block.id, line)
            else:
                if block.id not in current.block_ids:
                    current.block_ids.append(block.id)
                current.line_ids.append(line.id)
                current.text = f"{current.text}\n{line.text}".strip()

    if current is not None:
        sections.append(current)

    for section in sections:
        if section.method == "UNKNOWN":
            guess = classify_by_signature(section.text)
            if guess is not None:
                section.section_type, _score = guess
                section.method = "STRUCTURAL_SIGNATURE"
        elif section.method == "HEADER":
            line_count = len(section.line_ids)
            if line_count > _HEADER_RECLASSIFY_LINE_THRESHOLD:
                guess = classify_by_signature(section.text)
                if guess is not None:
                    section.section_type, _score = guess
                    section.method = "STRUCTURAL_SIGNATURE"

    lines_by_id = {line.id: line for b in document.blocks for line in b.lines}
    for section in sections:
        if section.section_type not in _RECORD_BEARING_TYPES:
            continue
        section_lines = [lines_by_id[lid] for lid in section.line_ids]
        # The heading line itself never starts a "record" — it is the
        # section's own boundary, already accounted for by `Section`.
        if section.method != "HEADER" and section_lines:
            section_lines = section_lines[1:]
        section.records = segment_records(section_lines, baseline_font, id_prefix=section.id)

    return sections
