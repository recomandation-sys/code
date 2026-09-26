"""Transform parser draft JSON into a Candidate Knowledge Profile.

Only reads fields already present in ``ParserDraftResponse`` — no PDF access,
no invented values. Missing identity or location fields stay empty strings /
empty lists rather than being guessed.
"""
from __future__ import annotations

from cv_parser.schemas.parser_response import (
    CEFRLevel,
    KnownSkill,
    ParserDraftResponse,
    SkillEvidence,
    SkillEvidenceSourceType,
)
from cv_parser.schemas.verified_profile import (
    CandidateKnowledgeProfile,
    JobFamily,
    LocationPreferences,
    MobilityPreference,
    NormalizedLanguageLevel,
    ProfileCertification,
    ProfileExperience,
    ProfileIdentity,
    ProfileLanguage,
    ProfileSkill,
    ProfileSkillEvidence,
    ProfileTarget,
    SeniorityLevel,
    SkillProficiencyLevel,
)

_STRONG_EVIDENCE: frozenset[SkillEvidenceSourceType] = frozenset(
    {"PROFESSIONAL_EXPERIENCE", "INTERNSHIP", "ALTERNANCE", "PROJECT"}
)
_MEDIUM_EVIDENCE: frozenset[SkillEvidenceSourceType] = frozenset(
    {"SKILLS_SECTION", "CERTIFICATION", "EDUCATION"}
)

_COUNTRY_NAMES: dict[str, str] = {
    "tunisia": "Tunisia",
    "tunisie": "Tunisia",
    "france": "France",
    "germany": "Germany",
    "allemagne": "Germany",
    "united states": "United States",
    "usa": "United States",
    "canada": "Canada",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "spain": "Spain",
    "espagne": "Spain",
    "italy": "Italy",
    "italie": "Italy",
    "belgium": "Belgium",
    "belgique": "Belgium",
    "morocco": "Morocco",
    "maroc": "Morocco",
    "algeria": "Algeria",
    "algérie": "Algeria",
}

_FOREIGN_HINTS = (
    "relocate",
    "relocation",
    "mobilité",
    "mobilite",
    "international",
    "abroad",
    "étranger",
    "etranger",
    "overseas",
)

_JOB_FAMILY_RULES: list[tuple[JobFamily, tuple[str, ...]]] = [
    ("FRONTEND_DEVELOPER", ("frontend", "front-end", "front end", "react developer", "vue developer", "angular")),
    ("BACKEND_DEVELOPER", ("backend", "back-end", "back end", "api developer", "server-side")),
    ("FULLSTACK_DEVELOPER", ("full stack", "fullstack", "full-stack", "mern", "mean stack")),
    ("MOBILE_DEVELOPER", ("mobile developer", "android developer", "ios developer", "flutter developer")),
    ("DEVOPS_ENGINEER", ("devops", "sre", "site reliability", "platform engineer")),
    ("DATA_SCIENTIST", ("data scientist", "machine learning engineer", "ml engineer", "ai engineer")),
    ("DATA_ENGINEER", ("data engineer", "etl developer", "big data engineer")),
    ("QA_ENGINEER", ("qa engineer", "quality assurance", "test engineer", "sdet")),
    ("SECURITY_ENGINEER", ("security engineer", "cybersecurity", "infosec")),
    ("CLOUD_ENGINEER", ("cloud engineer", "cloud architect", "aws engineer")),
    ("PRODUCT_MANAGER", ("product manager", "product owner", "chef de produit")),
    ("SOFTWARE_ENGINEER", ("software engineer", "software developer", "développeur", "developpeur", "programmer")),
]

_SENIORITY_KEYWORDS: list[tuple[SeniorityLevel, tuple[str, ...]]] = [
    ("INTERN", ("intern", "internship", "stagiaire", "stage")),
    ("JUNIOR", ("junior", "entry level", "entry-level", "débutant", "debutant")),
    ("MID", ("mid level", "mid-level", "intermediate")),
    ("SENIOR", ("senior", "sr.", "sr ")),
    ("LEAD", ("lead", "tech lead", "team lead", "principal")),
    ("MANAGER", ("manager", "management", "head of")),
]

