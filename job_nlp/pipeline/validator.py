"""Validate NormalizedJobProfileV1 against controlled vocabularies."""
from __future__ import annotations

from job_nlp.config.loader import load_labels, parent_classes
from job_nlp.contracts.ontology import ContractType, EducationLevel, MinimumExperienceBracket, SeniorityLevel, WorkMode
from job_nlp.pipeline.schemas import CertificationRequirements, NormalizedJobProfileV1


def validate(result: NormalizedJobProfileV1) -> NormalizedJobProfileV1:
    labels = load_labels()
    parents = set(parent_classes()) | set(labels.get("special_job_family_statuses", []))

    if result.job_family_parent not in parents:
        result.job_family_parent = "UNKNOWN"
    if str(getattr(result.seniority, "value", result.seniority)) not in set(labels["seniority"]):
        result.seniority = SeniorityLevel.UNKNOWN
    if str(getattr(result.contract_type, "value", result.contract_type)) not in set(labels["contract_type"]):
        result.contract_type = ContractType.UNKNOWN
    if str(getattr(result.work_mode, "value", result.work_mode)) not in set(labels["work_mode"]):
        result.work_mode = WorkMode.UNKNOWN
    if str(getattr(result.education_level, "value", result.education_level)) not in set(labels["education_level"]):
        result.education_level = EducationLevel.UNKNOWN
    if result.education_requirement not in set(labels["requirement_status"]):
        result.education_requirement = "UNKNOWN"

    brackets = {
        "0_YEARS",
        "1_2_YEARS",
        "3_5_YEARS",
        "5_7_YEARS",
        "8_PLUS_YEARS",
        "UNKNOWN",
    }
    if str(getattr(result.minimum_experience_bracket, "value", result.minimum_experience_bracket)) not in brackets:
        result.minimum_experience_bracket = MinimumExperienceBracket.UNKNOWN

    result.required_skills = _dedupe(result.required_skills)
    pref = _dedupe(result.preferred_skills)
    result.preferred_skills = [s for s in pref if s not in set(result.required_skills)]
    result.certifications = _dedupe(result.certifications)
    result.languages = _dedupe(result.languages)

    cr = result.certification_requirements
    result.certification_requirements = CertificationRequirements(
        required=_dedupe(cr.required),
        preferred=_dedupe(cr.preferred),
        unspecified=_dedupe(cr.unspecified),
    )
    return result


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        out.append(key)
    return out
