"""Lightweight evidence fusion for the production occupation decision layer.

This module is deliberately resolver-agnostic.  It does not create taxonomy
labels; it only normalizes source evidence, keeps raw scores, and applies
transparent promotion/pruning rules to paths that were already produced by
the existing reviewed-title, deterministic, or semantic components.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from job_nlp.paths import REPO_ROOT


CONFIG_PATH = REPO_ROOT / "job_nlp" / "config" / "occupation_decision_v2.json"


@dataclass(frozen=True)
class TitleAnalysis:
    raw_title: str
    segments: tuple[str, ...] = ()
    primary_occupation_text: str = ""
    secondary_occupation_segments: tuple[str, ...] = ()
    specialization_segments: tuple[str, ...] = ()
    domain_context_segments: tuple[str, ...] = ()
    technology_segments: tuple[str, ...] = ()
    seniority_segments: tuple[str, ...] = ()
    location_segments: tuple[str, ...] = ()
    unknown_context_segments: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw_title": self.raw_title,
            "segments": list(self.segments),
            "primary_occupation_text": self.primary_occupation_text,
            "secondary_occupation_segments": list(self.secondary_occupation_segments),
            "specialization_segments": list(self.specialization_segments),
            "domain_context_segments": list(self.domain_context_segments),
            "technology_segments": list(self.technology_segments),
            "seniority_segments": list(self.seniority_segments),
            "location_segments": list(self.location_segments),
            "unknown_context_segments": list(self.unknown_context_segments),
        }


@dataclass
class CandidateEvidence:
    family_id: str
    parent_id: str
    leaf_id: str
    raw_scores: dict[str, float | None] = field(default_factory=dict)
    support: dict[str, bool] = field(default_factory=dict)
    authority_tier: str = "SEMANTIC_ONLY"
    source_names: set[str] = field(default_factory=set)
    evidence: list[str] = field(default_factory=list)
    domain_only_evidence: bool = False
    technology_only_evidence: bool = False
    contradiction: bool = False
    decision_score: float = 0.0
    independent_evidence_count: int = 0
    source_agreement_count: int = 0
    normalized_scores: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "parent_id": self.parent_id,
            "leaf_id": self.leaf_id,
            "decision_score": round(float(self.decision_score), 6),
            "authority_tier": self.authority_tier,
            "raw_scores": {
                key: None if value is None else round(float(value), 6)
                for key, value in self.raw_scores.items()
            },
            "normalized_scores": {
                key: round(float(value), 6)
                for key, value in self.normalized_scores.items()
            },
            "support": dict(self.support),
            "source_agreement_count": self.source_agreement_count,
            "independent_evidence_count": self.independent_evidence_count,
            "domain_only_evidence": self.domain_only_evidence,
            "technology_only_evidence": self.technology_only_evidence,
            "contradiction": self.contradiction,
            "evidence": list(dict.fromkeys(self.evidence)),
        }


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _config(path: tuple[str, ...], default: Any) -> Any:
    value: Any = load_config()
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _clean_segment(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" \t-–—|,;:/+")


def split_title_segments(title: str) -> tuple[str, ...]:
    """Split conservatively while preserving every non-empty segment."""
    text = str(title or "").strip()
    if not text:
        return ()
    pieces = re.split(
        r"\s*(?:\||/|,|;|:|—|–|\s+-\s+|\s+&\s+|\s+\+\s+|\(|\))\s*",
        text,
    )
    result: list[str] = []
    for piece in pieces:
        clean = _clean_segment(piece)
        if clean and clean.casefold() not in {x.casefold() for x in result}:
            result.append(clean)
    return tuple(result) or (text,)


def _contains_token(segment: str, values: Iterable[str]) -> bool:
    lowered = f" {segment.casefold()} "
    return any(
        re.search(r"(?<![a-z0-9])" + re.escape(str(value).casefold()) + r"(?![a-z0-9])", lowered)
        for value in values
    )


def analyze_title(
    title: str,
    *,
    occupation_segments: dict[str, float] | None = None,
    technology_terms: Iterable[str] = (),
) -> TitleAnalysis:
    """Classify title segments without dropping later occupational evidence.

    ``occupation_segments`` is supplied by the existing taxonomy/KB matchers;
    this module never invents an occupation from a product or technology word.
    """
    segments = split_title_segments(title)
    occupation_segments = {
        _clean_segment(key).casefold(): float(value)
        for key, value in (occupation_segments or {}).items()
        if _clean_segment(key)
    }
    tech_terms = tuple(str(value) for value in technology_terms if str(value).strip())
    seniority_terms = _config(("title_context", "seniority"), ())
    location_terms = _config(("title_context", "location_workmode"), ())
    domain_terms = _config(("title_context", "domain_context"), ())

    occupation_hits: list[tuple[str, float]] = []
    specializations: list[str] = []
    domain: list[str] = []
    technologies: list[str] = []
    seniority: list[str] = []
    locations: list[str] = []
    unknown: list[str] = []
    for segment in segments:
        key = segment.casefold()
        score = occupation_segments.get(key)
        if score is not None and score > 0.0:
            occupation_hits.append((segment, score))
            continue
        if _contains_token(segment, tech_terms):
            technologies.append(segment)
        elif _contains_token(segment, seniority_terms):
            seniority.append(segment)
        elif _contains_token(segment, location_terms):
            locations.append(segment)
        elif _contains_token(segment, domain_terms):
            domain.append(segment)
        elif len(segments) > 1 and len(segment.split()) <= 4:
            specializations.append(segment)
        else:
            unknown.append(segment)

    primary = occupation_hits[0][0] if occupation_hits else ""
    secondary = tuple(segment for segment, _score in occupation_hits[1:])
    return TitleAnalysis(
        raw_title=str(title or ""),
        segments=segments,
        primary_occupation_text=primary,
        secondary_occupation_segments=secondary,
        specialization_segments=tuple(specializations),
        domain_context_segments=tuple(domain),
        technology_segments=tuple(technologies),
        seniority_segments=tuple(seniority),
        location_segments=tuple(locations),
        unknown_context_segments=tuple(unknown),
    )


def normalize_source_score(source: str, value: float | None) -> float | None:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    norm = _config(("fusion", "normalization", source), {})
    try:
        center = float(norm.get("center", 0.0))
        scale = max(1e-6, float(norm.get("scale", 1.0)))
    except (AttributeError, TypeError, ValueError):
        center, scale = 0.0, 1.0
    return max(0.0, min(1.0, (value - center) / scale))


def fuse_candidate(candidate: CandidateEvidence) -> CandidateEvidence:
    """Fuse heterogeneous source scores without discarding raw values."""
    weights = _config(("fusion", "weights"), {})
    present: list[tuple[float, float]] = []
    normalized: dict[str, float] = {}
    for source, raw in candidate.raw_scores.items():
        score = normalize_source_score(source, raw)
        weight = weights.get(source)
        if score is None or not isinstance(weight, (int, float)) or float(weight) <= 0.0:
            continue
        normalized[source] = score
        present.append((float(weight), score))
    if present:
        denominator = sum(weight for weight, _score in present)
        score = sum(weight * value for weight, value in present) / denominator
    else:
        score = 0.0
    # Agreement is a count of independent resolver sources, not a count of
    # lexical features.  Title and responsibility support are tracked
    # separately below; treating every feature as a source inflated scores.
    candidate.source_agreement_count = len(
        [name for name, value in candidate.raw_scores.items() if value is not None]
    )
    # Only title and responsibility axes are independent.  Aliases, reviewed
    # authority, semantic retrieval, domain and technology are correlated
    # context/authority signals and must not inflate corroboration.
    candidate.independent_evidence_count = int(bool(candidate.support.get("title"))) + int(
        bool(candidate.support.get("responsibilities"))
    )
    agreement_bonus = float(_config(("fusion", "agreement_bonus"), 0.06) or 0.0)
    evidence_bonus = float(_config(("fusion", "independent_evidence_bonus"), 0.05) or 0.0)
    score += max(0, candidate.source_agreement_count - 1) * agreement_bonus
    score += max(0, candidate.independent_evidence_count - 1) * evidence_bonus
    if candidate.domain_only_evidence:
        score -= float(_config(("promotion", "domain_only_penalty"), 0.20) or 0.20)
    if candidate.technology_only_evidence:
        score -= float(_config(("promotion", "technology_only_penalty"), 0.25) or 0.25)
    candidate.decision_score = max(0.0, min(1.0, score))
    candidate.normalized_scores = normalized
    return candidate


def authority_tier(*, source: str, deterministic_reviewed: bool = False) -> str:
    if deterministic_reviewed:
        return "EXACT_REVIEWED_TITLE"
    source = str(source or "")
    return {
        "deterministic": "SAFE_DETERMINISTIC_RULE",
        "reviewed_title": "REVIEWED_TITLE_VECTOR",
        "title_vector": "REVIEWED_TITLE_VECTOR",
        "semantic": "SEMANTIC_ONLY",
        "responsibility": "RESPONSIBILITY_ONLY",
    }.get(source, "SEMANTIC_ONLY")


def semantic_leaf_can_promote(candidate: CandidateEvidence) -> bool:
    minimum = float(_config(("promotion", "semantic_min_score"), 0.55) or 0.55)
    epsilon = float(_config(("promotion", "promotion_epsilon"), 0.0) or 0.0)
    minimum_evidence = int(_config(("promotion", "semantic_min_independent_evidence"), 2) or 2)
    if candidate.authority_tier == "EXACT_REVIEWED_TITLE":
        return True
    return (
        candidate.decision_score + epsilon >= minimum
        and candidate.independent_evidence_count >= minimum_evidence
        and not candidate.domain_only_evidence
        and not candidate.technology_only_evidence
        and not candidate.contradiction
    )


def relationship_map() -> dict[str, set[str]]:
    pairs = _config(("relationships", "subsumes"), ())
    result: dict[str, set[str]] = {}
    for pair in pairs if isinstance(pairs, list) else ():
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            result.setdefault(str(pair[0]), set()).add(str(pair[1]))
    return result


def prune_redundant_candidates(candidates: list[CandidateEvidence]) -> list[CandidateEvidence]:
    """Drop broader synonyms unless independently supported."""
    by_leaf = {candidate.leaf_id: candidate for candidate in candidates}
    drop: set[str] = set()
    for specific, broad_leaves in relationship_map().items():
        if specific not in by_leaf:
            continue
        specific_candidate = by_leaf[specific]
        for broad in broad_leaves:
            broad_candidate = by_leaf.get(broad)
            if broad_candidate is None:
                continue
            if broad_candidate.independent_evidence_count < specific_candidate.independent_evidence_count:
                drop.add(broad)
    return [candidate for candidate in candidates if candidate.leaf_id not in drop]


def non_it_signal(title: str, description: str = "") -> bool:
    text = f"{title}\n{description}".casefold()
    patterns = _config(("title_context", "non_it_domains"), ())
    return any(
        re.search(r"(?<![a-z0-9])" + re.escape(str(pattern).casefold()) + r"(?![a-z0-9])", text)
        for pattern in patterns if str(pattern).strip()
    )


def responsibility_sections(description: str) -> str:
    """Return role duties/summary text, excluding boilerplate sections."""
    text = re.sub(r"<[^>]+>", " ", str(description or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    headings = list(re.finditer(
        r"\b(?:responsibilities|duties|tasks|missions|what you(?:'|’)ll do|"
        r"what you will do|role summary|the role|your mission|benefits?|"
        r"compensation|about (?:us|the company)|company overview|why join|"
        r"equal opportunity|what we offer)\b",
        text,
        re.I,
    ))
    if headings:
        chunks: list[str] = []
        for index, heading in enumerate(headings[:6]):
            end = headings[index + 1].start() if index + 1 < len(headings) else min(len(text), heading.start() + 1800)
            if re.match(r"\b(?:benefits?|compensation|about|company overview|why join|equal opportunity|what we offer)\b", heading.group(0), re.I):
                continue
            chunks.append(text[heading.start():end])
        return " ".join(dict.fromkeys(chunks))[:4200]
    # Without a heading, only keep text with action verbs; this avoids using
    # generic company/benefits prose as an occupational signal.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    action = re.compile(
        r"\b(?:build|develop|design|implement|maintain|test|monitor|operate|"
        r"manage|analy[sz]e|deliver|deploy|integrate|support|troubleshoot|"
        r"lead|automate|configure|secure|research|publish|model|administer)\b",
        re.I,
    )
    return " ".join(sentence for sentence in sentences if action.search(sentence))[:2400]
