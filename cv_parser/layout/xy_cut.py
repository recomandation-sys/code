"""Recursive XY-Cut reading-order resolution (section 15-16, Strategy B).

Classical document-image-analysis technique for ordering blocks the way a
human eye scans a page: project block extents onto the Y axis to find
horizontal bands separated by real whitespace, then within a band that
cannot be split further on Y, project onto X to detect side-by-side
columns and order them left to right. It operates purely on relative
geometry (whitespace-gap ratios of page width/height), so it makes no
assumption about language, section names, column count, or template.
"""
from __future__ import annotations

from cv_parser.config import settings
from cv_parser.document.geometry import union_bbox
from cv_parser.document.models import Block
from cv_parser.layout.regions import Region

Interval = tuple[float, float]


def merge_intervals(intervals: list[Interval], min_gap: float) -> list[list[float]]:
    """Merge 1D intervals that are closer than `min_gap` apart.

    A whitespace gap smaller than `min_gap` is treated as ordinary
    inter-word/inter-line spacing rather than a real column/region
    boundary; only a gap that clears the threshold produces a split.
    """
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda iv: iv[0])
    merged: list[list[float]] = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start - merged[-1][1] <= min_gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def recursive_order(
    blocks: list[Block], page_width: float, page_height: float, page_index: int
) -> tuple[list[Block], list[Region]]:
    """Order blocks into natural reading order, returning annotated copies
    (`column_id` + `reading_order` set) plus the `Region` bands discovered.
    """
    if not blocks:
        return [], []

    band_gap = settings.layout_band_gap_ratio * page_height
    column_gap = settings.layout_column_gap_ratio * page_width

    y_bands = merge_intervals([(b.bbox.y0, b.bbox.y1) for b in blocks], band_gap)

    ordered: list[Block] = []
    regions: list[Region] = []
    order_counter = 0

    for band_idx, (band_start, band_end) in enumerate(y_bands):
        band_blocks = [b for b in blocks if b.bbox.y0 < band_end and b.bbox.y1 > band_start]
        if not band_blocks:
            continue

        x_cols = merge_intervals([(b.bbox.x0, b.bbox.x1) for b in band_blocks], column_gap)
        region_id = f"p{page_index}_region{band_idx}"
        column_ids: list[str] = []

        for col_idx, (col_start, col_end) in enumerate(x_cols):
            col_id = f"{region_id}_col{col_idx}"
            column_ids.append(col_id)
            col_blocks = sorted(
                (b for b in band_blocks if b.bbox.x0 < col_end and b.bbox.x1 > col_start),
                key=lambda b: b.bbox.y0,
            )
            for b in col_blocks:
                ordered.append(b.model_copy(update={"column_id": col_id, "reading_order": order_counter}))
                order_counter += 1

        band_bbox = union_bbox([b.bbox for b in band_blocks])
        regions.append(
            Region(id=region_id, page=page_index, bbox=band_bbox, column_count=len(x_cols), column_ids=column_ids)
        )

    return ordered, regions
