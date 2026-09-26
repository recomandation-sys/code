"""Pure geometry helpers used by ingestion, layout and structure discovery.

Every function here operates on relative/normalized quantities or plain
bounding boxes — never on a hard-coded page coordinate — per the "use
relative features, never template coordinates" principle (section 4.2).
"""
from __future__ import annotations

from cv_parser.document.models import BBox


def normalize_bbox(bbox: BBox, page_width: float, page_height: float) -> BBox:
    """Scale a pixel/point bbox into [0, 1] page-relative coordinates."""
    if page_width <= 0 or page_height <= 0:
        return BBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0)
    return BBox(
        x0=bbox.x0 / page_width,
        y0=bbox.y0 / page_height,
        x1=bbox.x1 / page_width,
        y1=bbox.y1 / page_height,
    )


def union_bbox(boxes: list[BBox]) -> BBox:
    if not boxes:
        return BBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0)
    return BBox(
        x0=min(b.x0 for b in boxes),
        y0=min(b.y0 for b in boxes),
        x1=max(b.x1 for b in boxes),
        y1=max(b.y1 for b in boxes),
    )


def vertical_overlap(a: BBox, b: BBox) -> float:
    """Length of the overlapping y-range between two boxes (0 if none)."""
    return max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))


def horizontal_overlap(a: BBox, b: BBox) -> float:
    return max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))


def horizontal_gap(a: BBox, b: BBox) -> float:
    """Positive whitespace gap between two boxes on the x axis, left-to-right."""
    if a.x1 <= b.x0:
        return b.x0 - a.x1
    if b.x1 <= a.x0:
        return a.x0 - b.x1
    return 0.0


def vertical_gap(a: BBox, b: BBox) -> float:
    if a.y1 <= b.y0:
        return b.y0 - a.y1
    if b.y1 <= a.y0:
        return a.y0 - b.y1
    return 0.0


def intersection_area(a: BBox, b: BBox) -> float:
    return max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0)) * max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))


def overlap_area_ratio(a: BBox, b: BBox) -> float:
    """Intersection area as a fraction of the smaller box's area."""
    smaller = min(a.area, b.area)
    if smaller <= 0:
        return 0.0
    return intersection_area(a, b) / smaller
