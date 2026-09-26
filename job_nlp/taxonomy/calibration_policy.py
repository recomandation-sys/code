"""Versioned, fail-safe policy for semantic family/leaf acceptance."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from job_nlp.paths import REPO_ROOT


DEFAULT_POLICY_PATH = REPO_ROOT / "job_nlp" / "config" / "leaf_calibration_policy_v1.json"


@dataclass(frozen=True)
class LeafCalibrationPolicy:
    policy_id: str = "leaf_calibration_policy_v1:defaults"
    family_threshold: float = 0.55
    parent_threshold: float = 0.55
    leaf_threshold: float = 0.55
    title_only_threshold: float = 0.55
    title_description_threshold: float = 0.52
    margin: float = 0.015
    allow_semantic_leaf: bool = False
    target_leaf_precision: float = 0.90
    min_leaf_coverage: float = 0.05
    active_overrides: dict[str, Any] | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> "LeafCalibrationPolicy":
        path = path or DEFAULT_POLICY_PATH
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            defaults = payload.get("defaults", {})
            # Only scalar, known fields are accepted.  A malformed policy must
            # never make the resolver more permissive than its safe defaults.
            values = {
                "policy_id": str(payload.get("policy_id") or "leaf_calibration_policy_v1:defaults"),
                "family_threshold": _bounded(defaults.get("family_threshold"), 0.55),
                "parent_threshold": _bounded(defaults.get("parent_threshold"), 0.55),
                "leaf_threshold": _bounded(defaults.get("leaf_threshold"), 0.55),
                "title_only_threshold": _bounded(defaults.get("title_only_threshold"), 0.55),
                "title_description_threshold": _bounded(defaults.get("title_description_threshold"), 0.52),
                "margin": _bounded(defaults.get("margin"), 0.015),
                "allow_semantic_leaf": bool(defaults.get("allow_semantic_leaf", False)),
                "target_leaf_precision": _bounded(defaults.get("target_leaf_precision"), 0.90),
                "min_leaf_coverage": _bounded(defaults.get("min_leaf_coverage"), 0.05),
                "active_overrides": payload.get("active_overrides") if isinstance(payload.get("active_overrides"), dict) else {},
            }
            # No leaf operating point met the target on the held-out report;
            # an override may not silently enable semantic leaves.
            if values["allow_semantic_leaf"] and not payload.get("evidence", {}).get("leaf_precision_target_met", False):
                values["allow_semantic_leaf"] = False
            return cls(**values)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return cls()

    def threshold(
        self,
        level: str,
        *,
        mode: str = "title_description",
        parent_id: str | None = None,
        leaf_id: str | None = None,
        pair_id: str | None = None,
        method: str | None = None,
    ) -> float:
        """Resolve an optional override, otherwise return a safe default."""
        base = {
            "family": self.family_threshold,
            "parent": self.parent_threshold,
            "leaf": self.leaf_threshold,
        }.get(level, self.leaf_threshold)
        overrides = self.active_overrides or {}
        keys = []
        if pair_id:
            keys.extend((
                f"{mode}:{method}:{level}:pair:{pair_id}" if method else "",
                f"{mode}:{level}:pair:{pair_id}",
            ))
        if method:
            keys.extend((f"{mode}:{method}:{level}:{leaf_id}" if leaf_id else "", f"{mode}:{method}:{level}"))
        keys.extend((f"{mode}:{level}:{leaf_id}" if leaf_id else "", f"{mode}:{level}:{parent_id}" if parent_id else "", f"{mode}:{level}", level))
        for key in (x for x in keys if x):
            value = overrides.get(key)
            if isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0:
                return float(value)
        return base


def _bounded(value: Any, fallback: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return fallback
    return value if 0.0 <= value <= 1.0 else fallback
