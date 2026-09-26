"""Common document model (README_CV_EXTRACTION_ARCHITECTURE.md section 12).

`BBox`, `Word`, `Line` and `Block` are the only vocabulary every later stage
(layout, structure, extractors, skills) is allowed to depend on. Whether the
text came from PyMuPDF's native layer or a Tesseract OCR fallback must be
invisible past `cv_parser/ingestion/`.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

TextSource = Literal["native_pdf", "ocr"]


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def x_center(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def y_center(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def area(self) -> float:
        return self.width * self.height


class Word(BaseModel):
    text: str
    page: int
    bbox: BBox
    normalized_bbox: BBox
    source: TextSource
    font_size: float | None = None
    font_flags: int | None = None
    color: int | None = None

    @property
    def is_bold(self) -> bool:
        # PyMuPDF span flag bit 2**4 marks a bold-weighted font
        # (see https://pymupdf.readthedocs.io -> TextPage flags).
        return bool(self.font_flags is not None and self.font_flags & (1 << 4))

    @property
    def is_italic(self) -> bool:
        return bool(self.font_flags is not None and self.font_flags & (1 << 1))


class Line(BaseModel):
    id: str
    page: int
    text: str
    words: list[Word]
    bbox: BBox
    normalized_bbox: BBox
    median_font_size: float | None = None
    bold_ratio: float = 0.0
    source: TextSource = "native_pdf"


class Block(BaseModel):
    id: str
    page: int
    lines: list[Line]
    bbox: BBox
    normalized_bbox: BBox
    column_id: str | None = None
    reading_order: int | None = None

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)
