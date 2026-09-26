"""Internal, non-API pipeline state (document profiling + the working
document object every later stage reads from and writes onto).

These models are deliberately separate from `schemas/parser_response.py`:
that module is the public contract returned to the frontend, while this one
is allowed to change shape freely as later phases (layout, structure,
extractors) add working state without breaking the API schema.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cv_parser.document.models import Block, Line, Word

PageState = Literal["DIGITAL_GOOD", "DIGITAL_SUSPECT", "SCAN"]
OverallPageState = Literal["DIGITAL_GOOD", "DIGITAL_SUSPECT", "SCAN", "MIXED"]
NativeTextQuality = Literal["GOOD", "SUSPECT", "POOR"]


class PageProfile(BaseModel):
    """Per-page profiling result (section 8)."""

    page_index: int
    width: float
    height: float
    rotation: int
    native_word_count: int
    native_character_count: int
    native_text_quality: NativeTextQuality
    image_coverage_ratio: float
    ocr_required: bool
    page_state: PageState


class Document(BaseModel):
    """Source-independent working document threaded through every stage."""

    source_name: str
    page_count: int
    pages: list[PageProfile] = Field(default_factory=list)
    words: list[Word] = Field(default_factory=list)
    lines: list[Line] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    used_ocr: bool = False

    @property
    def overall_page_state(self) -> OverallPageState:
        states = {p.page_state for p in self.pages}
        if not states:
            return "DIGITAL_GOOD"
        if len(states) > 1:
            return "MIXED"
        return next(iter(states))

    def words_on_page(self, page_index: int) -> list[Word]:
        return [w for w in self.words if w.page == page_index]
