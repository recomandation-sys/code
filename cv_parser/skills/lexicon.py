"""Loads the offline curated IT skill vocabulary (section 28) once per
process and indexes it by normalized alias text for matching.

This is deterministic domain vocabulary checked into the repository
(`resources/skills/it_lexicon.json`), not a trained model — see
`scripts/build_skill_lexicon.py` for how the file is assembled/validated.
"""
from __future__ import annotations

import json
from functools import lru_cache

from pydantic import BaseModel, Field

from cv_parser.config import RESOURCES_DIR
from cv_parser.skills.models import AliasEntry, CanonicalSkill
from cv_parser.skills.normalization import normalize_for_matching

LEXICON_PATH = RESOURCES_DIR / "skills" / "it_lexicon.json"


class Lexicon(BaseModel):
    skills_by_id: dict[str, CanonicalSkill] = Field(default_factory=dict)
    # normalized alias text -> AliasEntry. One normalized string always
    # maps to exactly one skill in a well-curated lexicon; duplicates are
    # rejected at load time (see `_load_raw`) rather than silently
    # shadowed, since a colliding alias is a lexicon authoring bug.
    alias_index: dict[str, AliasEntry] = Field(default_factory=dict)


def _load_raw(path=LEXICON_PATH) -> Lexicon:
    raw = json.loads(path.read_text(encoding="utf-8"))
    skills_by_id: dict[str, CanonicalSkill] = {}
    alias_index: dict[str, AliasEntry] = {}

    for entry in raw:
        skill = CanonicalSkill.model_validate(entry)
        if skill.id in skills_by_id:
            raise ValueError(f"Duplicate skill id in lexicon: {skill.id!r}")
        skills_by_id[skill.id] = skill

        for alias in skill.aliases:
            normalized = normalize_for_matching(alias.text)
            if not normalized:
                continue
            if normalized in alias_index:
                existing = alias_index[normalized]
                raise ValueError(
                    f"Duplicate alias {alias.text!r} (normalized {normalized!r}) "
                    f"maps to both {existing.skill_id!r} and {skill.id!r}"
                )
            alias_index[normalized] = AliasEntry(
                skill_id=skill.id,
                canonical_name=skill.canonical_name,
                category=skill.category,
                alias_text=alias.text,
                normalized_text=normalized,
                policy=alias.policy,
            )

    return Lexicon(skills_by_id=skills_by_id, alias_index=alias_index)


@lru_cache(maxsize=1)
def get_lexicon() -> Lexicon:
    """Cached singleton — the lexicon is parsed once per worker process
    (section 32: "load once per worker"), never rebuilt per CV."""
    return _load_raw()
