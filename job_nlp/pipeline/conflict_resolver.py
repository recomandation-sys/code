"""Conflict resolution between rules, taxonomy and neural predictions."""
from __future__ import annotations

from job_nlp.pipeline.schemas import RuleHit, TaxonomyCandidate
from job_nlp.rules.title_rules import seniority_from_experience


def resolve_job_family_parent(
    taxonomy_parent: str,
    taxonomy_leaf: str,
    model_result: RuleHit | None = None,
    best_candidate: TaxonomyCandidate | None = None,
) -> tuple[str, str]:
    """Merge taxonomy evidence with TF-IDF/XLM-R parent prediction."""
    if model_result and model_result.value and model_result.confidence and model_result.confidence >= 0.55:
        parent = str(model_result.value)
        if taxonomy_leaf != "UNKNOWN" and taxonomy_parent == parent and best_candidate:
            return parent, taxonomy_leaf
        if taxonomy_parent == parent and taxonomy_leaf != "UNKNOWN":
            return parent, taxonomy_leaf
        return parent, taxonomy_leaf if taxonomy_parent == parent else "UNKNOWN"

    if taxonomy_parent != "UNKNOWN":
        return taxonomy_parent, taxonomy_leaf
    return "UNKNOWN", "UNKNOWN"


def resolve_seniority(
    title_rule: RuleHit,
    experience_months: int | None,
    model_result: RuleHit | None = None,
) -> RuleHit:
    """Legacy pre-Phase-H path (experience→label). Prefer resolve_seniority_hybrid."""
    if title_rule.value and title_rule.confidence >= 0.9:
        return title_rule
    if model_result and model_result.value and model_result.confidence and model_result.confidence >= 0.7:
        return model_result
    # Forbidden in Phase H production — kept only so H1 can reproduce Acc≈0.6367 / Macro-F1≈0.6218
    exp_hit = seniority_from_experience(experience_months)
    if exp_hit.value:
        return exp_hit
    return RuleHit(value="UNKNOWN", confidence=0.0, source="DEFAULT")


def prefer_rule(rule_hit: RuleHit, model_result: RuleHit | None = None, *, min_confidence: float = 0.7) -> RuleHit:
    if rule_hit.value not in (None, "UNKNOWN", []) and rule_hit.confidence >= min_confidence:
        return rule_hit
    if model_result and model_result.value not in (None, "UNKNOWN", []):
        return model_result
    return rule_hit
