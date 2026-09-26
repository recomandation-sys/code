"""Core matching pipeline for one piece of source text (section 31,
steps: normalization -> Aho-Corasick scan -> boundary validation ->
context disambiguation).

`SAFE`/`SYMBOLIC` aliases are accepted as soon as they are boundary-valid.
`CONTEXT_REQUIRED` aliases additionally need either explicit list-like
context in the surrounding text, or a neighboring already-confirmed
match — evaluated in a second pass so a confirmed `SAFE` mention (e.g.
"Python" in "Python, Go, Java") can vouch for an ambiguous neighbor.
"""
from __future__ import annotations

from cv_parser.skills.automaton import scan
from cv_parser.skills.boundaries import is_valid_boundary
from cv_parser.skills.disambiguation import is_context_sufficient
from cv_parser.skills.models import AliasEntry, RawSkillMatch
from cv_parser.skills.normalization import normalize_for_matching


def _to_match(alias_entry: AliasEntry, start: int, end: int) -> RawSkillMatch:
    return RawSkillMatch(
        skill_id=alias_entry.skill_id,
        canonical_name=alias_entry.canonical_name,
        category=alias_entry.category,
        alias_text=alias_entry.alias_text,
        policy=alias_entry.policy,
        start=start,
        end=end,
    )


def match_text(text: str, *, in_skills_section: bool = False) -> list[RawSkillMatch]:
    """Run the full exact-alias matching pipeline over `text` and return
    every accepted match (offsets refer to `text`, case-insensitively)."""
    if not text:
        return []

    normalized = normalize_for_matching(text)
    raw_hits = scan(normalized)
    boundary_valid = [(s, e, ae) for s, e, ae in raw_hits if is_valid_boundary(normalized, s, e)]

    accepted: list[RawSkillMatch] = []
    confirmed_spans: list[tuple[int, int]] = []
    deferred: list[tuple[int, int, AliasEntry]] = []

    for start, end, alias_entry in boundary_valid:
        if alias_entry.policy == "CONTEXT_REQUIRED":
            deferred.append((start, end, alias_entry))
        else:
            accepted.append(_to_match(alias_entry, start, end))
            confirmed_spans.append((start, end))

    for start, end, alias_entry in deferred:
        if is_context_sufficient(
            normalized,
            start,
            end,
            in_skills_section=in_skills_section,
            other_match_spans=confirmed_spans,
        ):
            accepted.append(_to_match(alias_entry, start, end))

    return accepted