_LANGUAGE_LEVEL_MAP: dict[CEFRLevel, NormalizedLanguageLevel | None] = {
    "A1": "A1",
    "A2": "A2",
    "B1": "B1",
    "B2": "B2",
    "C1": "C1",
    "C2": "C2",
    "NATIVE": "NATIVE",
    "FLUENT": "FLUENT",
    "ADVANCED": "C1",
    "INTERMEDIATE": "B1",
    "BASIC": "A2",
    "UNKNOWN": None,
}


def _confident_string(value: str | None) -> str:
    return (value or "").strip()


def _evidence_confidence(source_type: SkillEvidenceSourceType) -> float:
    if source_type in _STRONG_EVIDENCE:
        return 1.0
    if source_type in _MEDIUM_EVIDENCE:
        return 0.7
    return 0.3


def _skill_level(max_confidence: float, strong_count: int) -> SkillProficiencyLevel:
    if max_confidence >= 1.0 and strong_count >= 2:
        return "ADVANCED"
    if max_confidence >= 1.0 or max_confidence >= 0.7:
        return "INTERMEDIATE"
    return "BASIC"


def _normalize_language_level(level: CEFRLevel | None) -> NormalizedLanguageLevel | None:
    if level is None:
        return None
    return _LANGUAGE_LEVEL_MAP.get(level)


def _collect_searchable_text(draft: ParserDraftResponse) -> str:
    chunks: list[str] = []
    for position in draft.target.desired_positions:
        chunks.append(position.raw)
        if position.normalized:
            chunks.append(position.normalized)
    for record in draft.experience.records:
        if record.title:
            chunks.append(record.title)
        if record.raw_text:
            chunks.append(record.raw_text)
    for cert in draft.certifications:
        chunks.append(cert.name)
        if cert.issuer:
            chunks.append(cert.issuer)
    return " ".join(chunks).lower()


