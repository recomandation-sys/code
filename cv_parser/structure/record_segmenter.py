"""Record segmentation (section 20).

Splits a record-bearing section's lines into logical records (one
experience entry, one project, one certification...) *before* any field
extraction happens. A record starts at a line that plausibly "anchors" a
new entry — a date mention, or a short, visually prominent line (typography
reset) — never at an arbitrary fixed line count. Full date parsing with
precision (section 25) is Phase D's job; the regex here is only a light,
deliberately permissive "does this line contain a date-like token"
detector used to find boundaries.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from cv_parser.config import settings
from cv_parser.document.models import Line

_MONTHS = (
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
    r"|janv|f[ée]vr|mars|avr|mai|juin|juil|ao[ûu]t|sept|oct|nov|d[ée]c"
)
_DATE_ANCHOR_RE = re.compile(
    rf"\b(19|20)\d{{2}}\b|\b({_MONTHS})[a-zéû]*\.?\s*(19|20)?\d{{2,4}}\b",
    re.IGNORECASE,
)


class RecordSpan(BaseModel):
    id: str
    line_ids: list[str] = Field(default_factory=list)
    raw_text: str
    anchor_text: str


def _is_record_anchor(line: Line, baseline_font: float) -> bool:
    text = line.text.strip()
    if not text:
        return False
    if _DATE_ANCHOR_RE.search(text):
        return True

    word_count = len(text.split())
    if word_count > settings.record_anchor_max_words:
        return False
    relative_size = (line.median_font_size or baseline_font) / baseline_font if baseline_font else 1.0
    return line.bold_ratio >= settings.record_anchor_bold_ratio or relative_size >= settings.record_anchor_relative_font


def _collapse_consecutive(indices: list[int]) -> list[int]:
    """A title line immediately followed by its own date-range line (a
    common two-line record header) are both anchors on their own, but
    together they describe *one* record, not two — so only the first of
    any run of back-to-back anchor lines actually starts a new record.
    """
    if not indices:
        return []
    collapsed = [indices[0]]
    previous = indices[0]
    for idx in indices[1:]:
        if idx != previous + 1:
            collapsed.append(idx)
        previous = idx
    return collapsed


def segment_records(lines: list[Line], baseline_font: float, id_prefix: str = "record") -> list[RecordSpan]:
    non_empty = [l for l in lines if l.text.strip()]
    if not non_empty:
        return []

    anchor_indices = [i for i, l in enumerate(non_empty) if _is_record_anchor(l, baseline_font)]
    if not anchor_indices or anchor_indices[0] != 0:
        anchor_indices = [0] + anchor_indices
    anchor_indices = _collapse_consecutive(sorted(set(anchor_indices)))

    records: list[RecordSpan] = []
    for idx, start in enumerate(anchor_indices):
        end = anchor_indices[idx + 1] if idx + 1 < len(anchor_indices) else len(non_empty)
        span_lines = non_empty[start:end]
        if not span_lines:
            continue
        records.append(
            RecordSpan(
                id=f"{id_prefix}_{len(records):03d}",
                line_ids=[l.id for l in span_lines],
                raw_text="\n".join(l.text for l in span_lines),
                anchor_text=span_lines[0].text.strip(),
            )
        )
    return records
