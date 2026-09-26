"""Single runtime source for the frozen five-field extraction ontology."""
from __future__ import annotations

import json
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any


ONTOLOGY_PATH = Path(__file__).with_name("ontology.json")
FIELD_NAMES = (
    "education_level",
    "work_mode",
    "contract_type",
    "minimum_experience_bracket",
    "seniority_level",
)


@lru_cache(maxsize=1)
def _load() -> dict[str, tuple[str, ...]]:
    raw = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    if tuple(raw) != FIELD_NAMES:
        raise ValueError("ontology field order is not locked")
    result: dict[str, tuple[str, ...]] = {}
    for field in FIELD_NAMES:
        values = tuple(str(value) for value in raw.get(field, []))
        if not values or len(values) != len(set(values)):
            raise ValueError(f"invalid ontology values for {field}")
        result[field] = values
    return result


FIELD_LABELS = _load()


def labels_for(field: str) -> tuple[str, ...]:
    try:
        return FIELD_LABELS[field]
    except KeyError as exc:
        raise KeyError(f"unknown extraction field: {field}") from exc


def is_valid_label(field: str, value: Any) -> bool:
    return isinstance(value, str) and value in labels_for(field)


def unknown_label(field: str) -> str:
    values = labels_for(field)
    if "UNKNOWN" not in values:
        raise ValueError(f"field has no UNKNOWN label: {field}")
    return "UNKNOWN"


def _enum(name: str, field: str) -> type[Enum]:
    return Enum(name, {value: value for value in labels_for(field)}, type=str)


# Runtime enums are generated from ontology.json; no second label list is maintained.
EducationLevel = _enum("EducationLevel", "education_level")
WorkMode = _enum("WorkMode", "work_mode")
ContractType = _enum("ContractType", "contract_type")
MinimumExperienceBracket = _enum("MinimumExperienceBracket", "minimum_experience_bracket")
SeniorityLevel = _enum("SeniorityLevel", "seniority_level")


def normalize_label(field: str, value: str | None) -> str:
    """Normalize legacy input aliases at a boundary; never emit an alias."""
    raw = (value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases: dict[str, dict[str, str]] = {
        "education_level": {
            "ENGINEER": "MASTER_OR_HIGHER",
            "ENGINEERING_DEGREE": "MASTER_OR_HIGHER",
            "PHD": "MASTER_OR_HIGHER",
            "DOCTORATE": "MASTER_OR_HIGHER",
            "MASTER": "MASTER_OR_HIGHER",
            "VOCATIONAL_DIPLOMA": "ASSOCIATE",
            "PROFESSIONAL_DIPLOMA": "ASSOCIATE",
            "BAC+2": "ASSOCIATE",
            "BAC_2": "ASSOCIATE",
            "BAC+3": "BACHELOR",
            "BAC_3": "BACHELOR",
            "BAC+5": "MASTER_OR_HIGHER",
            "BAC_5": "MASTER_OR_HIGHER",
        },
        "contract_type": {
            "CDI": "PERMANENT",
            "CDD": "FIXED_TERM",
            "CONTRACTOR": "FREELANCE",
            "CONTRACT": "FREELANCE",
        },
        "seniority_level": {
            "INTERN": "INTERN_ENTRY",
            "ENTRY": "INTERN_ENTRY",
            "LEAD": "LEAD_PRINCIPAL",
            "PRINCIPAL": "LEAD_PRINCIPAL",
            "MANAGER": "LEAD_PRINCIPAL",
            "DIRECTOR": "LEAD_PRINCIPAL",
            "EXECUTIVE": "LEAD_PRINCIPAL",
        },
    }
    normalized = aliases.get(field, {}).get(raw, raw)
    return normalized if normalized in labels_for(field) else unknown_label(field)
