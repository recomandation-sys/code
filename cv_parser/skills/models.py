"""Internal skill-lexicon models (section 29).

These are the *lexicon's* own data structures (loaded once from
`resources/skills/it_lexicon.json`), distinct from the public API models
in `cv_parser.schemas.parser_response` (`KnownSkill`, `UnmappedTechnology`)
that the extractor eventually produces.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cv_parser.schemas.parser_response import SkillCategory

# section 30: at least these three alias safety policies.
AliasPolicy = Literal["SAFE", "CONTEXT_REQUIRED", "SYMBOLIC"]


class SkillAlias(BaseModel):
    text: str
    policy: AliasPolicy = "SAFE"


class ExternalIds(BaseModel):
    esco_uri: str | None = None
    onet_id: str | None = None


class CanonicalSkill(BaseModel):
    id: str
    canonical_name: str
    category: SkillCategory | None = None
    aliases: list[SkillAlias] = Field(default_factory=list)
    external_ids: ExternalIds = Field(default_factory=ExternalIds)


class AliasEntry(BaseModel):
    """One (normalized alias -> skill) mapping, as indexed for matching."""

    skill_id: str
    canonical_name: str
    category: SkillCategory | None
    alias_text: str
    normalized_text: str
    policy: AliasPolicy


class RawSkillMatch(BaseModel):
    """One raw Aho-Corasick hit inside a single piece of source text,
    before context disambiguation / evidence aggregation."""

    skill_id: str
    canonical_name: str
    category: SkillCategory | None
    alias_text: str
    policy: AliasPolicy
    start: int
    end: int
