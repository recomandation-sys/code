"""Shared evidence, enum, experience, and hybrid policy implementation."""
from __future__ import annotations

import re
from typing import Any, Mapping

from job_nlp.contracts.ontology import FIELD_LABELS, is_valid_label, normalize_label, unknown_label


_URL_OR_EMAIL = re.compile(r"(?:https?://|www\.|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b)", re.I)
_SOURCE_VALUES = {"TITLE", "DESCRIPTION", "UNKNOWN"}
_PUBLIC_SOURCES = {"RULE", "ML", "HYBRID", "UNKNOWN"}


def unknown_field_result(field: str) -> dict[str, Any]:
    """Return the exact contract UNKNOWN object."""
    return {
        "value": unknown_label(field),
        "confidence": 0.0,
        "source": "UNKNOWN",
        "evidence": {"text": None, "start": None, "end": None, "source": "UNKNOWN"},
        "warnings": [],
    }


def _valid_evidence(
    title: str,
    description: str,
    text: Any,
    start: Any,
    end: Any,
    source: Any,
) -> bool:
    if not isinstance(text, str) or not text:
        return False
    source_name = str(source or "UNKNOWN").upper()
    if source_name not in _SOURCE_VALUES or source_name == "UNKNOWN":
        return False
    if _URL_OR_EMAIL.search(text):
        return False
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
        return False
    original = title if source_name == "TITLE" else description
    return end <= len(original) and original[start:end] == text


def validate_field_result(field: str, result: Mapping[str, Any], *, title: str = "", description: str = "") -> bool:
    if not isinstance(result, Mapping) or not is_valid_label(field, result.get("value")):
        return False
    if result.get("value") == "UNKNOWN":
        return result == unknown_field_result(field)
    if result.get("source") not in {"RULE", "ML", "HYBRID"}:
        return False
    evidence = result.get("evidence")
    if not isinstance(evidence, Mapping):
        return False
    return _valid_evidence(title, description, evidence.get("text"), evidence.get("start"), evidence.get("end"), evidence.get("source"))


def build_field_result(
    field: str,
    value: str | None,
    *,
    confidence: float = 0.0,
    source: str = "RULE",
    evidence_text: str | None = None,
    evidence_start: int | None = None,
    evidence_end: int | None = None,
    evidence_source: str = "UNKNOWN",
    title: str = "",
    description: str = "",
    warnings: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    label = normalize_label(field, value)
    if label == "UNKNOWN":
        return unknown_field_result(field)
    source_name = source if source in _PUBLIC_SOURCES - {"UNKNOWN"} else "RULE"
    if not _valid_evidence(title, description, evidence_text, evidence_start, evidence_end, evidence_source):
        return unknown_field_result(field)
    return {
        "value": label,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "source": source_name,
        "evidence": {
            "text": evidence_text,
            "start": evidence_start,
            "end": evidence_end,
            "source": str(evidence_source).upper(),
        },
        "warnings": list(warnings or []),
    }


def result_from_rule_hit(field: str, hit: Any, *, title: str = "", description: str = "") -> dict[str, Any]:
    if hit is None:
        return unknown_field_result(field)
    return build_field_result(
        field,
        getattr(hit, "value", None),
        confidence=float(getattr(hit, "confidence", 0.0) or 0.0),
        source="RULE",
        evidence_text=getattr(hit, "evidence_text", None),
        evidence_start=getattr(hit, "evidence_start", None),
        evidence_end=getattr(hit, "evidence_end", None),
        evidence_source=getattr(hit, "evidence_source", "UNKNOWN"),
        title=title,
        description=description,
        warnings=list(getattr(hit, "warnings", []) or []),
    )


def result_from_ml(field: str, payload: Mapping[str, Any] | None, *, title: str = "", description: str = "") -> dict[str, Any]:
    payload = payload or {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), Mapping) else {}
    return build_field_result(
        field,
        payload.get("value", payload.get("label")),
        confidence=float(payload.get("confidence", 0.0) or 0.0),
        source="ML",
        evidence_text=evidence.get("text", payload.get("exact_evidence")),
        evidence_start=evidence.get("start", payload.get("start_char")),
        evidence_end=evidence.get("end", payload.get("end_char")),
        evidence_source=evidence.get("source", payload.get("evidence_source", "UNKNOWN")),
        title=title,
        description=description,
        warnings=list(payload.get("warnings") or []),
    )


def hybrid_field_result(
    field: str,
    rule_result: Mapping[str, Any] | None,
    ml_result: Mapping[str, Any] | None,
    *,
    threshold: float = 0.65,
) -> dict[str, Any]:
    """Apply deterministic rule-first hybrid precedence on normalized results."""
    rule = dict(rule_result or unknown_field_result(field))
    ml = dict(ml_result or unknown_field_result(field))
    rule_known = rule.get("value") != "UNKNOWN" and rule.get("source") == "RULE"
    ml_known = ml.get("value") != "UNKNOWN" and ml.get("source") == "ML"
    if rule_known:
        chosen = dict(rule)
        warnings = list(chosen.get("warnings") or [])
        if ml_known and ml.get("value") != rule.get("value"):
            warnings.append("RULE_ML_CONTRADICTION")
        chosen["source"] = "HYBRID"
        chosen["warnings"] = list(dict.fromkeys(warnings))
        return chosen
    if ml_known and float(ml.get("confidence", 0.0) or 0.0) >= threshold:
        chosen = dict(ml)
        chosen["source"] = "HYBRID"
        return chosen
    return unknown_field_result(field)


def to_bracket(value_months: int | float | None, comparator: str = "EQ") -> str:
    """Normalize months according to the frozen bracket policy."""
    if value_months is None:
        return "UNKNOWN"
    try:
        months = float(value_months)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if months < 0:
        return "UNKNOWN"
    if str(comparator).upper() == "GT":
        months += 1.0
    if months < 12:
        return "0_YEARS"
    if months < 36:
        return "1_2_YEARS"
    if months < 60:
        return "3_5_YEARS"
    if months < 96:
        return "5_7_YEARS"
    return "8_PLUS_YEARS"

