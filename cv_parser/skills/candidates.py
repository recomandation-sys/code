"""Structured technology-list handling (sections 35-36).

Only applied to text regions that are *known* to be an explicit
technology list — the whole SKILLS section, or any line elsewhere
tagged with a configured label ("Technologies:", "Stack -", ...). Never
run against narrative prose: "Do not fuzzy-match every word of narrative
prose" (section 35).

For each comma/bullet/pipe/semicolon-separated segment not already
covered by an exact alias match:
1. try a strict RapidFuzz fallback against every canonical name/alias
   (only for segments long enough to be a real technology name);
2. otherwise, if the segment still plausibly names a technology (not a
   soft-skill phrase), preserve it as an unmapped candidate rather than
   silently discarding or force-mapping it (section 34).
"""
from __future__ import annotations

from functools import lru_cache

from rapidfuzz import fuzz

from cv_parser.config import settings
from cv_parser.skills.lexicon import get_lexicon
from cv_parser.skills.models import RawSkillMatch
from cv_parser.skills.normalization import split_tech_list

# A deliberately small, curated deny-list: soft skills and generic
# self-description phrases that commonly sit alongside real technologies
# in a "Skills" section but are not technologies themselves. Filtering
# these out keeps `unmapped_technology_candidates` meaningful instead of
# collecting every non-technical bullet point (still never *invents*
# anything — items here are simply not surfaced as tech at all).
_SOFT_SKILL_DENYLIST = {
    "communication", "leadership", "teamwork", "team spirit", "team player",
    "problem solving", "problem-solving", "time management", "adaptability",
    "creativity", "critical thinking", "work ethic", "collaboration",
    "organization", "organisation", "autonomy", "autonomie", "rigueur",
    "rigor", "esprit d'equipe", "esprit d'équipe", "travail d'equipe",
    "travail d'équipe", "communication ecrite", "communication écrite",
    "gestion du temps", "sens de l'organisation", "curiosity", "curiosite",
    "curiosité", "motivation", "flexibility", "flexibilite", "flexibilité",
    "creative", "proactive", "proactivite", "proactivité", "self-motivated",
}


@lru_cache(maxsize=1)
def _fuzzy_targets() -> list[tuple[str, str, str, object]]:
    """(search_text_lower, skill_id, canonical_name, category) for every
    canonical name and alias in the lexicon — the RapidFuzz candidate
    pool. Built once, alongside the automaton (section 32's "load once
    per worker" applies here too)."""
    lexicon = get_lexicon()
    targets: list[tuple[str, str, str, object]] = []
    seen: set[str] = set()
    for skill in lexicon.skills_by_id.values():
        texts = {skill.canonical_name, *[a.text for a in skill.aliases]}
        for text in texts:
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            targets.append((key, skill.id, skill.canonical_name, skill.category))
    return targets


def _fuzzy_lookup(segment: str) -> tuple[str, str, object] | None:
    if len(segment) < settings.skill_min_fuzzy_term_chars:
        return None
    query = segment.lower()
    best: tuple[str, str, object] | None = None
    best_score = 0.0
    for target_text, skill_id, canonical_name, category in _fuzzy_targets():
        score = fuzz.ratio(query, target_text)
        if score >= settings.skill_fuzzy_cutoff and score > best_score:
            best_score = score
            best = (skill_id, canonical_name, category)
    return best


def _looks_like_soft_skill(segment: str) -> bool:
    return segment.strip().lower().rstrip(".") in _SOFT_SKILL_DENYLIST


def _spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


class RecoveredMatch:
    __slots__ = ("skill_id", "canonical_name", "category", "raw_text")

    def __init__(self, skill_id: str, canonical_name: str, category, raw_text: str):
        self.skill_id = skill_id
        self.canonical_name = canonical_name
        self.category = category
        self.raw_text = raw_text


def resolve_tech_list_candidates(
    text: str, exact_matches: list[RawSkillMatch]
) -> tuple[list[RecoveredMatch], list[str]]:
    """Process one confirmed technology-list text region.

    Returns `(fuzzy_recovered, unmapped_raw_names)`. Segments already
    covered by an exact automaton match are skipped entirely — this only
    fills the gap for spelling/formatting variants exact matching missed.
    """
    fuzzy_recovered: list[RecoveredMatch] = []
    unmapped: list[str] = []

    for segment, start, end in split_tech_list(text):
        if any(_spans_overlap(start, end, m.start, m.end) for m in exact_matches):
            continue

        fuzzy = _fuzzy_lookup(segment)
        if fuzzy is not None:
            skill_id, canonical_name, category = fuzzy
            fuzzy_recovered.append(RecoveredMatch(skill_id, canonical_name, category, segment))
            continue

        if _looks_like_soft_skill(segment):
            continue
        if len(segment) < 2:
            continue

        unmapped.append(segment)

    return fuzzy_recovered, unmapped
