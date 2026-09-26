"""Column-count diagnostics (section 15).

`xy_cut.recursive_order` already performs the real per-band column split
used for reading order. This module exposes a cheap, page-level summary —
"roughly how many columns does this page have" — for logging, tests, and
later quality/adaptive-retry heuristics, without duplicating the ordering
logic itself.
"""
from __future__ import annotations

from cv_parser.config import settings
from cv_parser.document.models import Block
from cv_parser.layout.xy_cut import merge_intervals


def estimate_column_count(blocks: list[Block], page_width: float) -> int:
    """A coarse, whole-page estimate of side-by-side column count.

    Ignores vertical banding (so a full-width header above a two-column
    body will pull this estimate toward 1 if the header is large) — use
    `xy_cut.recursive_order`'s per-band `Region.column_count` for anything
    that needs band-aware precision.
    """
    if not blocks:
        return 0
    column_gap = settings.layout_column_gap_ratio * page_width
    x_intervals = merge_intervals([(b.bbox.x0, b.bbox.x1) for b in blocks], column_gap)
    return len(x_intervals)
