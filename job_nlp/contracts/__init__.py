"""Shared rule/ML field contract for the five job extraction fields."""

from job_nlp.contracts.business_policy import (
    build_field_result,
    hybrid_field_result,
    result_from_rule_hit,
    result_from_ml,
    to_bracket,
    unknown_field_result,
    validate_field_result,
)
from job_nlp.contracts.ontology import FIELD_LABELS, FIELD_NAMES, labels_for

__all__ = [
    "FIELD_LABELS",
    "FIELD_NAMES",
    "labels_for",
    "build_field_result",
    "hybrid_field_result",
    "result_from_rule_hit",
    "result_from_ml",
    "to_bracket",
    "unknown_field_result",
    "validate_field_result",
    "extract_rule_fields",
    "adapt_ml_fields",
    "resolve_hybrid_fields",
]


def __getattr__(name: str):
    if name in {"extract_rule_fields", "adapt_ml_fields", "resolve_hybrid_fields"}:
        from job_nlp.contracts import adapters

        return getattr(adapters, name)
    raise AttributeError(name)
