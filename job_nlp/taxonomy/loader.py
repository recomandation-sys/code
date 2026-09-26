"""Taxonomy loader: parent → allowed leaves."""
from __future__ import annotations

import json
import csv
from collections import defaultdict
from functools import lru_cache

from job_nlp.paths import TAXONOMY_JSON, WORKING_CSV


@lru_cache(maxsize=1)
def parent_to_leaves() -> dict[str, tuple[str, ...]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    if TAXONOMY_JSON.exists():
        data = json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))
        for e in data.get("entries", []):
            parent, leaf = e.get("parent"), e.get("leaf")
            if parent and leaf:
                mapping[str(parent)].add(str(leaf))
    if WORKING_CSV.exists():
        with WORKING_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                parent, leaf = row.get("job_family_parent"), row.get("job_family_leaf")
                if parent and leaf and leaf not in ("UNKNOWN", "nan"):
                    mapping[parent].add(leaf)
    return {p: tuple(sorted(leaves)) for p, leaves in sorted(mapping.items())}


def allowed_leaves(parent: str) -> list[str]:
    if not parent or parent in ("UNKNOWN", "NON_IT"):
        return []
    return list(parent_to_leaves().get(parent, ()))


def leaf_to_parent() -> dict[str, str]:
    out: dict[str, str] = {}
    for parent, leaves in parent_to_leaves().items():
        for leaf in leaves:
            out.setdefault(leaf, parent)
    return out


def trainable_leaves() -> set[str]:
    if not WORKING_CSV.exists():
        return set()
    out: set[str] = set()
    with WORKING_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("leaf_trainable_v1", "").upper() == "TRUE" and row.get("job_family_leaf"):
                out.add(row["job_family_leaf"])
    return out
