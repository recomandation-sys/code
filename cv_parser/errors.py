"""Typed, API-facing errors for file validation and ingestion failures.

Each error carries a stable machine-readable ``code`` plus a human message,
matching the error shape in README_CV_EXTRACTION_ARCHITECTURE.md section 7
so the FastAPI layer can translate them 1:1 into HTTP error bodies without
re-deciding wording per endpoint.
"""
from __future__ import annotations


class CVParserError(Exception):
    """Base class for all recoverable, user-facing parsing errors."""

    code: str = "PARSER_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


class EmptyFileError(CVParserError):
    code = "EMPTY_FILE"


class InvalidPdfError(CVParserError):
    code = "INVALID_PDF"


class FileTooLargeError(CVParserError):
    code = "FILE_TOO_LARGE"


class TooManyPagesError(CVParserError):
    code = "TOO_MANY_PAGES"


class PdfPasswordRequiredError(CVParserError):
    code = "PDF_PASSWORD_REQUIRED"


class MalformedPdfError(CVParserError):
    code = "MALFORMED_PDF"
