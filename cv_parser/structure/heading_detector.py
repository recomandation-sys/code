"""Heading candidate detection (section 17).

Heading detection is structural first: relative font size, boldness,
line length, whitespace isolation, and case — never keyword matching
(that only happens afterwards, in `section_classifier`, on lines this
module already flagged as heading-shaped). Scores are heuristic
engineering scores, not probabilities (section 17).

Two passes:
1. Score every line on its own local style signals.
2. Any line that shares the exact style "signature" (font-size bucket +
   bold + case pattern) of a strongly-scored line gets a small boost —
   this catches a real repeated heading style whose individual occurrence
   would otherwise sit just under the strong-acceptance threshold
   ("repeated heading style" / "common alignment with other heading-like
   lines" signals).
"""
from __future__ import annotations

import statistics

from pydantic import BaseModel, Field

from cv_parser.config import settings
from cv_parser.document.models import Block, Line
from cv_parser.schemas.internal import Document


class HeadingCandidate(BaseModel):
    line_id: str
    block_id: str
    page: int
    text: str
    score: float
    relative_font_size: float
    is_bold: bool
    is_upper: bool
    reason_codes: list[str] = Field(default_factory=list)


def compute_baseline_font_size(document: Document) -> float:
    """The document's "body text" font size, used as the relative-size
    reference (section 4.2: never a fixed `font_size >= 14` rule)."""
    sizes = [w.font_size for w in document.words if w.font_size]
    if not sizes:
        return 10.0
    return statistics.median(sizes)


def style_signature(candidate: HeadingCandidate) -> tuple[int, bool, bool]:
    """A coarse (font-size bucket, bold, uppercase) style fingerprint.

    Used both for the in-module "repeated heading style" promotion pass
    and by `section_classifier` to tell a genuine (if unrecognized)
    section heading from a record-level title that merely happens to also
    be bold/short (they style identically to plain geometry but a real
    section heading almost always shares its style with other confirmed
    section headings, while a record title's style is usually distinct).
    """
    size_bucket = round(candidate.relative_font_size, 1)
    return (round(size_bucket * 10), candidate.is_bold, candidate.is_upper)


def _score_line(line: Line, baseline_font: float, gap_before: float | None, gap_after: float | None) -> HeadingCandidate:
    text = line.text.strip()
    relative_size = (line.median_font_size or baseline_font) / baseline_font if baseline_font else 1.0
    is_bold = line.bold_ratio >= settings.heading_bold_ratio_threshold
    letters = [c for c in text if c.isalpha()]
    is_upper = bool(letters) and all(c.isupper() for c in letters)
    word_count = len(text.split())

    score = 0.0
    reasons: list[str] = []

    if relative_size >= settings.heading_relative_font_large:
        score += 2.0
        reasons.append("LARGE_RELATIVE_FONT")
    elif relative_size >= settings.heading_relative_font_medium:
        score += 1.0
        reasons.append("MEDIUM_RELATIVE_FONT")

    if is_bold:
        score += 1.5
        reasons.append("BOLD")

    if 1 <= word_count <= 5:
        score += 1.0
        reasons.append("SHORT_LINE")

    if is_upper:
        score += 1.0
        reasons.append("UPPERCASE")

    # "whitespace before/after": a real vertical gap larger than a normal
    # line-to-line gap suggests this line is visually isolated as a title,
    # not just the next line of body prose.
    line_height = line.bbox.height or 10.0
    if gap_before is not None and gap_before > line_height * 0.6:
        score += 0.75
        reasons.append("WHITESPACE_BEFORE")
    if gap_after is not None and gap_after > line_height * 0.6:
        score += 0.25
        reasons.append("WHITESPACE_AFTER")

    if text.endswith(":"):
        score += 0.5
        reasons.append("SEPARATOR_PROXIMITY")

    return HeadingCandidate(
        line_id=line.id,
        block_id="",  # filled in by caller
        page=line.page,
        text=text,
        score=score,
        relative_font_size=round(relative_size, 3),
        is_bold=is_bold,
        is_upper=is_upper,
        reason_codes=reasons,
    )


def detect_headings(document: Document) -> list[HeadingCandidate]:
    """Every line is heading-eligible, not just a block's first line.

    Phase A/B's paragraph builder groups purely on vertical-gap-vs-font-size
    (`build_blocks`), which is deliberately conservative and, on real CVs
    with tight section spacing, often merges an entire section run
    (heading + body) into one block, or even several consecutive sections
    into one block. Restricting heading search to `block.lines[0]` would
    silently make every non-first section heading invisible. Scoring every
    line instead keeps heading detection correct independent of how
    coarse or fine the upstream block grouping happens to be.
    """
    baseline = compute_baseline_font_size(document)
    candidates: list[HeadingCandidate] = []

    for page in {b.page for b in document.blocks}:
        page_blocks: list[Block] = [b for b in document.blocks if b.page == page]
        for i, block in enumerate(page_blocks):
            for j, line in enumerate(block.lines):
                if not line.text.strip():
                    continue

                if j > 0:
                    gap_before = line.bbox.y0 - block.lines[j - 1].bbox.y1
                else:
                    gap_before = block.bbox.y0 - page_blocks[i - 1].bbox.y1 if i > 0 else None

                if j + 1 < len(block.lines):
                    gap_after = block.lines[j + 1].bbox.y0 - line.bbox.y1
                else:
                    gap_after = page_blocks[i + 1].bbox.y0 - block.bbox.y1 if i + 1 < len(page_blocks) else None

                candidate = _score_line(line, baseline, gap_before, gap_after)
                candidate.block_id = block.id
                candidates.append(candidate)

    strong = [c for c in candidates if c.score >= settings.heading_score_strong]
    strong_signatures = {style_signature(c) for c in strong}

    accepted: list[HeadingCandidate] = []
    for c in candidates:
        if c.score >= settings.heading_score_strong:
            accepted.append(c)
        elif c.score >= settings.heading_score_candidate_min and style_signature(c) in strong_signatures:
            c.score += 1.0
            c.reason_codes.append("REPEATED_HEADING_STYLE")
            accepted.append(c)

    return accepted
