"""Evidence aggregation and skill deduplication (sections 37-38).

Collects every raw hit across all scanned sections/records, merges
mentions of the same canonical skill ("ReactJS", "React.js", "React" all
become one `React` entry with all three preserved as `raw_mentions`), and
keeps evidence pointing back to exactly where each mention was found.
"""
from __future__ import annotations

from dataclasses import dataclass

from cv_parser.schemas.parser_response import (
    KnownSkill,
    SkillCategory,
    SkillEvidence,
    SkillEvidenceSourceType,
    UnmappedTechnology,
)


@dataclass
class SkillHit:
    skill_id: str
    canonical_name: str
    category: SkillCategory | None
    raw_text: str
    source_type: SkillEvidenceSourceType
    source_id: str | None
    source_label: str | None = None


@dataclass
class UnmappedHit:
    raw_name: str
    source_type: SkillEvidenceSourceType
    source_id: str | None
    source_label: str | None = None


def _evidence_key(ev: SkillEvidence) -> tuple:
    return (ev.source_type, ev.source_id, (ev.raw_text or "").strip().lower())


def aggregate_known_skills(hits: list[SkillHit]) -> list[KnownSkill]:
    by_skill: dict[str, KnownSkill] = {}
    seen_mentions: dict[str, set[str]] = {}
    seen_evidence: dict[str, set[tuple]] = {}

    for hit in hits:
        skill = by_skill.get(hit.skill_id)
        if skill is None:
            skill = KnownSkill(canonical_name=hit.canonical_name, category=hit.category)
            by_skill[hit.skill_id] = skill
            seen_mentions[hit.skill_id] = set()
            seen_evidence[hit.skill_id] = set()

        raw = hit.raw_text.strip()
        mention_key = raw.lower()
        if mention_key and mention_key not in seen_mentions[hit.skill_id]:
            seen_mentions[hit.skill_id].add(mention_key)
            skill.raw_mentions.append(raw)

        ev = SkillEvidence(
            source_type=hit.source_type,
            source_id=hit.source_id,
            source_label=hit.source_label,
            raw_text=raw,
        )
        ev_key = _evidence_key(ev)
        if ev_key not in seen_evidence[hit.skill_id]:
            seen_evidence[hit.skill_id].add(ev_key)
            skill.evidence.append(ev)

    return list(by_skill.values())


def aggregate_unmapped(hits: list[UnmappedHit]) -> list[UnmappedTechnology]:
    by_name: dict[str, UnmappedTechnology] = {}
    seen_evidence: dict[str, set[tuple]] = {}

    for hit in hits:
        raw = hit.raw_name.strip()
        key = raw.lower()
        if not key:
            continue

        entry = by_name.get(key)
        if entry is None:
            entry = UnmappedTechnology(raw_name=raw, known=False, source_type=hit.source_type)
            by_name[key] = entry
            seen_evidence[key] = set()

        ev = SkillEvidence(
            source_type=hit.source_type,
            source_id=hit.source_id,
            source_label=hit.source_label,
            raw_text=raw,
        )
        ev_key = _evidence_key(ev)
        if ev_key not in seen_evidence[key]:
            seen_evidence[key].add(ev_key)
            entry.evidence.append(ev)

    return list(by_name.values())
