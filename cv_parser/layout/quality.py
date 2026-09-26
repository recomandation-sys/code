"""Layout quality diagnostics (section 16/48).

Cheap, purely structural signals about whether a chosen reading-order
strategy produced something coherent. Phase G's adaptive retry loop
consumes this to decide whether to fall back from `XY_CUT` to `SIMPLE` (or
vice versa) for a given page; this module only measures, it does not
retry.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from cv_parser.config import settings
from cv_parser.document.models import Block

LayoutQualityStatus = Literal["GOOD", "POOR"]


class LayoutQualityReport(BaseModel):
    block_count: int
    column_switch_ratio: float
    distinct_columns: int
    status: LayoutQualityStatus


def compute_layout_quality(ordered_blocks: list[Block]) -> LayoutQualityReport:
    """`ordered_blocks` must already be in the reading order to evaluate.

    `column_switch_ratio` measures how often the column changes between
    consecutive blocks in reading order. A well-formed multi-column layout
    finishes one column's blocks before starting the next, so switches
    should stay close to (regions x (columns - 1)), not scale with block
    count; a high ratio indicates blocks from different columns got
    interleaved (section 48's "interleaved columns" symptom).

    Note: `column_id is None` (Strategy A never assigns one) is *not*
    treated as evidence of poor quality here — that would make Strategy A
    look artificially "worse" by this metric's own construction. The
    document-level `orphan_ratio` in `parse_quality` (section 47) is a
    different, text/section-coverage-based signal computed once structure
    discovery (Phase C) exists.
    """
    total = len(ordered_blocks)
    if total == 0:
        return LayoutQualityReport(block_count=0, column_switch_ratio=0.0, distinct_columns=0, status="GOOD")

    switches = sum(
        1
        for a, b in zip(ordered_blocks, ordered_blocks[1:])
        if a.page == b.page and a.column_id is not None and b.column_id is not None and a.column_id != b.column_id
    )
    distinct_columns = len({b.column_id for b in ordered_blocks if b.column_id is not None})
    column_switch_ratio = switches / total

    is_poor = distinct_columns > 1 and column_switch_ratio > settings.layout_retry_column_switch_threshold

    return LayoutQualityReport(
        block_count=total,
        column_switch_ratio=round(column_switch_ratio, 4),
        distinct_columns=distinct_columns,
        status="POOR" if is_poor else "GOOD",
    )
