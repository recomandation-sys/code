"""File validation (section 7).

Runs entirely in memory — no temp file is ever written for validation or
native extraction, which sidesteps the "safe temporary-file lifecycle" /
"never trust uploaded filenames" concerns in section 54 rather than having
to manage one.
"""
from __future__ import annotations

import pymupdf as fitz

from cv_parser.config import settings
from cv_parser.errors import (
    EmptyFileError,
    FileTooLargeError,
    InvalidPdfError,
    MalformedPdfError,
    PdfPasswordRequiredError,
    TooManyPagesError,
)

_PDF_SIGNATURE = b"%PDF-"
_SIGNATURE_SEARCH_WINDOW = 2048


def open_and_validate_pdf(data: bytes) -> fitz.Document:
    """Validate raw upload bytes and return an opened, readable PyMuPDF document.

    Raises a `cv_parser.errors.CVParserError` subclass on any validation
    failure; callers (e.g. the FastAPI layer) can turn `.code`/`.message`
    directly into the HTTP error body.
    """
    if not data:
        raise EmptyFileError("The uploaded file is empty.")

    max_bytes = int(settings.max_pdf_size_mb * 1024 * 1024)
    if len(data) > max_bytes:
        raise FileTooLargeError(
            f"The uploaded file exceeds the maximum allowed size of {settings.max_pdf_size_mb:.0f} MB."
        )

    if _PDF_SIGNATURE not in data[:_SIGNATURE_SEARCH_WINDOW]:
        raise InvalidPdfError("The uploaded file is not a readable PDF.")

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # pragma: no cover - fitz raises many internal types
        raise MalformedPdfError(f"The uploaded file could not be parsed as a PDF: {exc}") from exc

    if doc.is_encrypted and not doc.authenticate(""):
        doc.close()
        raise PdfPasswordRequiredError("Please upload an unlocked PDF.")

    if doc.page_count == 0:
        doc.close()
        raise InvalidPdfError("The uploaded PDF has no pages.")

    if doc.page_count > settings.max_pdf_pages:
        page_count = doc.page_count
        doc.close()
        raise TooManyPagesError(
            f"The uploaded PDF has {page_count} pages, exceeding the maximum of {settings.max_pdf_pages}."
        )

    return doc
