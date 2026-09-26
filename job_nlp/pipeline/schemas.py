"""Pydantic output contract — NormalizedJobProfileV1."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from job_nlp.contracts.ontology import (
    ContractType,
    EducationLevel,
    MinimumExperienceBracket,
    SeniorityLevel,
    WorkMode,
)


class Evidence(BaseModel):
    field: str
    value: Any
    source: str  # RULE | NEURAL | NORMALIZER | TITLE_RULE | TITLE_REGEX
    confidence: float | None = None
    evidence_text: str | None = None
    start: int | None = None
    end: int | None = None


class RuleHit(BaseModel):
    value: Any
    confidence: float = 1.0
    evidence_text: str | None = None
    source: str = "RULE"
    # Optional provenance fields keep legacy callers compatible while allowing
    # the aligned public adapter to round-trip evidence against raw text.
    evidence_start: int | None = None
    evidence_end: int | None = None
    evidence_source: str = "UNKNOWN"
    warnings: list[str] = Field(default_factory=list)


class CertificationRequirements(BaseModel):
    required: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)
    unspecified: list[str] = Field(default_factory=list)


class Location(BaseModel):
    country: str | None = None


class TaxonomyCandidate(BaseModel):
    leaf: str
    parent: str
    priority: int
    matched_text: str
    pattern_id: str
    source: str = "TITLE_REGEX"
    kb_leaf_id: str | None = None
    kb_parent_id: str | None = None
    kb_family_id: str | None = None
    unresolved: bool = False


class NormalizedJobProfileV1(BaseModel):
    job_family_parent: str = "UNKNOWN"
    job_family_leaf: str = "UNKNOWN"
    seniority: SeniorityLevel = SeniorityLevel.UNKNOWN
    contract_type: ContractType = ContractType.UNKNOWN
    work_mode: WorkMode = WorkMode.UNKNOWN
    minimum_experience_bracket: MinimumExperienceBracket = MinimumExperienceBracket.UNKNOWN
    education_level: EducationLevel = EducationLevel.UNKNOWN
    education_requirement: str = "UNKNOWN"
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    certification_requirements: CertificationRequirements = Field(default_factory=CertificationRequirements)
    languages: list[str] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    evidence: list[Evidence] = Field(default_factory=list)
    pipeline_version: str = "1.0.0"


# ponytail: alias keeps old import sites working until fully migrated
JobExtractionResult = NormalizedJobProfileV1
