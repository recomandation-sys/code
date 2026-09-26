from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.schemas import CandidateProfileResponse, ExtractResponse, HealthResponse
from cv_parser.config import settings
from cv_parser.errors import CVParserError
from cv_parser.pipeline import extract_candidate_profile, extract_profile

logger = logging.getLogger("cv_parser.api")
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", parser_version=settings.parser_version)


@router.post(
    "/api/cv/parse",
    response_model=ExtractResponse,
    responses={400: {"description": "Validation error"}, 422: {"description": "Unparsable PDF"}},
)
async def parse_cv(file: UploadFile = File(...)) -> ExtractResponse:
    # File validation itself (signature, size, page count, password, empty)
    # happens inside cv_parser.ingestion.validator so there is exactly one
    # place that owns those rules; this endpoint only translates the
    # resulting CVParserError into an HTTP body (section 7).
    content = await file.read()

    try:
        profile = extract_profile(content, source_name=file.filename or "uploaded.pdf")
    except CVParserError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc
    except Exception:
        logger.exception("CV extraction failed for %s", file.filename)
        raise HTTPException(
            status_code=422,
            detail={"code": "PARSE_FAILED", "message": "Could not parse this PDF."},
        )

    return ExtractResponse(**profile)


@router.post(
    "/api/cv/profile",
    response_model=CandidateProfileResponse,
    responses={400: {"description": "Validation error"}, 422: {"description": "Unparsable PDF"}},
)
async def parse_cv_profile(file: UploadFile = File(...)) -> CandidateProfileResponse:
    content = await file.read()

    try:
        profile = extract_candidate_profile(content, source_name=file.filename or "uploaded.pdf")
    except CVParserError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc
    except Exception:
        logger.exception("CV normalization failed for %s", file.filename)
        raise HTTPException(
            status_code=422,
            detail={"code": "NORMALIZE_FAILED", "message": "Could not normalize this CV."},
        )

    return CandidateProfileResponse(**profile)
