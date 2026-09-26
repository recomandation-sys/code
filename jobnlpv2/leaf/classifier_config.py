"""Centralized experimental leaf-classifier parameters.

Defaults preserve the existing 70/15/15 weight allocation as a starting point,
not as gold-set-validated optimal values. OOD thresholds remain disabled until
calibrated. No production scorer imports this module yet.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class LeafClassifierConfig:
    top_k_candidates: int = 5
    top_k_ambiguous: int = 2
    weight_title: float = 0.70
    weight_technology: float = 0.15
    weight_definition: float = 0.075
    weight_main_tasks: float = 0.075
    chunk_size: int = 64
    chunk_overlap: int = 32
    top_n_chunks: int = 3
    task_aggregation_method: str = "top_n_mean"
    definition_aggregation_method: str = "top_n_mean"
    ambiguity_margin: float = 0.02
    ood_score_threshold: float | None = None
    ood_margin_threshold: float | None = None
    min_evidence_score: float | None = None

    def __post_init__(self) -> None:
        if self.top_k_candidates < 2 or self.top_k_ambiguous < 2:
            raise ValueError("top_k_candidates and top_k_ambiguous must be >= 2")
        if self.top_k_ambiguous > self.top_k_candidates:
            raise ValueError("top_k_ambiguous cannot exceed top_k_candidates")
        if self.chunk_size < 8 or not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("invalid chunk size or overlap")
        if self.top_n_chunks < 1:
            raise ValueError("top_n_chunks must be positive")
        for method in (self.task_aggregation_method, self.definition_aggregation_method):
            if method not in {"top_n_mean", "mean", "max"}:
                raise ValueError(f"unsupported aggregation method: {method}")
        weights = (self.weight_title, self.weight_technology, self.weight_definition, self.weight_main_tasks)
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("nonnegative evidence weights must sum to 1")
        for threshold in (self.ambiguity_margin, self.ood_score_threshold, self.ood_margin_threshold, self.min_evidence_score):
            if threshold is not None and not 0 <= threshold <= 1:
                raise ValueError("thresholds must be between zero and one")


CLASSIFIER_CONFIG = LeafClassifierConfig()
