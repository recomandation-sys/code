"""Pure scoring helpers for the experimental leaf classifier.

The caller supplies website-selected duty text and similarity scores; this module
never parses website layouts or hardcodes occupational labels.
"""
from __future__ import annotations

from math import isfinite
from typing import Iterable, Mapping

from classifier_config import CLASSIFIER_CONFIG, LeafClassifierConfig


def _score(value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ValueError("scores must be finite")
    return max(0.0, min(1.0, value))


def aggregate_chunks(values: Iterable[float], method: str, top_n: int) -> float:
    scores = sorted((_score(value) for value in values), reverse=True)
    if not scores:
        return 0.0
    if method == "max":
        return scores[0]
    if method == "mean":
        return sum(scores) / len(scores)
    if method == "top_n_mean":
        top = scores[:top_n]
        return sum(top) / len(top)
    raise ValueError(f"unsupported aggregation method: {method}")


def grounded_technology_scores(technology_ids: Iterable[str], relations: Mapping[str, Mapping], leaves: Iterable[str]) -> dict[str, float]:
    """Deduplicated exact taxonomy edges; shared technology votes are discounted."""
    scores = {leaf: 0.0 for leaf in leaves}
    ids = set(technology_ids)
    if not ids:
        return scores
    for tech_id in ids:
        edge = relations.get(tech_id)
        if not edge:
            continue
        linked = set(edge.get("leaves", ())) & scores.keys()
        if not linked:
            continue
        contribution = 1.0 / len(linked)
        for leaf in linked:
            scores[leaf] += contribution
    scale = max(1.0, max(scores.values(), default=0.0))
    return {leaf: value / scale for leaf, value in scores.items()}


def decide_leaf(channels: Mapping[str, Mapping[str, float]], config: LeafClassifierConfig = CLASSIFIER_CONFIG) -> dict:
    """Return a selected leaf, two ambiguous candidates, or no supported leaf.

    Scores are evidence scores, not calibrated probabilities. OOD gates stay
    disabled until thresholds are fitted on an annotated validation set.
    """
    if not channels:
        return {"status": "NO_LEAF", "leaf": None, "candidates": [], "margin": None}
    ranked = []
    for leaf, parts in channels.items():
        title = _score(parts.get("title", 0.0))
        technology = _score(parts.get("technology", 0.0))
        definition = _score(parts.get("definition", 0.0))
        tasks = _score(parts.get("main_tasks", 0.0))
        total = (config.weight_title * title + config.weight_technology * technology + config.weight_definition * definition + config.weight_main_tasks * tasks)
        ranked.append({"leaf": leaf, "score": total, "title": title, "technology": technology, "definition": definition, "main_tasks": tasks})
    ranked.sort(key=lambda row: (-row["score"], row["leaf"]))
    best = ranked[0]
    margin = best["score"] - ranked[1]["score"] if len(ranked) > 1 else None
    evidence = max(best["technology"], best["definition"], best["main_tasks"])
    low_score = config.ood_score_threshold is not None and best["score"] < config.ood_score_threshold
    low_evidence = config.min_evidence_score is None or evidence < config.min_evidence_score
    weak_margin = config.ood_margin_threshold is None or margin is None or margin < config.ood_margin_threshold
    if low_score and low_evidence and weak_margin:
        status, chosen = "NO_LEAF", None
    elif margin is not None and margin < config.ambiguity_margin:
        status, chosen = "REVIEW_AMBIGUOUS", None
    else:
        status, chosen = "SELECTED", best["leaf"]
    limit = config.top_k_ambiguous if status == "REVIEW_AMBIGUOUS" else config.top_k_candidates
    return {"status": status, "leaf": chosen, "candidates": ranked[:limit], "margin": margin}
