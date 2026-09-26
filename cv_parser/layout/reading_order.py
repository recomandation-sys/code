"""Reading-order strategies (section 16) and the document-level entry point.

Strategy A (`order_simple`) is the naive top-to-bottom/left-to-right sort:
correct for single-column documents, and the designated fallback when
Strategy B's layout quality looks poor. Strategy B (`order_xy_cut`) is
column-aware and is used by default since it degrades to the same order as
Strategy A on genuinely single-column pages.
"""
from __future__ import annotations

from typing import Literal

from cv_parser.document.models import Block
from cv_parser.layout.regions import Region
from cv_parser.layout.xy_cut import recursive_order
from cv_parser.schemas.internal import Document

ReadingStrategy = Literal["SIMPLE", "XY_CUT"]


def order_simple(blocks: list[Block]) -> list[Block]:
    """Strategy A: pure positional order, no column awareness."""
    ordered = sorted(blocks, key=lambda b: (round(b.bbox.y0, 1), b.bbox.x0))
    return [b.model_copy(update={"reading_order": i, "column_id": None}) for i, b in enumerate(ordered)]


def order_xy_cut(blocks: list[Block], page_width: float, page_height: float, page_index: int) -> tuple[list[Block], list[Region]]:
    """Strategy B: column-aware Recursive XY-Cut order."""
    return recursive_order(blocks, page_width, page_height, page_index)


def assign_reading_order(document: Document, strategy: ReadingStrategy = "XY_CUT") -> tuple[Document, list[Region]]:
    """Return a new `Document` whose `blocks` are reordered/annotated per
    page using `strategy`, plus the `Region`s discovered (empty for
    `SIMPLE`, which does not reason about columns/regions at all).
    """
    new_blocks: list[Block] = []
    regions: list[Region] = []

    for page_profile in document.pages:
        page_blocks = [b for b in document.blocks if b.page == page_profile.page_index]
        if not page_blocks:
            continue
        if strategy == "SIMPLE":
            new_blocks.extend(order_simple(page_blocks))
        else:
            ordered, page_regions = order_xy_cut(
                page_blocks, page_profile.width, page_profile.height, page_profile.page_index
            )
            new_blocks.extend(ordered)
            regions.extend(page_regions)

    updated = document.model_copy(update={"blocks": new_blocks})
    return updated, regions
