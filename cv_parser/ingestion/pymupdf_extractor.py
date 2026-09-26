"""Native PDF extraction (section 9) and the top-level ingestion entry point.

Uses PyMuPDF as the primary extractor. Word bounding boxes come from the
fast, reliable `page.get_text("words")` API; per-word font metadata (size,
flags, color) is recovered by overlapping each word's box against the
richer `page.get_text("dict")` span geometry, since the two APIs don't
expose a common word-level index.
"""
from __future__ import annotations

import pymupdf as fitz

from cv_parser.document.deduplication import dedupe_words
from cv_parser.document.geometry import normalize_bbox
from cv_parser.document.line_builder import build_blocks, build_lines
from cv_parser.document.models import BBox, Word
from cv_parser.ingestion.pdf_profiler import profile_page
from cv_parser.ingestion.validator import open_and_validate_pdf
from cv_parser.schemas.internal import Document

# `_collect_style_spans` only ever reads `type == 0` (text) blocks and
# immediately discards image blocks — but some decorative CV templates
# render a gradient/textured background as thousands of tiny tiled image
# XObjects (observed: 33k+ image blocks for a single real image behind
# the text), and PyMuPDF still pays to enumerate every one of them
# unless explicitly told not to preserve images in the result, which
# turns an ~8s-per-page call into ~0.1s with an otherwise identical
# text result (section 53: a decorative template must never make a
# normal digital CV pathologically slow).
_DICT_FLAGS_NO_IMAGES = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES


def _collect_style_spans(
    page: fitz.Page, textpage: fitz.TextPage
) -> tuple[list[tuple[tuple[float, float, float, float], float | None, int | None, int | None]], int]:
    """Returns (spans, character_count). `character_count` is derived from
    this same `"dict"` extraction pass rather than issuing a separate
    `page.get_text("text")` call — each `get_text` call rebuilds a fresh
    PyMuPDF text page from scratch, which becomes a real bottleneck (10s+)
    on graphics-heavy decorative CV templates with thousands of vector
    objects, so real CVs must not pay for it three times per page (the
    shared `textpage` avoids a second full rebuild for the sibling
    `"words"` call too).
    """
    spans = []
    character_count = 0
    raw = page.get_text("dict", textpage=textpage)
    for block in raw.get("blocks", []):
        if block.get("type") != 0:  # 0 = text block, 1 = image block
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                spans.append((tuple(span["bbox"]), span.get("size"), span.get("flags"), span.get("color")))
                character_count += len(span.get("text", ""))
    return spans, character_count


def _style_for_bbox(
    bbox: tuple[float, float, float, float],
    spans: list[tuple[tuple[float, float, float, float], float | None, int | None, int | None]],
) -> tuple[float | None, int | None, int | None]:
    x0, y0, x1, y1 = bbox
    best_overlap = 0.0
    best = (None, None, None)
    for sbbox, size, flags, color in spans:
        sx0, sy0, sx1, sy1 = sbbox
        ox = max(0.0, min(x1, sx1) - max(x0, sx0))
        oy = max(0.0, min(y1, sy1) - max(y0, sy0))
        overlap = ox * oy
        if overlap > best_overlap:
            best_overlap = overlap
            best = (size, flags, color)
    return best


def extract_words(page: fitz.Page, page_index: int) -> tuple[list[Word], int]:
    """Returns (words, character_count)."""
    # Built once (excluding images) and shared by both extraction calls
    # below, instead of each independently rebuilding its own text page.
    textpage = page.get_textpage(flags=_DICT_FLAGS_NO_IMAGES)
    words_raw = page.get_text("words", textpage=textpage)
    spans, character_count = _collect_style_spans(page, textpage)
    if not words_raw:
        return [], character_count

    words: list[Word] = []
    for x0, y0, x1, y1, text, _block_no, _line_no, _word_no in words_raw:
        size, flags, color = _style_for_bbox((x0, y0, x1, y1), spans)
        bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)
        words.append(
            Word(
                text=text,
                page=page_index,
                bbox=bbox,
                normalized_bbox=normalize_bbox(bbox, page.rect.width, page.rect.height),
                source="native_pdf",
                font_size=size,
                font_flags=flags,
                color=color,
            )
        )
    return dedupe_words(words), character_count


def load_document(data: bytes, source_name: str = "cv.pdf") -> Document:
    """Validate, extract, and assemble a fully-populated `Document`.

    Phase A scope: real words/lines/blocks with real geometry, from native
    PDF text only. OCR fallback for pages flagged `ocr_required` is wired
    in Phase H; until then such pages simply keep whatever thin native text
    they have and are surfaced via `page_state`/`ocr_required` so later
    phases (and `parse_quality`) know to be conservative about them.
    """
    doc = open_and_validate_pdf(data)
    try:
        document = Document(source_name=source_name, page_count=doc.page_count)
        for page_index in range(doc.page_count):
            page = doc[page_index]
            words, character_count = extract_words(page, page_index)
            page_profile = profile_page(page, page_index, words, character_count)

            document.pages.append(page_profile)
            document.words.extend(words)

            lines = build_lines(words, page.rect.width, page.rect.height, page_index)
            blocks = build_blocks(lines, page.rect.width, page.rect.height, page_index)
            document.lines.extend(lines)
            document.blocks.extend(blocks)

        return document
    finally:
        doc.close()
