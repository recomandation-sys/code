"""HTTP-facing response models for the CV extraction API.

`ExtractResponse` mirrors `cv_parser.schemas.parser_response.ParserDraftResponse`
field-for-field rather than re-declaring nested types, so the FastAPI layer
stays a thin transport wrapper around the pipeline's own Pydantic contract.
"""
from __future__ import annotations

from pydantic import BaseModel

from cv_parser.schemas.parser_response import ParserDraftResponse
from cv_parser.schemas.verified_profile import CandidateKnowledgeProfile


class ExtractResponse(ParserDraftResponse):
    pass


class CandidateProfileResponse(CandidateKnowledgeProfile):
    """Normalized candidate profile for job matching and recommendations."""
    pass


class ErrorResponse(BaseModel):
    """Shape matches section 7, e.g. {"code": "INVALID_PDF", "message": "..."}."""

    code: str
    message: str


class HealthResponse(BaseModel):
    status: str
    parser_version: str
