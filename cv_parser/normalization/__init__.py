"""Formal, language-agnostic normalization helpers (text, dates, occupations,
languages) shared across structure discovery and field extraction."""

from cv_parser.normalization.candidate_profile import (
    normalize_candidate_profile,
    normalize_candidate_profile_dict,
)

__all__ = ["normalize_candidate_profile", "normalize_candidate_profile_dict"]
