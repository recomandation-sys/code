__all__ = [
    "JobNLPService",
    "extract_job",
    "get_service",
    "JobExtractionResult",
    "NormalizedJobProfileV1",
    "NormalizedJobOffer",
    "Evidence",
]

def __getattr__(name: str):
    if name in {"JobNLPService", "extract_job", "get_service"}:
        from job_nlp.pipeline.job_extraction_pipeline import JobNLPService, extract_job, get_service
        return {"JobNLPService": JobNLPService, "extract_job": extract_job, "get_service": get_service}[name]
    if name in {"Evidence", "JobExtractionResult", "NormalizedJobProfileV1"}:
        from job_nlp.pipeline.schemas import Evidence, JobExtractionResult, NormalizedJobProfileV1
        return {"Evidence": Evidence, "JobExtractionResult": JobExtractionResult, "NormalizedJobProfileV1": NormalizedJobProfileV1}[name]
    if name == "NormalizedJobOffer":
        from job_nlp.schemas.normalized_job_offer import NormalizedJobOffer
        return NormalizedJobOffer
    raise AttributeError(name)