def _find_countries(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for needle, canonical in _COUNTRY_NAMES.items():
        if needle in text and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


def _infer_mobility(
    draft: ParserDraftResponse,
    preferred_countries: list[str],
    searchable_text: str,
) -> list[MobilityPreference]:
    mobility: list[MobilityPreference] = []
    work_modes = set(draft.target.desired_work_modes)

    if "REMOTE" in work_modes:
        mobility.append("REMOTE")
    if work_modes.intersection({"ONSITE", "HYBRID"}):
        mobility.append("LOCAL")
    if preferred_countries or any(hint in searchable_text for hint in _FOREIGN_HINTS):
        mobility.append("FOREIGN")

    deduped: list[MobilityPreference] = []
    for item in mobility:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _infer_job_families(text: str) -> list[JobFamily]:
    families: list[JobFamily] = []
    for family, keywords in _JOB_FAMILY_RULES:
        if any(keyword in text for keyword in keywords):
            families.append(family)
    if not families and any(k in text for k in ("developer", "engineer", "développeur", "developpeur")):
        families.append("SOFTWARE_ENGINEER")
    deduped: list[JobFamily] = []
    for family in families:
        if family not in deduped:
            deduped.append(family)
    return deduped


def _infer_seniority(draft: ParserDraftResponse, searchable_text: str) -> list[SeniorityLevel]:
    seniority: list[SeniorityLevel] = []
    for level, keywords in _SENIORITY_KEYWORDS:
        if any(keyword in searchable_text for keyword in keywords):
            seniority.append(level)

    exp = draft.experience
    if not seniority:
        total_months = (
            exp.professional_months + exp.internship_months + exp.alternance_months + exp.freelance_months
        )
        if exp.internship_months > 0 and exp.professional_months == 0 and exp.freelance_months == 0:
            seniority.append("INTERN")
        elif total_months < 24:
            seniority.append("JUNIOR")

    deduped: list[SeniorityLevel] = []
    for level in seniority:
        if level not in deduped:
            deduped.append(level)
    return deduped


def _map_identity(draft: ParserDraftResponse) -> ProfileIdentity:
    def _field(field) -> str:
        if field and field.value:
            return field.value.strip()
        return ""

    return ProfileIdentity(
        full_name=_field(draft.identity.full_name),
        email=_field(draft.identity.email),
        phone=_field(draft.identity.phone),
        country=_field(draft.identity.country),
    )


def _map_location(draft: ParserDraftResponse) -> LocationPreferences:
    current_country = ""
    if draft.identity.country and draft.identity.country.value:
        current_country = draft.identity.country.value.strip()

    # Preferred countries and mobility are collected via the post-validation
    # survey — do not infer them from experience text.
    mobility = _infer_mobility(draft, [], "")
    return LocationPreferences(
        current_country=current_country,
        mobility_preferences=mobility,
        preferred_countries=[],
    )


def _map_target(draft: ParserDraftResponse) -> ProfileTarget:
    searchable = _collect_searchable_text(draft).lower()
    positions: list[str] = []
    for position in draft.target.desired_positions:
        label = (position.normalized or position.raw).strip()
        if label and label not in positions:
            positions.append(label)

    return ProfileTarget(
        desired_positions=positions,
        desired_job_families=_infer_job_families(searchable),
        desired_contract_types=list(draft.target.desired_contract_types),
        desired_work_modes=list(draft.target.desired_work_modes),
        desired_seniority=_infer_seniority(draft, searchable),
    )


def _map_experience(draft: ParserDraftResponse) -> ProfileExperience:
    exp = draft.experience
    total = exp.professional_months + exp.internship_months + exp.alternance_months + exp.freelance_months
    return ProfileExperience(
        professional_months=exp.professional_months,
        internship_months=exp.internship_months,
        alternance_months=exp.alternance_months,
        freelance_months=exp.freelance_months,
        total_months=total,
    )


def _evidence_text(evidence: SkillEvidence) -> str:
    return (evidence.raw_text or "").strip()


def _map_skills(draft: ParserDraftResponse) -> tuple[list[ProfileSkill], list[ProfileSkillEvidence]]:
    skills: list[ProfileSkill] = []
    evidence_rows: list[ProfileSkillEvidence] = []

    for known in draft.skills.known:
        skill_name, skill_row, rows = _map_known_skill(known)
        skills.append(skill_row)
        evidence_rows.extend(rows)

    skills.sort(key=lambda s: (-s.confidence, s.name.lower()))
    return skills, evidence_rows


def _map_known_skill(known: KnownSkill) -> tuple[str, ProfileSkill, list[ProfileSkillEvidence]]:
    evidence_rows: list[ProfileSkillEvidence] = []
    confidences: list[float] = []
    strong_count = 0

    for evidence in known.evidence:
        confidence = _evidence_confidence(evidence.source_type)
        confidences.append(confidence)
        if confidence >= 1.0:
            strong_count += 1
        evidence_rows.append(
            ProfileSkillEvidence(
                skill=known.canonical_name,
                source_type=evidence.source_type,
                source_label=(evidence.source_label or "").strip(),
                source_id=evidence.source_id,
                confidence=confidence,
                evidence_text=_evidence_text(evidence),
            )
        )

    max_confidence = max(confidences) if confidences else 0.3
    category = known.category or "OTHER_IT"
    skill_row = ProfileSkill(
        name=known.canonical_name,
        category=category,
        level=_skill_level(max_confidence, strong_count),
        confidence=round(max_confidence, 2),
    )
    return known.canonical_name, skill_row, evidence_rows


def _map_languages(draft: ParserDraftResponse) -> list[ProfileLanguage]:
    languages: list[ProfileLanguage] = []
    for entry in draft.languages:
        level = _normalize_language_level(entry.normalized_level)
        languages.append(ProfileLanguage(language=entry.language, level=level))
    return languages


def _map_certifications(draft: ParserDraftResponse) -> list[ProfileCertification]:
    certs: list[ProfileCertification] = []
    for entry in draft.certifications:
        year = ""
        if entry.date and entry.date.year is not None:
            year = str(entry.date.year)
        certs.append(
            ProfileCertification(
                name=entry.name.strip(),
                issuer=_confident_string(entry.issuer),
                year=year,
            )
        )
    return certs


def normalize_candidate_profile(draft: ParserDraftResponse) -> CandidateKnowledgeProfile:
    """Transform a parser draft into a recommendation-ready candidate profile."""
    skills, skill_evidence = _map_skills(draft)
    return CandidateKnowledgeProfile(
        identity=_map_identity(draft),
        location_preferences=_map_location(draft),
        target=_map_target(draft),
        experience=_map_experience(draft),
        skills=skills,
        skill_evidence=skill_evidence,
        languages=_map_languages(draft),
        certifications=_map_certifications(draft),
    )


def normalize_candidate_profile_dict(draft: dict) -> dict:
    """Convenience wrapper accepting raw draft JSON."""
    parsed = ParserDraftResponse.model_validate(draft)
    return normalize_candidate_profile(parsed).model_dump(mode="json")
