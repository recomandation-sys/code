"""Parser draft JSON — the public API contract returned to the review form
(README_CV_EXTRACTION_ARCHITECTURE.md section 49).

Confidence is always a discrete `HIGH`/`MEDIUM`/`LOW` label with supporting
`reason_codes`, never a fabricated float (section 45). Every "unknown"
field is represented explicitly (`None` / empty list) rather than omitted or
guessed (section 4.4) — most of these are populated starting in Phase D-G;
Phase A only guarantees the schema and the `meta` ingestion diagnostics are
real.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["HIGH", "MEDIUM", "LOW"]
ContractType = Literal["CDI", "CDD", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "OTHER"]
WorkMode = Literal["REMOTE", "HYBRID", "ONSITE"]
DatePrecision = Literal["YEAR", "MONTH", "DAY"]
ExperienceType = Literal["PROFESSIONAL", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "UNKNOWN"]
DesiredPositionSourceType = Literal["EXPLICIT_TARGET", "CV_HEADLINE", "PROFILE_STATEMENT"]
SkillEvidenceSourceType = Literal[
    "SKILLS_SECTION",
    "PROFESSIONAL_EXPERIENCE",
    "INTERNSHIP",
    "ALTERNANCE",
    "PROJECT",
    "CERTIFICATION",
    "PROFILE",
    "EDUCATION",
    "OTHER",
]
SkillCategory = Literal[
    "PROGRAMMING_LANGUAGE",
    "FRAMEWORK",
    "LIBRARY",
    "DATABASE",
    "CLOUD",
    "DEVOPS",
    "CI_CD",
    "CONTAINER",
    "CONTAINER_ORCHESTRATION",
    "VERSION_CONTROL",
    "OPERATING_SYSTEM",
    "TESTING",
    "DATA_ENGINEERING",
    "MACHINE_LEARNING",
    "CYBERSECURITY",
    "NETWORKING",
    "MONITORING",
    "API_TECHNOLOGY",
    "WEB_TECHNOLOGY",
    "MOBILE",
    "DEVELOPMENT_TOOL",
    "METHODOLOGY",
    "OTHER_IT",
    "TECHNOLOGY",
    "PROFESSIONAL_SKILL",
]
CEFRLevel = Literal[
    "A1", "A2", "B1", "B2", "C1", "C2",
    "NATIVE", "FLUENT", "ADVANCED", "INTERMEDIATE", "BASIC", "UNKNOWN",
]
ParseQualityStatus = Literal["GOOD", "FAIR", "POOR"]


class ConfidentValue(BaseModel):
    value: str | None = None
    confidence: Confidence = "LOW"
    method: str | None = None
    reason_codes: list[str] = Field(default_factory=list)


class IdentitySection(BaseModel):
    full_name: ConfidentValue | None = None
    email: ConfidentValue | None = None
    phone: ConfidentValue | None = None
    country: ConfidentValue | None = None


class DesiredPosition(BaseModel):
    raw: str
    normalized: str | None = None
    source_type: DesiredPositionSourceType
    confidence: Confidence


class TargetSection(BaseModel):
    desired_positions: list[DesiredPosition] = Field(default_factory=list)
    desired_contract_types: list[ContractType] = Field(default_factory=list)
    desired_work_modes: list[WorkMode] = Field(default_factory=list)


class PartialDate(BaseModel):
    year: int | None = None
    month: int | None = None
    day: int | None = None
    precision: DatePrecision | None = None


class ExperienceRecord(BaseModel):
    id: str
    type: ExperienceType
    title: str | None = None
    start_date: PartialDate | None = None
    end_date: PartialDate | None = None
    is_current: bool = False
    raw_text: str | None = None
    technologies: list[str] = Field(default_factory=list)
    confidence: Confidence = "LOW"


class ExperienceSection(BaseModel):
    professional_months: int = 0
    internship_months: int = 0
    alternance_months: int = 0
    freelance_months: int = 0
    records: list[ExperienceRecord] = Field(default_factory=list)


class SkillEvidence(BaseModel):
    source_type: SkillEvidenceSourceType
    source_id: str | None = None
    source_label: str | None = None
    raw_text: str | None = None


class KnownSkill(BaseModel):
    canonical_name: str
    category: SkillCategory | None = None
    raw_mentions: list[str] = Field(default_factory=list)
    evidence: list[SkillEvidence] = Field(default_factory=list)


class UnmappedTechnology(BaseModel):
    raw_name: str
    known: bool = False
    source_type: SkillEvidenceSourceType | None = None
    evidence: list[SkillEvidence] = Field(default_factory=list)


class SkillsSection(BaseModel):
    known: list[KnownSkill] = Field(default_factory=list)
    unmapped_technology_candidates: list[UnmappedTechnology] = Field(default_factory=list)


class LanguageEntry(BaseModel):
    language: str
    raw_level: str | None = None
    normalized_level: CEFRLevel | None = None
    confidence: Confidence = "LOW"


class CertificationEntry(BaseModel):
    id: str
    name: str
    issuer: str | None = None
    date: PartialDate | None = None
    technology_evidence: list[str] = Field(default_factory=list)


class ParseQuality(BaseModel):
    status: ParseQualityStatus = "GOOD"
    section_coverage: float | None = None
    orphan_ratio: float | None = None
    record_coherence: float | None = None
    warnings: list[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    field: str
    reason: str
    confidence: Confidence | None = None


class ParseMeta(BaseModel):
    """Ingestion/runtime diagnostics. Not part of the ML-forbidden surface —
    purely operational facts about how this specific document was parsed."""

    parser_version: str
    page_count: int
    used_ocr: bool = False
    overall_page_state: str | None = None
    reading_strategy: str | None = None
    parse_duration_ms: float | None = None
    word_count: int = 0
    line_count: int = 0
    block_count: int = 0
    sections_found: int = 0
    unknown_section_count: int = 0


class ParserDraftResponse(BaseModel):
    identity: IdentitySection = Field(default_factory=IdentitySection)
    target: TargetSection = Field(default_factory=TargetSection)
    experience: ExperienceSection = Field(default_factory=ExperienceSection)
    skills: SkillsSection = Field(default_factory=SkillsSection)
    languages: list[LanguageEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    parse_quality: ParseQuality = Field(default_factory=ParseQuality)
    review_items: list[ReviewItem] = Field(default_factory=list)
    meta: ParseMeta
