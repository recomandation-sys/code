"""FastAPI entry point.

    uvicorn app.main:app --reload --port 8000

POST a CV as multipart/form-data to /api/cv/parse and get back the parser
draft JSON produced by cv_parser.pipeline.extract_profile.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from cv_parser.config import settings
from recommendation.api import router as recommendation_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="CV Extraction + Skill Recommendation Service",
    description="Deterministic CV parsing plus skill-level job recommendation "
    "(professional cosine + technology exact IDs). No LLM ranking.",
    version=settings.parser_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(recommendation_router, prefix="/api")
