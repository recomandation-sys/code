"""Candidate Knowledge Profile — normalized output for job matching (section 50).

Produced by transforming a parser draft into a compact, recommendation-ready
representation. This is what the job recommendation system consumes; it drops
review bookkeeping (parse_quality, review_items, meta) while preserving
structured skills, evidence, and match-relevant preferences.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cv_parser.schemas.parser_response import ContractType, WorkMode

MobilityPreference = Literal["LOCAL", "FOREIGN", "REMOTE"]
SeniorityLevel = Literal["INTERN", "JUNIOR", "MID", "SENIOR", "LEAD", "MANAGER"]
SkillProficiencyLevel = Literal["BASIC", "INTERMEDIATE", "ADVANCED"]
NormalizedLanguageLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2", "NATIVE", "FLUENT"]
JobFamily = Literal[
    "FRONTEND_DEVELOPER",
    "BACKEND_DEVELOPER",
    "FULLSTACK_DEVELOPER",
    "MOBILE_DEVELOPER",
    "DEVOPS_ENGINEER",
    "DATA_SCIENTIST",
    "DATA_ENGINEER",
    "SOFTWARE_ENGINEER",
    "QA_ENGINEER",
    "SECURITY_ENGINEER",
    "CLOUD_ENGINEER",
    "PRODUCT_MANAGER",
    "OTHER",
]


class ProfileIdentity(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""


class LocationPreferences(BaseModel):
    current_country: str = ""
    mobility_preferences: list[MobilityPreference] = Field(default_factory=list)
    preferred_countries: list[str] = Field(default_factory=list)


class ProfileTarget(BaseModel):
    desired_positions: list[str] = Field(default_factory=list)
    desired_job_families: list[JobFamily] = Field(default_factory=list)
    desired_contract_types: list[ContractType] = Field(default_factory=list)
    desired_work_modes: list[WorkMode] = Field(default_factory=list)
    desired_seniority: list[SeniorityLevel] = Field(default_factory=list)


class ProfileExperience(BaseModel):
    professional_months: int = 0
    internship_months: int = 0
    alternance_months: int = 0
    freelance_months: int = 0
    total_months: int = 0


class ProfileSkill(BaseModel):
    name: str
    category: str
    level: SkillProficiencyLevel = "BASIC"
    confidence: float = Field(ge=0.0, le=1.0)


class ProfileSkillEvidence(BaseModel):
    skill: str
    source_type: str
    source_label: str = ""
    source_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str = ""


class ProfileLanguage(BaseModel):
    language: str
    level: NormalizedLanguageLevel | None = None


class ProfileCertification(BaseModel):
    name: str
    issuer: str = ""
    year: str = ""


class CandidateKnowledgeProfile(BaseModel):
    identity: ProfileIdentity = Field(default_factory=ProfileIdentity)
    location_preferences: LocationPreferences = Field(default_factory=LocationPreferences)
    target: ProfileTarget = Field(default_factory=ProfileTarget)
    experience: ProfileExperience = Field(default_factory=ProfileExperience)
    skills: list[ProfileSkill] = Field(default_factory=list)
    skill_evidence: list[ProfileSkillEvidence] = Field(default_factory=list)
    languages: list[ProfileLanguage] = Field(default_factory=list)
    certifications: list[ProfileCertification] = Field(default_factory=list)


# Backward-compatible alias used in earlier architecture docs.
VerifiedCandidateProfile = CandidateKnowledgeProfile
