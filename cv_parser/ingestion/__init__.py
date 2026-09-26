"""PDF ingestion: validation, page profiling, and native text extraction.

Public entry point: `load_document`.
"""
from __future__ import annotations

from cv_parser.ingestion.pymupdf_extractor import load_document

__all__ = ["load_document"]
