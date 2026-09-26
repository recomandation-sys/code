"""Optional FastAPI wrapper for English-only job extraction (EN_V1).

Every request goes through the preprocessing gate before a feature extractor.
A refusal returns the existing offer or skills payload and does not call
``JobNLPService``. ``language_verified`` is not a request field. Callers that
use ``JobNLPService.extract()`` directly still run the stopword check.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, field_validator

from job_nlp.ingestion.preprocess.adapters import from_api_fields
from job_nlp.ingestion.preprocess.integrate import preprocess_and_extract, refusal_offer
from job_nlp.ingestion.preprocess.language import open_predictor
from job_nlp.pipeline.job_extraction_pipeline import JobNLPService
from job_nlp.pipeline.schemas import Location, NormalizedJobProfileV1
from job_nlp.pipeline.validator import validate
from job_nlp.schemas.normalized_job_offer import SCHEMA_VERSION

app = FastAPI(title="Job NLP Extraction EN_V1", version="EN_V1")
_service: JobNLPService | None = None
# Loaded once per process. A missing model refuses every offer.
_predictor = open_predictor()


def get_extractor() -> JobNLPService:
    global _service
    if _service is None:
        _service = JobNLPService(
            load_en_skills=True,
            leaf_mode=os.getenv("JOB_NLP_LEAF_MODE", "production").strip().lower(),
        )
    return _service


class JobExtractRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # Bounds protect the model process from accidental or hostile oversized
    # payloads while leaving ample room for real job postings and source IDs.
    title: str = Field(min_length=1, max_length=512)
    description: str = Field(default="", max_length=50_000)
    country: str = Field(default="", max_length=256)
    job_id: str = Field(default="", max_length=256)
    source: str = Field(default="", max_length=256)
    source_id: str | None = Field(default=None, max_length=256)
    legacy_v1: bool = False
    skills_only: bool = False

    @field_validator("title")
    @classmethod
    def _title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must contain a non-whitespace character")
        return value


def _mode(req: JobExtractRequest) -> str:
    if req.skills_only:
        return "skills_only"
    if req.legacy_v1:
        return "legacy_v1"
    return "extract"


def _refused(req: JobExtractRequest, gate) -> dict:
    if req.skills_only:
        return {"professional_skills": [], "technologies": []}
    if req.legacy_v1:
        return validate(
            NormalizedJobProfileV1(
                pipeline_version="EN_V1",
                location=Location(country=req.country or None),
            )
        ).model_dump(mode="json")
    return refusal_offer(
        gate,
        title=req.title,
        country=req.country,
        job_id=req.job_id,
        source=req.source,
        source_id=req.source_id,
    ).model_dump(mode="json")


@app.post("/api/v1/jobs/extract")
def extract(req: JobExtractRequest) -> dict:
    result = preprocess_and_extract(
        from_api_fields(
            title=req.title,
            description=req.description,
            country=req.country,
            job_id=req.job_id,
            source=req.source,
            source_id=req.source_id,
        ),
        get_extractor(),
        _predictor,
        mode=_mode(req),
    )
    if result.extraction is None:
        return _refused(req, result.gate)
    payload = result.extraction
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload


@app.get("/health")
def health() -> dict:
    service = get_extractor()
    stack = service.en_skills
    if stack is None:
        nesta_ready = True
        technology_ready = True
    else:
        nesta_ready = bool(
            getattr(stack, "loaded", False)
            and getattr(stack, "_nesta", None) is not None
            and getattr(stack, "_nesta", None) is not False
        )
        technology_ready = not any(
            str(warning).startswith("tech_v2_load_failed:")
            for warning in (getattr(stack, "warnings", None) or [])
        )

    semantic = service.semantic_resolver
    semantic_ready = semantic is None or bool(
        getattr(semantic, "_model", None) is not None
        and getattr(semantic, "_vectors", None) is not None
        and getattr(semantic, "_vectors", None) is not False
    )
    title_index = service.title_vector_resolver
    title_index_ready = title_index is None or bool(
        getattr(title_index, "model", None) is not None
        and getattr(title_index, "_vectors", None) is not None
        and getattr(title_index, "_vectors", None) is not False
    )
    components = {
        "knowledge_base": service.knowledge_base is not None,
        "nesta": nesta_ready,
        "technology_taxonomy": technology_ready,
        "semantic_family": semantic_ready,
        "reviewed_title_index": title_index_ready,
        "language_model": not str(getattr(_predictor, "version", "unavailable")).startswith("unavailable"),
    }
    return {
        "status": "ok" if all(components.values()) else "degraded",
        "pipeline_version": service.pipeline_version,
        "schema_version": SCHEMA_VERSION,
        "language": "en",
        "components": components,
    }
