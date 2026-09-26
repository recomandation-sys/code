"""job_nlp — hybrid rule-based job attribute extraction (no LLM at runtime)."""

__all__ = ["extract_job", "JobNLPService", "JobExtractionResult", "NormalizedJobProfileV1"]
__version__ = "1.0.0"

def __getattr__(name: str):
    if name in {"extract_job", "JobNLPService"}:
        from job_nlp.pipeline.job_extraction_pipeline import JobNLPService, extract_job
        return {"extract_job": extract_job, "JobNLPService": JobNLPService}[name]
    if name in {"JobExtractionResult", "NormalizedJobProfileV1"}:
        from job_nlp.pipeline.schemas import JobExtractionResult, NormalizedJobProfileV1
        return {"JobExtractionResult": JobExtractionResult, "NormalizedJobProfileV1": NormalizedJobProfileV1}[name]
    raise AttributeError(name)
