"""Ordinal helpers for the production four-tier education ontology."""
from __future__ import annotations

from collections.abc import Iterable

from .models import EducationLevel


def rank(level: EducationLevel) -> int:
    return level.rank


def min_of(levels: Iterable[EducationLevel]) -> EducationLevel:
    return min(levels, key=rank)


def max_of(levels: Iterable[EducationLevel]) -> EducationLevel:
    return max(levels, key=rank)


def is_higher(a: EducationLevel, b: EducationLevel) -> bool:
    return rank(a) > rank(b)
