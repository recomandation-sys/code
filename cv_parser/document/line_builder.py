"""Line/block reconstruction from geometry (section 14).

Phase A note: this module intentionally implements only a single-pass,
single-column-friendly baseline (cluster words into lines by y-proximity,
then lines into blocks by vertical-gap size). It does not yet do
column-aware splitting or Recursive XY-Cut reading order — that is Phase
B's job (`cv_parser/layout/`). Keeping the function signatures stable here
means Phase B can replace the internals without touching callers.
"""
from __future__ import annotations

import statistics

from cv_parser.config import settings
from cv_parser.document.geometry import normalize_bbox, union_bbox
from cv_parser.document.models import BBox, Block, Line, Word


def build_lines(words: list[Word], page_width: float, page_height: float, page_index: int) -> list[Line]:
    """Cluster words that sit on (approximately) the same baseline into lines.

    Words are first sorted by vertical center so that clusters — and thus
    the returned line order — come out top-to-bottom by construction. Left
    -to-right order within a line comes from a secondary sort by x0.
    """
    if not words:
        return []

    ordered = sorted(words, key=lambda w: (w.bbox.y_center, w.bbox.x0))

    clusters: list[list[Word]] = []
    cluster_y: float = 0.0
    cluster_h: float = 0.0
    for w in ordered:
        h = w.bbox.height or 1.0
        if clusters and abs(w.bbox.y_center - cluster_y) <= max(h, cluster_h) * 0.5:
            clusters[-1].append(w)
            n = len(clusters[-1])
            cluster_y = cluster_y + (w.bbox.y_center - cluster_y) / n
            cluster_h = max(cluster_h, h)
        else:
            clusters.append([w])
            cluster_y = w.bbox.y_center
            cluster_h = h

    lines: list[Line] = []
    for i, cluster in enumerate(clusters):
        cluster_sorted = sorted(cluster, key=lambda w: w.bbox.x0)
        text = " ".join(w.text for w in cluster_sorted)
        bbox = union_bbox([w.bbox for w in cluster_sorted])
        sizes = [w.font_size for w in cluster_sorted if w.font_size]
        median_size = statistics.median(sizes) if sizes else None
        bold_ratio = sum(1 for w in cluster_sorted if w.is_bold) / len(cluster_sorted)
        lines.append(
            Line(
                id=f"p{page_index}_l{i}",
                page=page_index,
                text=text,
                words=cluster_sorted,
                bbox=bbox,
                normalized_bbox=normalize_bbox(bbox, page_width, page_height),
                median_font_size=median_size,
                bold_ratio=bold_ratio,
                source=cluster_sorted[0].source,
            )
        )
    return lines


def build_blocks(lines: list[Line], page_width: float, page_height: float, page_index: int) -> list[Block]:
    """Group consecutive lines into paragraph-like blocks by vertical gap.

    A gap larger than `block_gap_font_multiple` times the local font height
    starts a new block. This is a coarse baseline; Phase B additionally
    reasons about columns and repeated visual styles before finalizing
    block boundaries.
    """
    if not lines:
        return []

    groups: list[list[Line]] = [[lines[0]]]
    for prev, line in zip(lines, lines[1:]):
        gap = line.bbox.y0 - prev.bbox.y1
        font_h = prev.median_font_size or (prev.bbox.height or 10.0)
        if gap > font_h * settings.block_gap_font_multiple:
            groups.append([line])
        else:
            groups[-1].append(line)

    blocks: list[Block] = []
    for i, group in enumerate(groups):
        bbox = union_bbox([l.bbox for l in group])
        blocks.append(
            Block(
                id=f"p{page_index}_b{i}",
                page=page_index,
                lines=group,
                bbox=bbox,
                normalized_bbox=normalize_bbox(bbox, page_width, page_height),
                reading_order=i,
            )
        )
    return blocks
