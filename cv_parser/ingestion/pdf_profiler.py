"""Document/page profiling and the native-text quality gate (sections 8 & 10).

Decides, per page, whether the native PDF text layer is trustworthy enough
to use directly or whether the page should fall back to OCR (Phase H). The
decision uses only cheap, purely structural signals — never content
keywords or template coordinates.
"""
from __future__ import annotations

import pymupdf as fitz

from cv_parser.config import settings
from cv_parser.document.models import Word
from cv_parser.schemas.internal import NativeTextQuality, PageProfile, PageState

_REPLACEMENT_CHAR = "\ufffd"


def compute_image_coverage_ratio(page: fitz.Page) -> float:
    """Fraction of page area covered by raster images actually placed on it."""
    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return 0.0
    try:
        infos = page.get_image_info(xrefs=False)
    except Exception:
        return 0.0

    covered = 0.0
    for info in infos:
        bbox = info.get("bbox")
        if not bbox:
            continue
        x0, y0, x1, y1 = bbox
        x0, y0 = max(x0, 0.0), max(y0, 0.0)
        x1, y1 = min(x1, page.rect.width), min(y1, page.rect.height)
        covered += max(0.0, x1 - x0) * max(0.0, y1 - y0)
    return min(1.0, covered / page_area)


def _assess_text_quality(words: list[Word], character_count: int) -> NativeTextQuality:
    word_count = len(words)
    bad_chars = sum(text.count(_REPLACEMENT_CHAR) for text in (w.text for w in words))
    bad_char_ratio = bad_chars / character_count if character_count else 0.0
    single_char_words = sum(1 for w in words if len(w.text.strip()) <= 1)
    fragmentation_ratio = single_char_words / word_count if word_count else 1.0

    is_poor = (
        character_count < settings.native_text_min_chars_per_page
        or bad_char_ratio > settings.native_text_max_bad_char_ratio
        or fragmentation_ratio > settings.native_text_max_single_char_word_ratio
    )
    if is_poor:
        return "POOR"

    is_suspect = (
        character_count < settings.native_text_suspect_chars_per_page
        or fragmentation_ratio > settings.native_text_suspect_single_char_word_ratio
    )
    return "SUSPECT" if is_suspect else "GOOD"


def _decide_page_state(quality: NativeTextQuality, image_coverage_ratio: float) -> tuple[PageState, bool]:
    if quality == "POOR":
        return "SCAN", True
    if quality == "SUSPECT":
        ocr_required = image_coverage_ratio > settings.native_text_scan_image_coverage_ratio
        return "DIGITAL_SUSPECT", ocr_required
    return "DIGITAL_GOOD", False


def profile_page(page: fitz.Page, page_index: int, words: list[Word], character_count: int) -> PageProfile:
    quality = _assess_text_quality(words, character_count)
    # `image_coverage_ratio` only ever changes the OCR decision when text
    # quality is already borderline (`_decide_page_state`) — a "GOOD"
    # page never needs it. Scanning every image object on the page can be
    # expensive on graphics-heavy decorative CV templates, so real,
    # perfectly-fine digital CVs must not pay that cost (section 53:
    # digital PDFs stay on the lightweight path).
    image_coverage_ratio = compute_image_coverage_ratio(page) if quality != "GOOD" else 0.0
    page_state, ocr_required = _decide_page_state(quality, image_coverage_ratio)

    return PageProfile(
        page_index=page_index,
        width=page.rect.width,
        height=page.rect.height,
        rotation=page.rotation,
        native_word_count=len(words),
        native_character_count=character_count,
        native_text_quality=quality,
        image_coverage_ratio=round(image_coverage_ratio, 4),
        ocr_required=ocr_required,
        page_state=page_state,
    )
