"""NormalizedJobOffer — JOB_EXTRACTION_PIPELINE_EN_V1 public contract."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from shared_matching.enums import Language, RequirementModality, WorkSchedule
from job_nlp.contracts.ontology import (
    ContractType,
    EducationLevel,
    MinimumExperienceBracket,
    SeniorityLevel,
    WorkMode,
)

SCHEMA_VERSION = "JOB_EXTRACTION_PIPELINE_EN_V1"

JobContractType = ContractType
SkillCategory = Literal["SKILL", "KNOWLEDGE", "TECHNOLOGY"]


class JobIdentity(BaseModel):
    job_id: str = ""
    title: str = ""
    normalized_title: str = ""
    job_family: str = "UNKNOWN"
    job_parent: str = "UNKNOWN"
    job_leaf: str | None = "UNKNOWN"
    esco_occupation_uri: str | None = None
    esco_occupation_label: str | None = None
    source: str = ""
    source_id: str | None = None


class JobLocation(BaseModel):
    country: str = ""  # ISO alpha-2 when known
    # Retained for internal location matching, but intentionally omitted from
    # the public EN_V1 payload (the product contract exposes country only).
    city: str | None = Field(default=None, exclude=True)
    work_modes: list[WorkMode] = Field(default_factory=list)


class JobRequirements(BaseModel):
    contract_type: JobContractType = ContractType.UNKNOWN
    work_schedule: WorkSchedule = "UNKNOWN"
    seniority: SeniorityLevel = SeniorityLevel.UNKNOWN  # not produced by structured V1
    minimum_experience_bracket: MinimumExperienceBracket = MinimumExperienceBracket.UNKNOWN
    education_level: EducationLevel | None = None
    # Requirement modality is an internal rule signal; only the normalized
    # education level is part of the public output.
    education_requirement: RequirementModality = Field(default="UNSPECIFIED", exclude=True)


class JobSkillEntity(BaseModel):
    name: str
    canonical_id: str = ""
    normalized_skill: str = ""
    skill_kind: str = ""
    category: SkillCategory = "SKILL"
    esco_uri: str | None = None
    # Requirement modality is retained for recommendation matching but is not
    # exposed in the two-bucket skills API/output.
    requirement: RequirementModality = Field(default="UNSPECIFIED", exclude=True)
    # Heuristic extraction confidence (not a calibrated probability)
    extraction_confidence: float = 0.0
    requirement_confidence: float = Field(default=0.0, exclude=True)
    sources: list[str] = Field(default_factory=list)
    surface: str = ""
    evidence: str = ""


class JobLanguage(BaseModel):
    language: Language | str = "UNKNOWN"


class JobCertification(BaseModel):
    name: str
    issuer: str | None = None
    required: bool = False
    evidence: str = ""


class OccupationPath(BaseModel):
    """One taxonomy-valid Family → Parent → Leaf prediction.

    ``occupation_paths`` is deliberately a list of complete paths rather than
    three independent arrays.  This prevents invalid cartesian combinations
    when a posting genuinely spans more than one nearby occupation.
    """

    job_family: str
    job_parent: str
    job_leaf: str
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class JobQuality(BaseModel):
    language: str = "en"
    warnings: list[str] = Field(default_factory=list)
    abstentions: list[str] = Field(default_factory=list)
    extractor_version: str = SCHEMA_VERSION
    status: str = "ok"  # ok | unsupported_language | error
    family_resolver_method: str = "abstain"
    family_semantic_score: float | None = None
    family_semantic_margin: float | None = None
    # Auditable evidence/method metadata for every extracted field.
    field_evidence: dict[str, list[dict[str, str]]] = Field(default_factory=dict)
    field_methods: dict[str, str] = Field(default_factory=dict)
    # Resolver decisions are diagnostic metadata, not model confidence.  Keep
    # them in the public record so production errors can be reviewed without
    # reconstructing an inference run from log files.
    decision_metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedJobOffer(BaseModel):
    schema_version: str = SCHEMA_VERSION
    identity: JobIdentity = Field(default_factory=JobIdentity)
    location: JobLocation = Field(default_factory=JobLocation)
    requirements: JobRequirements = Field(default_factory=JobRequirements)
    skills: list[JobSkillEntity] = Field(default_factory=list)
    languages: list[JobLanguage] = Field(default_factory=list)
    occupation_paths: list[OccupationPath] = Field(default_factory=list)
    # Certifications are extracted internally for compatibility, but are not
    # a product field in the current job-extraction response.
    certifications: list[JobCertification] = Field(default_factory=list, exclude=True)
    quality: JobQuality = Field(default_factory=JobQuality)

    @property
    def technology_skills(self) -> list[JobSkillEntity]:
        return [s for s in self.skills if s.category == "TECHNOLOGY"]

    @property
    def professional_skills(self) -> list[JobSkillEntity]:
        return [s for s in self.skills if s.category == "SKILL"]

    def skills_only(self) -> dict[str, list[dict]]:
        """Return the public NESTA/Technology V2 skill view.

        Requirement modality is still retained internally for compatibility with
        older matching code, but it is deliberately not part of this projection.
        The skills extraction contract has only two buckets: professional skills
        and technologies.
        """
        def clean(skill: JobSkillEntity) -> dict:
            row = skill.model_dump(mode="json")
            row.pop("requirement", None)
            row.pop("requirement_confidence", None)
            return row

        return {
            "professional_skills": [clean(s) for s in self.professional_skills],
            "technologies": [clean(s) for s in self.technology_skills],
        }
