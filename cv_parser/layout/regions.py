"""Region model (section 15).

A `Region` is one horizontal band of the page (e.g. a full-width header, or
the multi-column body beneath it) together with however many side-by-side
columns were detected inside that band. Regions are an internal-only
bookkeeping structure produced by `xy_cut.recursive_order`; Phase C can
later use `region_id`/column membership as a structural signal (section
19: "region hierarchy indicates a new section").
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from cv_parser.document.models import BBox


class Region(BaseModel):
    id: str
    page: int
    bbox: BBox
    column_count: int
    column_ids: list[str] = Field(default_factory=list)
