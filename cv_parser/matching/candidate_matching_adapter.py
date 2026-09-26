"""CV matching adapter — confirmed profile + survey → CandidateKnowledgeProfile."""
from __future__ import annotations

from typing import Any

from cv_parser.schemas.verified_profile import (
    CandidateKnowledgeProfile,
    LocationPreferences,
    ProfileCertification,
    ProfileExperience,
    ProfileIdentity,
    ProfileLanguage,
    ProfileSkill,
    ProfileSkillEvidence,
    ProfileTarget,
)
from shared_matching.skill_identity import canonicalize_skill_name


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, dict) and "value" in value:
        return str(value.get("value") or default)
    return str(value)


def profile_from_confirmed_and_survey(
    confirmed: dict[str, Any] | None = None,
    survey: dict[str, Any] | None = None,
    *,
    draft_normalized: dict[str, Any] | None = None,
) -> CandidateKnowledgeProfile:
    """Merge product confirmed profile + preference survey into matching profile.

    Empty rather than invent. Skill names are canonicalized for job comparison.
    """
    confirmed = confirmed or {}
    survey = survey or {}
    base = draft_normalized or {}

    identity_src = confirmed.get("identity") or base.get("identity") or {}
    identity = ProfileIdentity(
        full_name=_str(identity_src.get("full_name") or identity_src.get("fullName")),
        email=_str(identity_src.get("email")),
        phone=_str(identity_src.get("phone")),
        country=_str(identity_src.get("country")),
    )

    # Survey wins for prefs; confirmed may already store them after PreferenceSurveyPage.
    mobility = _as_list(
        survey.get("mobility_preferences")
        or survey.get("mobilityPreferences")
        or confirmed.get("mobility_preferences")
        or confirmed.get("mobilityPreferences")
    )
    preferred_countries = _as_list(
        survey.get("preferred_countries")
        or survey.get("preferredCountries")
        or confirmed.get("preferred_countries")
        or confirmed.get("preferredCountries")
    )
    contract_types = _as_list(
        survey.get("desired_contract_types")
        or survey.get("desiredContractTypes")
        or confirmed.get("desired_contract_types")
        or confirmed.get("desiredContractTypes")
        or (base.get("target") or {}).get("desired_contract_types")
    )
    work_modes = _as_list(
        survey.get("desired_work_modes")
        or survey.get("desiredWorkModes")
        or confirmed.get("desired_work_modes")
        or confirmed.get("desiredWorkModes")
        or (base.get("target") or {}).get("desired_work_modes")
    )

    target_src = confirmed.get("target") or base.get("target") or {}
    positions = _as_list(
        confirmed.get("desired_positions")
        or confirmed.get("desiredPositions")
        or target_src.get("desired_positions")
    )
    families = _as_list(target_src.get("desired_job_families") or confirmed.get("desired_job_families"))
    seniority = _as_list(target_src.get("desired_seniority") or confirmed.get("desired_seniority"))

    location = LocationPreferences(
        current_country=identity.country,
        mobility_preferences=[m for m in mobility if m in ("LOCAL", "FOREIGN", "REMOTE")],  # type: ignore[misc]
        preferred_countries=[str(c) for c in preferred_countries if c],
    )

    exp_src = confirmed.get("experience") or base.get("experience") or {}
    experience = ProfileExperience(
        professional_months=int(exp_src.get("professional_months") or exp_src.get("professionalMonths") or 0),
        internship_months=int(exp_src.get("internship_months") or exp_src.get("internshipMonths") or 0),
        alternance_months=int(exp_src.get("alternance_months") or exp_src.get("alternanceMonths") or 0),
        freelance_months=int(exp_src.get("freelance_months") or exp_src.get("freelanceMonths") or 0),
        total_months=int(exp_src.get("total_months") or exp_src.get("totalMonths") or 0),
    )
    if experience.total_months <= 0:
        experience.total_months = (
            experience.professional_months
            + experience.internship_months
            + experience.alternance_months
            + experience.freelance_months
        )

    skills_raw = confirmed.get("skills") or base.get("skills") or []
    if isinstance(skills_raw, dict):
        skills_raw = skills_raw.get("known") or []
    skills: list[ProfileSkill] = []
    seen: set[str] = set()
    for s in skills_raw:
        if not isinstance(s, dict):
            continue
        name = canonicalize_skill_name(s.get("name") or s.get("canonical_name") or s.get("canonicalName") or "")
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        level = str(s.get("level") or "BASIC").upper()
        if level not in ("BASIC", "INTERMEDIATE", "ADVANCED"):
            level = "BASIC"
        conf = float(s.get("confidence") or 0.7)
        skills.append(
            ProfileSkill(
                name=name,
                category=str(s.get("category") or "OTHER_IT"),
                level=level,  # type: ignore[arg-type]
                confidence=max(0.0, min(1.0, conf)),
            )
        )

    # customSkills (user-added) — names only
    for raw in _as_list(confirmed.get("customSkills") or confirmed.get("custom_skills")):
        name = canonicalize_skill_name(str(raw) if not isinstance(raw, dict) else (raw.get("name") or ""))
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        skills.append(ProfileSkill(name=name, category="OTHER_IT", level="BASIC", confidence=0.5))

    evidence_raw = confirmed.get("skill_evidence") or base.get("skill_evidence") or []
    evidence: list[ProfileSkillEvidence] = []
    for e in evidence_raw:
        if not isinstance(e, dict):
            continue
        skill = canonicalize_skill_name(e.get("skill") or "")
        if not skill:
            continue
        evidence.append(
            ProfileSkillEvidence(
                skill=skill,
                source_type=str(e.get("source_type") or e.get("sourceType") or ""),
                source_label=str(e.get("source_label") or e.get("sourceLabel") or ""),
                source_id=e.get("source_id") or e.get("sourceId"),
                confidence=float(e.get("confidence") or 0.5),
                evidence_text=str(e.get("evidence_text") or e.get("evidenceText") or ""),
            )
        )

    langs = []
    for lg in _as_list(confirmed.get("languages") or base.get("languages")):
        if not isinstance(lg, dict):
            continue
        lang = _str(lg.get("language") or lg.get("name"))
        if not lang:
            continue
        level = lg.get("level") or lg.get("normalized_level")
        if isinstance(level, dict):
            level = level.get("value")
        langs.append(ProfileLanguage(language=lang, level=level if level else None))

    certs = []
    for c in _as_list(confirmed.get("certifications") or base.get("certifications")):
        if not isinstance(c, dict):
            continue
        name = _str(c.get("name"))
        if not name:
            continue
        certs.append(
            ProfileCertification(
                name=name,
                issuer=_str(c.get("issuer")),
                year=_str(c.get("year") or c.get("date")),
            )
        )

    # Filter contract/work to known CV enums
    cv_contracts = [c for c in contract_types if str(c).upper() in {"CDI", "CDD", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "OTHER"}]
    cv_modes = [m for m in work_modes if str(m).upper() in {"REMOTE", "HYBRID", "ONSITE"}]

    return CandidateKnowledgeProfile(
        identity=identity,
        location_preferences=location,
        target=ProfileTarget(
            desired_positions=[str(p) for p in positions if p],
            desired_job_families=families,  # type: ignore[arg-type]
            desired_contract_types=cv_contracts,  # type: ignore[arg-type]
            desired_work_modes=cv_modes,  # type: ignore[arg-type]
            desired_seniority=seniority,  # type: ignore[arg-type]
        ),
        experience=experience,
        skills=skills,
        skill_evidence=evidence,
        languages=langs,
        certifications=certs,
    )


def profile_from_confirmed_and_survey_dict(
    confirmed: dict[str, Any] | None = None,
    survey: dict[str, Any] | None = None,
    draft_normalized: dict[str, Any] | None = None,
) -> dict:
    return profile_from_confirmed_and_survey(
        confirmed, survey, draft_normalized=draft_normalized
    ).model_dump(mode="json")
