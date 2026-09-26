"""Thin adapters exposing rules, ML payloads, and hybrid decisions uniformly."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from job_nlp.contracts.business_policy import (
    build_field_result,
    hybrid_field_result,
    result_from_ml,
    result_from_rule_hit,
    unknown_field_result,
)
from job_nlp.contracts.ontology import FIELD_NAMES
from job_nlp.extraction.seniority_experience_extractor import extract_seniority
from job_nlp.rules.contract import extract_contract
from job_nlp.rules.education import extract_education
from job_nlp.rules.experience import extract_experience
from job_nlp.rules.seniority import extract_seniority_from_title
from job_nlp.rules.work_mode import extract_work_mode


def _seniority_rule_hit(title: str, description: str, contract_type: str | None = None) -> Any:
    result = extract_seniority(title, description, contract_type)
    return {
        "value": result.seniority_level.value,
        "confidence": 0.95 if result.evidence_text else 0.0,
        "evidence_text": result.evidence_text,
        "evidence_start": result.evidence_start,
        "evidence_end": result.evidence_end,
        "evidence_source": "TITLE" if result.evidence_source == "TITLE_EXPLICIT" else "DESCRIPTION" if result.evidence_source == "DESCRIPTION_TENURE" else result.evidence_source if result.evidence_source in {"TITLE", "DESCRIPTION"} else "UNKNOWN",
        "warnings": [],
    }


def extract_rule_fields(title: str, description: str) -> dict[str, dict[str, Any]]:
    """Return exactly the five normalized rule results."""
    contract_hit = extract_contract(title, description)
    contract_result = result_from_rule_hit("contract_type", contract_hit, title=title, description=description)
    contract_value = contract_result["value"]
    seniority_hit = _seniority_rule_hit(title, description, contract_value)
    # The seniority helper is already a dictionary-shaped hit; adapt it without
    # introducing a second evidence policy.
    seniority_result = build_field_result(
        "seniority_level",
        seniority_hit["value"],
        confidence=seniority_hit["confidence"],
        source="RULE",
        evidence_text=seniority_hit["evidence_text"],
        evidence_start=seniority_hit["evidence_start"],
        evidence_end=seniority_hit["evidence_end"],
        evidence_source=seniority_hit["evidence_source"],
        title=title,
        description=description,
        warnings=seniority_hit["warnings"],
    )
    fields = {
        "education_level": result_from_rule_hit("education_level", extract_education(title, description), title=title, description=description),
        "work_mode": result_from_rule_hit("work_mode", extract_work_mode(title, description), title=title, description=description),
        "contract_type": contract_result,
        "minimum_experience_bracket": result_from_rule_hit("minimum_experience_bracket", extract_experience(title, description), title=title, description=description),
        "seniority_level": seniority_result,
    }
    return {field: fields.get(field, unknown_field_result(field)) for field in FIELD_NAMES}


def adapt_ml_fields(
    payload: Mapping[str, Mapping[str, Any]] | None,
    *,
    title: str = "",
    description: str = "",
) -> dict[str, dict[str, Any]]:
    payload = payload or {}
    return {
        field: result_from_ml(field, payload.get(field), title=title, description=description)
        for field in FIELD_NAMES
    }


def resolve_hybrid_fields(
    title: str,
    description: str,
    ml_payload: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    threshold: float = 0.65,
) -> dict[str, dict[str, Any]]:
    rules = extract_rule_fields(title, description)
    models = adapt_ml_fields(ml_payload, title=title, description=description)
    return {
        field: hybrid_field_result(field, rules[field], models[field], threshold=threshold)
        for field in FIELD_NAMES
    }
