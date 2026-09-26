"""Geometric deduplication (section 13).

Some PDF producers draw text twice at (near-)identical coordinates — e.g. a
fill pass then a stroke pass to fake a bold weight when no real bold font is
embedded, or a duplicated/watermarked text layer. That is a purely
geometric artifact of how the page was authored, not a property of any
particular language or CV template, so it is collapsed here — before any
structural or linguistic processing happens — using only position and text
equality. Identical text at genuinely different positions is never touched.
"""
from __future__ import annotations

from cv_parser.config import settings
from cv_parser.document.models import Word


def dedupe_words(words: list[Word]) -> list[Word]:
    tol = settings.dedup_position_tolerance_pt
    seen: set[tuple[str, int, int, int, int]] = set()
    out: list[Word] = []
    for w in words:
        key = (
            w.text,
            round(w.bbox.x0 / tol),
            round(w.bbox.y0 / tol),
            round(w.bbox.x1 / tol),
            round(w.bbox.y1 / tol),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    return out
