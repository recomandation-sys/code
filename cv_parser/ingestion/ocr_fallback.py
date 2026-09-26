"""OCR fallback (section 11) — implemented in Phase H.

Deliberately not wired into `pymupdf_extractor.load_document` yet: per the
phased plan, the digital-native path must be validated first so OCR
complexity never delays or masks regressions in the (much more common)
digital-PDF path. Pages that fail the native-text quality gate are still
surfaced today via `PageProfile.ocr_required` / `page_state`, so nothing
downstream needs to change once this module goes live.
"""
from __future__ import annotations


def run_ocr_on_page(*args, **kwargs):  # pragma: no cover - Phase H
    raise NotImplementedError(
        "OCR fallback is not implemented yet (Phase H). "
        "This page was flagged `ocr_required=True` by the native-text quality gate."
    )
