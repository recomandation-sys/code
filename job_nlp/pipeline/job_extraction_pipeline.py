"""End-to-end job extraction — EN_V1 skills + source-aware structured fields V1."""
from __future__ import annotations

from functools import lru_cache
from threading import RLock
from typing import Any
import re

from job_nlp.pipeline.schemas import (
    CertificationRequirements,
    Location,
    NormalizedJobProfileV1,
    RuleHit,
)
from job_nlp.pipeline.validator import validate
from job_nlp.preprocessing.model_text import to_model_text
from job_nlp.rules import extract_certifications
from job_nlp.schemas.normalized_job_offer import (
    SCHEMA_VERSION,
    JobCertification,
    JobIdentity,
    JobLanguage,
    JobLocation,
    JobQuality,
    JobRequirements,
    JobSkillEntity,
    OccupationPath,
    NormalizedJobOffer,
)
from job_nlp.scripts.filter_english_datasets import classify_language


class LanguageTrust:
    """Process-local token. JSON cannot produce this object.

    Direct ``JobNLPService.extract()`` callers still run the stopword check.
    Only ``preprocess_and_extract`` passes ``LANGUAGE_TRUST`` after fastText
    has already accepted the description. The HTTP schema does not expose it.
    """


LANGUAGE_TRUST = LanguageTrust()


class FamilyDecision:
    """Resolved family path. job_family UNKNOWN is not an IT offer."""

    def __init__(
        self,
        *,
        job_family: str,
        job_parent: str,
        job_leaf: str | None,
        family_tier: int,
        family_method: str,
        family_semantic_score: float | None,
        family_semantic_margin: float | None,
        normalized_title: str,
        occupation_paths: list,
        semantic_decision: dict,
        additional_semantic_decision: dict,
        responsibility_decision: dict,
        title_decision: dict,
        title_analysis: Any,
        leaf_override: dict | None,
        hierarchy_validation: dict,
        occupation_path_metadata: dict,
    ) -> None:
        self.job_family = job_family
        self.job_parent = job_parent
        self.job_leaf = job_leaf
        self.family_tier = family_tier
        self.family_method = family_method
        self.family_semantic_score = family_semantic_score
        self.family_semantic_margin = family_semantic_margin
        self.normalized_title = normalized_title
        self.occupation_paths = occupation_paths
        self.semantic_decision = semantic_decision
        self.additional_semantic_decision = additional_semantic_decision
        self.responsibility_decision = responsibility_decision
        self.title_decision = title_decision
        self.title_analysis = title_analysis
        self.leaf_override = leaf_override
        self.hierarchy_validation = hierarchy_validation
        self.occupation_path_metadata = occupation_path_metadata
        self.warnings: list[str] = []
        self.abstentions: list[str] = []


from job_nlp.skills.en_skill_stack import EnSkillStack
from job_nlp.structured.pipeline import extract_structured_fields
from shared_matching.skill_identity import canonicalize_skill_name, professional_skill_id
from job_nlp.taxonomy.engine import collect_candidates, collect_fuzzy_candidates, resolve_candidates
from job_nlp.taxonomy.semantic_resolver import SemanticFamilyResolver
from job_nlp.taxonomy.title_vector_resolver import ReviewedTitleVectorResolver
from job_nlp.taxonomy.calibration_policy import LeafCalibrationPolicy
from job_nlp.taxonomy.decision_layer_v2 import (
    CandidateEvidence,
    analyze_title,
    authority_tier,
    fuse_candidate,
    non_it_signal,
    prune_redundant_candidates,
    responsibility_sections,
    semantic_leaf_can_promote,
)
from job_nlp.taxonomy.model_identity import public_model_identifier
from job_nlp.taxonomy.title_normalization import normalize_occupation_title

# Deterministic field extractors are part of the job package.  Keep their
# import isolated so stripped deployments can still use the skills / taxonomy
# portions of this service and fall back to the structured extractors.
try:
    from job_nlp.extraction.contract_type_extractor import (
        ContractTypeExtractor,
        enforce_internship_consistency,
        normalize_contract_type,
    )
    from job_nlp.extraction.education import EducationExtractor
    from job_nlp.extraction.language_extractor import extract_languages as extract_languages_src
    from job_nlp.extraction.seniority_experience_extractor import SeniorityExperienceExtractor, months_to_bracket
    from job_nlp.extraction.work_mode_extractor import WorkModeExtractor
except ImportError:  # pragma: no cover - only relevant to stripped deployments
    ContractTypeExtractor = None  # type: ignore[assignment,misc]
    normalize_contract_type = None  # type: ignore[assignment]
    enforce_internship_consistency = None  # type: ignore[assignment]
    EducationExtractor = None  # type: ignore[assignment,misc]
    extract_languages_src = None  # type: ignore[assignment]
    SeniorityExperienceExtractor = None  # type: ignore[assignment,misc]
    months_to_bracket = None  # type: ignore[assignment]
    WorkModeExtractor = None  # type: ignore[assignment,misc]


@lru_cache(maxsize=32)
def _education_extractor_for_country(country: str):
    """Reuse the immutable education rule set across offers in one country."""
    return EducationExtractor(country=country) if EducationExtractor else None

try:
    from job_nlp.knowledge_base.src import ITKnowledgeBase
except ImportError:  # reference database is optional in stripped deployments
    ITKnowledgeBase = None  # type: ignore[assignment,misc]


def _human_evidence_text(value: object) -> str:
    """Convert an evidence value to a safe, human-readable snippet."""
    if value is None or isinstance(value, bool):
        return ""
    text = " ".join(str(value).split()).strip()
    return "" if text.casefold() in {"true", "false", "none", "nan"} else text


def _dedupe_evidence(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Preserve first evidence occurrence and remove repeated source lines."""
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        clean = {
            "text": _human_evidence_text(row.get("text")),
            "source": _human_evidence_text(row.get("source")),
            "section": _human_evidence_text(row.get("section")) or "OTHER",
            "method": _human_evidence_text(row.get("method")) or "RULE",
        }
        if not clean["text"]:
            continue
        key = tuple(clean[field].casefold() for field in ("text", "source", "section", "method"))
        if key in seen:
            continue
        seen.add(key)
        result.append(clean)
    return result


def _compact_decision_warning(prefix: str, decision: dict[str, Any]) -> str:
    """Expose resolver status without duplicating the structured decision blob."""
    status = _human_evidence_text(decision.get("status")) or "unknown"
    reason = _human_evidence_text(decision.get("reason"))
    return f"{prefix}:{status}" + (f":{reason}" if reason else "")


_AUTOMATION_PHRASES = (
    re.compile(r"\btest\s+automation\b", re.I),
    re.compile(r"\bautomated\s+(?:testing|tests?|test\s+cases?)\b", re.I),
    re.compile(r"\bautomation\s+(?:frameworks?|code|development|engineering)\b", re.I),
)
_AUTOMATION_TOOLS = (
    re.compile(r"\bselenium(?:\s+webdriver)?\b", re.I),
    re.compile(r"\bappium\b", re.I),
    re.compile(r"\bplaywright\b", re.I),
    re.compile(r"\bcypress\b", re.I),
    re.compile(r"\brobot\s+framework\b", re.I),
    re.compile(r"\b(?:rest\s+assured|webdriver|uft)\b", re.I),
)


def _automation_evidence_gate(
    title: str,
    description: str,
    skills: list[JobSkillEntity],
    candidate: Any,
    policy: LeafCalibrationPolicy,
    *,
    family: str,
    parent: str,
) -> bool:
    """Accept a narrowly gated automation leaf below the global leaf threshold.

    The global semantic leaf operating point remains conservative because it is
    not calibrated for broad autonomous use.  This exception is evidence-based:
    it requires a known testing parent, the TEST_AUTOMATION candidate, a score
    at least at the title+description operating point, a clear margin, and
    multiple concrete automation signals.  It therefore fixes the observed
    false abstention without lowering the threshold for unrelated leaves.
    """
    if not candidate or getattr(candidate, "leaf_id", "") != "TEST_AUTOMATION":
        return False
    if family != "SOFTWARE" or parent != "SOFTWARE_TESTING":
        return False
    try:
        score = float(getattr(candidate, "score", 0.0))
        margin = float(getattr(candidate, "margin", 0.0))
    except (TypeError, ValueError):
        return False
    minimum_score = max(0.50, min(policy.leaf_threshold, policy.title_description_threshold))
    if score < minimum_score or margin < max(0.03, policy.margin * 2.0):
        return False

    text = f"{title}\n{description}"
    phrase_hits = sum(bool(pattern.search(text)) for pattern in _AUTOMATION_PHRASES)
    # Count concrete technology entities too; this keeps the gate robust when
    # punctuation or a vendor spelling prevents a raw-text regex match.
    technology_names = " ".join(
        str(skill.name) for skill in skills if skill.category == "TECHNOLOGY"
    )
    tool_hits = sum(
        bool(pattern.search(text) or pattern.search(technology_names))
        for pattern in _AUTOMATION_TOOLS
    )
    return phrase_hits >= 1 and (tool_hits >= 2 or phrase_hits >= 3)


def _as_score(value: object) -> float:
    """Return a finite taxonomy score bounded to the public [0, 1] range."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _occupation_path_evidence(
    candidate: dict[str, Any],
    title: str,
    description: str,
    skills: list[JobSkillEntity],
) -> list[str]:
    """Convert resolver signals to compact, human-readable path evidence."""
    evidence: list[str] = []
    if _as_score(candidate.get("lexical_title_overlap")) > 0.0:
        evidence.append("title")
    if _as_score(candidate.get("lexical_detail_overlap")) > 0.0:
        evidence.append("description")
    if candidate.get("matched_title"):
        evidence.append("reviewed_title")
    # Technologies corroborate a branch but never create a branch on their
    # own; selection still requires title/description support below.
    if skills and candidate.get("lexical_detail_overlap", 0.0):
        evidence.append("technologies_or_skills")
    if not evidence and title.strip():
        evidence.append("title")
    return list(dict.fromkeys(evidence))


def _build_occupation_paths(
    *,
    title: str,
    description: str,
    skills: list[JobSkillEntity],
    job_family: str,
    job_parent: str,
    job_leaf: str | None,
    family_method: str,
    family_semantic_score: float | None,
    semantic_decision: dict[str, Any],
    title_decision: dict[str, Any],
    additional_semantic_decision: dict[str, Any] | None = None,
    responsibility_decision: dict[str, Any] | None = None,
    title_analysis: Any | None = None,
    knowledge_base: Any,
    allow_semantic: bool,
    policy: LeafCalibrationPolicy,
) -> tuple[list[OccupationPath], dict[str, Any], list[str]]:
    """Select a small set of coherent taxonomy paths bottom-up from leaves.

    Resolver candidates are evidence only. Every emitted tuple is checked
    against the relational KB, and parent/family proximity is derived from
    supported child leaves rather than independent similarities.
    """
    if knowledge_base is None:
        return [], {"status": "knowledge_base_unavailable"}, []

    hierarchy_rows = knowledge_base.rows(
        "SELECT l.leaf_id, l.parent_id, p.family_id, l.label "
        "FROM leaf l JOIN parent p ON p.parent_id=l.parent_id"
    )
    hierarchy = {
        str(row["leaf_id"]): (str(row["family_id"]), str(row["parent_id"]), str(row["label"] or ""))
        for row in hierarchy_rows
    }
    candidate_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    invalid_candidates = 0

    def add_candidate(
        candidate: dict[str, Any],
        *,
        source: str,
        force: bool = False,
        exact_reviewed: bool = False,
    ) -> None:
        nonlocal invalid_candidates
        family = str(candidate.get("family_id") or "")
        parent = str(candidate.get("parent_id") or "")
        leaf = str(candidate.get("leaf_id") or "")
        if leaf not in hierarchy:
            invalid_candidates += 1
            return
        expected_family, expected_parent, label = hierarchy[leaf]
        # Never trust cross-branch metadata over the relational path.
        if (family and family != expected_family) or (parent and parent != expected_parent):
            invalid_candidates += 1
            return
        score = _as_score(candidate.get("score"))
        if not score and not force:
            return
        row = dict(candidate)
        row.update({"family_id": expected_family, "parent_id": expected_parent, "leaf_id": leaf, "score": score, "label": label})
        row["source"] = source
        row["deterministic"] = force or source == "deterministic"
        row["evidence"] = _occupation_path_evidence(row, title, description, skills)
        source_key = {
            "semantic": "semantic_profile",
            "responsibility": "responsibility",
            "reviewed_title": "reviewed_title",
            "title_vector": "title_vector",
            "deterministic": "deterministic",
        }.get(source, source)
        support = {
            # Semantic retrieval is candidate generation, not title evidence.
            # Only an explicit lexical occupation match (or an exact reviewed
            # mapping) can activate the title axis.
            "title": _as_score(row.get("lexical_title_overlap")) > 0.0
            or exact_reviewed,
            "responsibilities": bool(row.get("responsibility_support"))
            or _as_score(row.get("lexical_detail_overlap")) >= 0.02,
            # Kept for audit compatibility; aliases are authority metadata,
            # never an additional independent evidence axis.
            "alias": bool(row.get("matched_title")) or exact_reviewed,
            "technology": bool(row.get("technology_support")),
            "domain": bool(row.get("domain_support")),
        }
        evidence = CandidateEvidence(
            family_id=expected_family,
            parent_id=expected_parent,
            leaf_id=leaf,
            raw_scores={source_key: score},
            support=support,
            authority_tier=authority_tier(source=source, deterministic_reviewed=exact_reviewed),
            source_names={source},
            evidence=list(row["evidence"]),
            domain_only_evidence=bool(row.get("domain_only_evidence")),
            technology_only_evidence=bool(row.get("technology_only_evidence")),
        )
        row["_evidence"] = evidence
        row["exact_reviewed"] = exact_reviewed
        key = (expected_family, expected_parent, leaf)
        current = candidate_map.get(key)
        if current is None:
            candidate_map[key] = row
        else:
            # Keep every independent signal.  The previous implementation
            # retained only the largest raw score, which silently discarded
            # title/description corroboration and made semantic promotion
            # impossible for otherwise valid leaves.
            existing = current["_evidence"]
            incoming = row["_evidence"]
            for name, value in incoming.raw_scores.items():
                if value is not None:
                    existing.raw_scores[name] = max(
                        float(value), float(existing.raw_scores.get(name) or 0.0)
                    )
            existing.support.update({key: bool(value) or bool(existing.support.get(key)) for key, value in incoming.support.items()})
            existing.source_names.update(incoming.source_names)
            existing.evidence = list(dict.fromkeys(existing.evidence + incoming.evidence))
            existing.authority_tier = (
                "EXACT_REVIEWED_TITLE" if existing.authority_tier == "EXACT_REVIEWED_TITLE" or incoming.authority_tier == "EXACT_REVIEWED_TITLE"
                else existing.authority_tier
            )
            existing.domain_only_evidence = existing.domain_only_evidence and incoming.domain_only_evidence
            existing.technology_only_evidence = existing.technology_only_evidence and incoming.technology_only_evidence
            current["evidence"] = existing.evidence
            current["source"] = "+".join(sorted(existing.source_names))
            current["deterministic"] = bool(current.get("deterministic")) or bool(row.get("deterministic"))
            current["exact_reviewed"] = bool(current.get("exact_reviewed")) or exact_reviewed
            # Retain the richer lexical/context metadata from either source.
            for field in ("lexical_title_overlap", "lexical_detail_overlap", "matched_title", "responsibility_support", "reviewed_candidate_set"):
                if row.get(field) and not current.get(field):
                    current[field] = row[field]

    # Deterministic paths are authoritative and remain first when complete.
    if job_family != "UNKNOWN" and job_parent != "UNKNOWN" and job_leaf:
        add_candidate(
            {
                "family_id": job_family,
                "parent_id": job_parent,
                "leaf_id": job_leaf,
                "score": family_semantic_score if family_semantic_score is not None else 1.0,
                "lexical_title_overlap": 1.0 if family_method in {
                    "reviewed_kb_title", "regex_esco_agree", "regex_only", "esco_deterministic", "title_fuzzy"
                } else 0.0,
            },
            source="deterministic",
            force=True,
            exact_reviewed=family_method == "reviewed_kb_title",
        )

    if allow_semantic:
        for decision in (semantic_decision or {}, additional_semantic_decision or {}):
            for item in decision.get("candidate_paths", []) or []:
                if isinstance(item, dict):
                    add_candidate(item, source="semantic")
        for item in (responsibility_decision or {}).get("candidate_paths", []) or []:
            if isinstance(item, dict):
                add_candidate(item, source="responsibility")
    # Human-reviewed title alternatives are deterministic evidence and remain
    # available even when the calibrated semantic leaf fallback is disabled.
    # Uncalibrated vector candidates still require ``allow_semantic`` above.
    if title_decision.get("deterministic_reviewed"):
        for item in title_decision.get("candidate_paths", []) or []:
            if isinstance(item, dict):
                item = dict(item)
                item_rank = int(item.get("rank") or 1)
                exact_path = title_decision.get("status") == "resolved_title" or (
                    title_decision.get("status") == "resolved_title_with_alternatives" and item_rank == 1
                )
                item["reviewed_candidate_set"] = not exact_path
                add_candidate(
                    item,
                    source="reviewed_title",
                    exact_reviewed=exact_path and not bool(item.get("segment_candidate")),
                )
    elif allow_semantic:
        for item in title_decision.get("candidate_paths", []) or []:
            if isinstance(item, dict):
                item = dict(item)
                item["reviewed_candidate_set"] = bool(title_decision.get("candidate_set")) or bool(item.get("candidate_only"))
                add_candidate(item, source="reviewed_title")

    rejected: list[dict[str, Any]] = []
    # Normalize and fuse only after all sources have been collected.  Raw
    # resolver scores remain in the audit metadata; ``score`` becomes the
    # bounded decision score used for promotion and ranking.
    for row in candidate_map.values():
        evidence = fuse_candidate(row["_evidence"])
        row["score"] = evidence.decision_score
        row["decision_score"] = evidence.decision_score
        row["independent_evidence_count"] = evidence.independent_evidence_count
        row["source_agreement_count"] = evidence.source_agreement_count
        row["authority_tier"] = evidence.authority_tier
        row["evidence_audit"] = evidence.as_dict()
        row["deterministic"] = bool(row.get("deterministic")) or evidence.authority_tier in {
            "EXACT_REVIEWED_TITLE", "SAFE_DETERMINISTIC_RULE"
        }
    retained_evidence = {
        candidate.leaf_id for candidate in prune_redundant_candidates(
            [row["_evidence"] for row in candidate_map.values()]
        )
    }
    for key, row in list(candidate_map.items()):
        if row["leaf_id"] not in retained_evidence:
            rejected.append({
                "family_id": row.get("family_id"),
                "parent_id": row.get("parent_id"),
                "leaf_id": row.get("leaf_id"),
                "score": row.get("score"),
                "reason": "redundant_subsumed_leaf",
            })
            del candidate_map[key]

    if not candidate_map:
        flags = ["PATH_HIERARCHY_INVALID"] if invalid_candidates else []
        return [], {"status": "no_supported_candidates", "invalid_candidates": invalid_candidates, "flags": flags}, flags

    # A secondary branch needs lexical support from title or relevant
    # description. A technology-only neighbour cannot create a new path.
    absolute_threshold = max(
        policy.title_description_threshold if description.strip() else policy.title_only_threshold,
        policy.leaf_threshold,
    )
    supported: list[dict[str, Any]] = []
    out_of_domain = non_it_signal(title, description)
    for candidate in candidate_map.values():
        score = _as_score(candidate.get("score"))
        title_overlap = _as_score(candidate.get("lexical_title_overlap"))
        detail_overlap = _as_score(candidate.get("lexical_detail_overlap"))
        deterministic = bool(candidate.get("deterministic"))
        has_text_support = title_overlap > 0.0 or detail_overlap >= 0.02 or deterministic
        evidence = candidate["_evidence"]
        if out_of_domain and not (
            evidence.support.get("title") or evidence.support.get("responsibilities")
        ) and not deterministic:
            rejected.append({
                "family_id": candidate.get("family_id"),
                "parent_id": candidate.get("parent_id"),
                "leaf_id": candidate.get("leaf_id"),
                "score": score,
                "reason": "OOD_ABSTENTION",
            })
            continue
        # A semantic/vector result is promoted only when independent title and
        # responsibility evidence corroborate it.  Domain/product/technology
        # context remains useful for ranking but can never create a leaf.
        promoted = deterministic or (
            score + 0.01 >= absolute_threshold
            and has_text_support
            and semantic_leaf_can_promote(evidence)
        )
        if promoted:
            candidate["text_supported"] = has_text_support
            supported.append(candidate)
        else:
            rejected.append({
                "family_id": candidate.get("family_id"),
                "parent_id": candidate.get("parent_id"),
                "leaf_id": candidate.get("leaf_id"),
                "score": score,
                "reason": (
                    "semantic_corroboration_required"
                    if not deterministic
                    else "evidence_gate"
                ),
                "authority_tier": candidate.get("authority_tier"),
                "independent_evidence_count": candidate.get("independent_evidence_count", 0),
            })
    if not supported:
        flags = ["PATH_HIERARCHY_INVALID"] if invalid_candidates else []
        return [], {"status": "all_candidates_failed_evidence_gate", "invalid_candidates": invalid_candidates, "flags": flags}, flags

    supported.sort(key=lambda row: (_as_score(row.get("score")), str(row.get("leaf_id"))), reverse=True)
    primary_replaced = False
    semantic_best = max(
        (_as_score(row.get("score")) for row in supported if not row.get("deterministic")),
        default=0.0,
    )
    primary_key = (job_family, job_parent, job_leaf or "")
    primary = candidate_map.get(primary_key)
    if primary is None and supported:
        # For a semantic-only record, the highest fused candidate is the
        # primary occupation; secondary rules are evaluated relative to it.
        primary = supported[0]
        primary_key = (primary.get("family_id"), primary.get("parent_id"), primary.get("leaf_id"))
    # A safe rule remains authoritative unless a non-reviewed semantic path
    # has strong, independent title + responsibility support.  This guard is
    # intentionally narrow; exact reviewed-title mappings are never replaced.
    if primary and primary.get("deterministic") and not primary.get("exact_reviewed"):
        competing = [
            row for row in supported
            if not row.get("deterministic")
            and _as_score(row.get("lexical_title_overlap")) >= 0.30
            and _as_score(row.get("lexical_detail_overlap")) >= 0.10
            and _as_score(row.get("score")) >= 0.88
            and (row.get("family_id"), row.get("parent_id"), row.get("leaf_id")) != primary_key
        ]
        if competing:
            primary["_rejected_by_contradiction"] = True
            primary["_evidence"].contradiction = True
            supported = [row for row in supported if row is not primary]
            primary = max(competing, key=lambda row: _as_score(row.get("score")))
            primary_key = (primary.get("family_id"), primary.get("parent_id"), primary.get("leaf_id"))
            primary_replaced = True
    best_score = _as_score(primary.get("score")) if primary else semantic_best
    # A reviewed/rule title is authoritative, but nearby semantic leaves may
    # still be retained when their own calibrated scores and text evidence
    # support a genuine hybrid role. Compare them with the best semantic leaf,
    # never with the deterministic score marker of 1.0.
    # Unrelated branches need stronger evidence than leaves sharing the same
    # parent. This suppresses common semantic neighbours such as
    # CLOUD_ARCHITECT → SUSTAINABLE_IT while retaining genuinely hybrid
    # cloud/security roles with scores in the high .70s.
    # Secondary occupations use a stricter floor than the primary.  Two
    # transparent exceptions preserve high-value multi-role cases: an
    # explicit automation role with concrete tools, or a reviewed secondary
    # title segment validated by the description.
    secondary_floor = max(absolute_threshold, 0.60)
    close_delta = 0.08
    comparison_anchor = semantic_best if primary and primary.get("deterministic") and semantic_best else best_score
    if primary and primary.get("deterministic") and semantic_best:
        # A deterministic title score is an authority marker, not a semantic
        # probability; use the best semantic leaf as the closeness anchor.
        primary["aggregation_score"] = semantic_best

    selected: list[dict[str, Any]] = []
    for candidate in supported:
        is_primary = primary is not None and (
            candidate.get("family_id"), candidate.get("parent_id"), candidate.get("leaf_id")
        ) == primary_key
        score = _as_score(candidate.get("score"))
        if is_primary:
            selected.append(candidate)
        else:
            explicit_automation = (
                candidate.get("leaf_id") == "TEST_AUTOMATION"
                and bool(re.search(r"\b(?:test automation|automated testing|automation framework)", f"{title}\n{description}", re.I))
                and len(re.findall(r"\b(?:selenium|appium|playwright|cypress|robot framework|rest assured)\b", f"{title}\n{description}", re.I)) >= 2
            )
            validated_segment = bool(candidate.get("segment_candidate")) and _as_score(candidate.get("lexical_detail_overlap")) >= 0.04
            label_tokens = [
                token for token in re.findall(r"[a-z][a-z0-9]+", str(candidate.get("label") or "").casefold())
                if len(token) >= 4 and token not in {"engineer", "developer", "specialist", "analyst", "tester"}
            ]
            role_text = f"{title}\n{responsibility_sections(description)}".casefold()
            role_phrase = r"\s+(?:and|/|&)?\s*".join(re.escape(token) for token in label_tokens)
            direct_role_support = len(label_tokens) >= 2 and bool(
                re.search(r"(?<![a-z0-9])" + role_phrase + r"(?![a-z0-9])", role_text)
            )
            secondary_allowed = (
            # A reviewed candidate set is only a shortlist.  Description
            # existence alone is not evidence for every shortlisted leaf.
            (bool(candidate.get("reviewed_candidate_set")) and detail_overlap >= 0.04)
                or explicit_automation
                or validated_segment
                or (direct_role_support and score + 0.01 >= secondary_floor)
            )
        if not is_primary and secondary_allowed and comparison_anchor - score <= close_delta:
            same_parent = primary is not None and (
                candidate.get("family_id"), candidate.get("parent_id")
            ) == (primary.get("family_id"), primary.get("parent_id"))
            cross_family = primary is not None and candidate.get("family_id") != primary.get("family_id")
            if primary is not None and not same_parent:
                branch_floor = 0.70 if cross_family else 0.65
                title_support = _as_score(candidate.get("lexical_title_overlap")) >= 0.15
                detail_support = _as_score(candidate.get("lexical_detail_overlap")) >= 0.10
                if score < branch_floor or not (title_support or detail_support):
                    continue
            selected.append(candidate)
    if not selected:
        selected = [primary] if primary is not None else [supported[0]]

    def aggregate(rows: list[dict[str, Any]]) -> float:
        scores = sorted((_as_score(row.get("aggregation_score", row.get("score"))) for row in rows), reverse=True)
        return 0.0 if not scores else (scores[0] if len(scores) == 1 else 0.75 * scores[0] + 0.25 * scores[1])

    parent_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    family_groups: dict[str, list[dict[str, Any]]] = {}
    for row in selected:
        parent_groups.setdefault((str(row["family_id"]), str(row["parent_id"])), []).append(row)
        family_groups.setdefault(str(row["family_id"]), []).append(row)
    parent_scores = {key: aggregate(rows) for key, rows in parent_groups.items()}
    family_scores = {key: aggregate(rows) for key, rows in family_groups.items()}
    best_parent = max(parent_scores.values(), default=0.0)
    best_family = max(family_scores.values(), default=0.0)

    final: list[dict[str, Any]] = []
    for row in selected:
        parent_score = parent_scores[(str(row["family_id"]), str(row["parent_id"]))]
        family_score = family_scores[str(row["family_id"])]
        is_primary = primary is not None and (
            row.get("family_id"), row.get("parent_id"), row.get("leaf_id")
        ) == primary_key
        if not is_primary and (best_parent - parent_score > close_delta or best_family - family_score > close_delta):
            continue
        row["parent_aggregate"] = round(parent_score, 6)
        row["family_aggregate"] = round(family_score, 6)
        final.append(row)

    final.sort(
        key=lambda row: (
            0 if primary is not None and (row.get("family_id"), row.get("parent_id"), row.get("leaf_id")) == primary_key else 1,
            -_as_score(row.get("score")),
            str(row.get("family_id")), str(row.get("parent_id")), str(row.get("leaf_id")),
        )
    )
    final = final[:5]
    paths = [
        OccupationPath(
            job_family=str(row["family_id"]),
            job_parent=str(row["parent_id"]),
            job_leaf=str(row["leaf_id"]),
            score=round(_as_score(row.get("score")), 6),
            evidence=list(row.get("evidence") or []),
        )
        for row in final
    ]
    flags: list[str] = []
    families = {path.job_family for path in paths}
    parents = {(path.job_family, path.job_parent) for path in paths}
    if len(paths) > 1 and any(sum(1 for path in paths if (path.job_family, path.job_parent) == parent) > 1 for parent in parents):
        flags.append("MULTI_LEAF")
    if len(parents) > 1:
        flags.append("MULTI_PARENT")
    if len(families) > 1:
        flags.extend(["MULTI_FAMILY", "CROSS_FAMILY_ROLE"])
    if len(paths) > 1 and paths[0].score - paths[1].score <= close_delta:
        flags.append("CLOSE_OCCUPATION_PATHS")
    if any(path.score < absolute_threshold for path in paths[1:]):
        flags.append("WEAK_SECONDARY_PATH")
    # Report disagreement only when both signals point to different paths
    # that survived selection; a discarded neighbour is not a user-visible
    # conflict and should not flood production diagnostics.
    title_supported = [row for row in final if _as_score(row.get("lexical_title_overlap")) >= 0.15]
    detail_supported = [row for row in final if _as_score(row.get("lexical_detail_overlap")) >= 0.05]
    if len(final) > 1 and title_supported and detail_supported:
        title_best = max(title_supported, key=lambda row: _as_score(row.get("lexical_title_overlap")))
        detail_best = max(detail_supported, key=lambda row: _as_score(row.get("lexical_detail_overlap")))
        if (title_best.get("family_id"), title_best.get("parent_id"), title_best.get("leaf_id")) != (
            detail_best.get("family_id"), detail_best.get("parent_id"), detail_best.get("leaf_id")
        ):
            flags.append("TITLE_DESCRIPTION_BRANCH_CONFLICT")
    if invalid_candidates:
        flags.append("PATH_HIERARCHY_INVALID")
    metadata = {
        "status": "accepted" if paths else "abstained",
        "count": len(paths),
        "decision_layer": "occupation_decision_v2_1",
        "decision_score_not_probability": True,
        "absolute_threshold": absolute_threshold,
        "secondary_delta": close_delta,
        "parent_scores": {f"{family}:{parent}": score for (family, parent), score in parent_scores.items()},
        "family_scores": family_scores,
        "invalid_candidates": invalid_candidates,
        "candidate_evidence": [row.get("evidence_audit") for row in candidate_map.values()],
        "rejected_candidates": rejected,
        "title_analysis": title_analysis.as_dict() if hasattr(title_analysis, "as_dict") else title_analysis,
        "ood_gate": {"non_it_signal": out_of_domain, "status": "ABSTAIN" if out_of_domain and not paths else "PASS"},
        "flags": flags,
        "primary_replaced": primary_replaced,
    }
    return paths, metadata, flags


class JobNLPService:
    """Load once; call extract() many times. Default output: NormalizedJobOffer."""

    def __init__(
        self,
        *,
        load_baselines: bool = False,
        load_en_skills: bool = True,
        load_knowledge_base: bool = True,
        load_semantic: bool = True,
        preload_semantic: bool = True,
        load_tfidf: bool = True,
        device: str = "cpu",
        leaf_mode: str = "production",
    ) -> None:
        # load_baselines default False: structured V1 uses ESCO occupation, not trained family models
        self.pipeline_version = "EN_V1"
        self.schema_version = SCHEMA_VERSION
        self.device = device
        self.startup_warnings: list[str] = []
        self.tfidf_parent = None
        self.xlmr_parent = None
        self.seniority_model = None
        self._semantic_lock = RLock()
        self.leaf_policy = LeafCalibrationPolicy.load()
        if leaf_mode not in {"production", "best_effort"}:
            raise ValueError("leaf_mode must be 'production' or 'best_effort'")
        # ``production`` obeys the held-out calibration policy.  The explicit
        # opt-in mode is useful for recall-oriented experiments and keeps the
        # trade-off visible instead of silently weakening the deployment gate.
        self.leaf_mode = leaf_mode
        self.semantic_leaf_allowed = self.leaf_policy.allow_semantic_leaf or leaf_mode == "best_effort"
        self.contract_extractor = ContractTypeExtractor() if ContractTypeExtractor else None
        self.seniority_experience_extractor = SeniorityExperienceExtractor() if SeniorityExperienceExtractor else None
        # Production output must not infer ONSITE from missing evidence. The
        # standalone CLI retains its legacy default for backward compatibility.
        self.work_mode_extractor = WorkModeExtractor(default_mode=None) if WorkModeExtractor else None
        self.en_skills: EnSkillStack | None = EnSkillStack(device=device) if load_en_skills else None
        if self.en_skills is not None:
            # Pay model initialization once at process startup, not on the
            # first web request.  This makes request latency predictable.
            self.en_skills.load()
        self.knowledge_base = None
        if load_knowledge_base and ITKnowledgeBase:
            try:
                self.knowledge_base = ITKnowledgeBase()
            except Exception as exc:  # noqa: BLE001
                # Keep the API alive so /health can report a degraded worker
                # and structured fields can still be served.  Do not expose
                # filesystem/database details in the public response.
                self.startup_warnings.append(f"knowledge_base_load_failed:{type(exc).__name__}")
        self.knowledge_base_version = "UNKNOWN"
        if self.knowledge_base is not None:
            try:
                version_rows = self.knowledge_base.rows("SELECT value FROM metadata WHERE key='taxonomy_version'")
                if version_rows:
                    self.knowledge_base_version = str(version_rows[0]["value"])
            except Exception:
                pass
        self.semantic_resolver = SemanticFamilyResolver(policy=self.leaf_policy) if load_semantic and self.knowledge_base is not None else None
        if self.semantic_resolver is not None and preload_semantic:
            # Load once per service instance (application startup), never per
            # request. A missing/offline model is non-fatal; deterministic
            # tiers remain available and the warning is exposed on output.
            self.semantic_resolver.load()
        self.title_vector_resolver = (
            ReviewedTitleVectorResolver(model=self.semantic_resolver._model if self.semantic_resolver else None)
            if load_semantic and self.knowledge_base is not None else None
        )
        if self.title_vector_resolver is not None and preload_semantic:
            self.title_vector_resolver.load()
        # Expose immutable startup invariants so production health checks can
        # distinguish a valid model/cache from a silently stale taxonomy.
        self.startup_metadata: dict[str, Any] = {
            "decision_layer": "occupation_decision_v2_1",
            "knowledge_base_version": self.knowledge_base_version,
            "semantic_model": public_model_identifier(
                getattr(self.semantic_resolver, "model_name", "local-e5")
            ) if self.semantic_resolver is not None else None,
            "semantic_leaf_policy": {
                "allow_semantic_leaf": self.semantic_leaf_allowed,
                "leaf_mode": self.leaf_mode,
                "policy_id": self.leaf_policy.policy_id,
                "family_threshold": self.leaf_policy.family_threshold,
                "parent_threshold": self.leaf_policy.parent_threshold,
                "leaf_threshold": self.leaf_policy.leaf_threshold,
                "title_only_threshold": self.leaf_policy.title_only_threshold,
                "title_description_threshold": self.leaf_policy.title_description_threshold,
                "margin": self.leaf_policy.margin,
            },
        }
        if self.knowledge_base is not None:
            try:
                counts = {
                    name: int(self.knowledge_base.rows(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"])
                    for name, table in (("families", "family"), ("parents", "parent"), ("leaves", "leaf"))
                }
                self.startup_metadata["taxonomy_counts"] = counts
                expected = {"families": 8, "parents": 24, "leaves": 118}
                mismatches = [f"{key}:{counts[key]}!=expected:{value}" for key, value in expected.items() if counts.get(key) != value]
                if mismatches:
                    self.startup_warnings.append("severe:taxonomy_index_mismatch:" + ",".join(mismatches))
                    self.startup_metadata["status"] = "DEGRADED"
                else:
                    self.startup_metadata["status"] = "READY"
            except Exception as exc:  # noqa: BLE001
                self.startup_metadata["status"] = "DEGRADED"
                self.startup_warnings.append(f"taxonomy_invariant_check_failed:{type(exc).__name__}")
        else:
            self.startup_metadata["status"] = "DEGRADED"
            self.startup_warnings.append("severe:knowledge_base_unavailable")
        if self.title_vector_resolver is not None:
            self.startup_metadata["reviewed_title_index"] = {
                "source": self.title_vector_resolver.title_csv.name,
                "uses_candidate_sets": self.title_vector_resolver.uses_candidate_sets,
                "rows": len(getattr(self.title_vector_resolver, "_rows", []) or []),
                "vectors": int(getattr(getattr(self.title_vector_resolver, "_vectors", None), "shape", [0])[0])
                if getattr(self.title_vector_resolver, "_vectors", None) is not None and getattr(self.title_vector_resolver, "_vectors", None) is not False else 0,
            }
        if load_tfidf or load_baselines:
            try:
                from job_nlp.models.job_family_parent.train_tfidf_svm import ParentFamilyBaseline

                baseline = ParentFamilyBaseline()
                if baseline.model is not None:
                    self.tfidf_parent = baseline
            except Exception:
                pass
        if load_baselines:
            try:
                from job_nlp.models.job_family_parent.train_xlmr import ParentFamilyXLMR

                xlmr = ParentFamilyXLMR()
                if xlmr.model is not None:
                    self.xlmr_parent = xlmr
            except Exception:
                pass
            try:
                from job_nlp.models.seniority.train_tfidf import SeniorityTfidf
                from job_nlp.paths import SENIORITY_REGISTRY_PATH
                import json
                from pathlib import Path

                art = None
                if SENIORITY_REGISTRY_PATH.exists():
                    art = Path(json.loads(SENIORITY_REGISTRY_PATH.read_text(encoding="utf-8"))["champion"]["artifact"])
                model = SeniorityTfidf(art)
                if model.model is not None:
                    self.seniority_model = model
            except Exception:
                pass

    def _nesta_skill_text(self, skill_entities: list, description: str) -> str:
        """Cleaned NESTA surfaces. Extract them here when the caller has none yet."""
        names: list[str] = []
        for skill in skill_entities or []:
            sources = list(getattr(skill, "sources", None) or [])
            if sources and "NESTA" not in sources:
                continue
            name = getattr(skill, "name", "") or getattr(skill, "surface", "")
            if name:
                names.append(str(name))
        if not names and description.strip() and self.en_skills is not None:
            try:
                raw = self.en_skills.extract(description)
            except Exception:  # noqa: BLE001
                raw = []
            for entity in raw:
                sources = list(entity.get("sources") or [])
                if sources and "NESTA" not in sources:
                    continue
                surface = entity.get("surface") or entity.get("canonical") or ""
                if surface:
                    names.append(str(surface))
        return "; ".join(dict.fromkeys(names))

    def resolve_job_family(self, title: str, description: str) -> "FamilyDecision":
        """Family id only. Parent and leaf are filled later by extract().

        Uses the reviewed-title, regex, ESCO, TF-IDF, and
        job-title-normalizer-e5-base tiers. UNKNOWN means no known family.
        """
        title_model, description_model = to_model_text(title, description)
        warnings: list[str] = []
        abstentions: list[str] = []

        class _NoOccupation:
            occupation_method = ""
            occupation_family = None
            occupation_uri = None

        return self._resolve_family(
            title,
            description,
            title_model,
            description_model,
            [],
            _NoOccupation(),
            warnings,
            abstentions,
            family_only=True,
        )

    def _resolve_family(
        self,
        title: str,
        description: str,
        title_model: str,
        description_model: str,
        skill_entities: list,
        structured: Any,
        warnings: list[str],
        abstentions: list[str],
        family_only: bool = False,
    ) -> "FamilyDecision":
        warn_from = len(warnings)
        abstain_from = len(abstentions)
        job_family = "UNKNOWN"
        job_parent = "UNKNOWN"
        job_leaf = None
        family_tier = 5
        family_method = "abstain"
        family_conflict = False
        family_abstention = "no reviewed KB title, retargeted regex, or deterministic KB occupation path"
        family_semantic_score: float | None = None
        family_semantic_margin: float | None = None
        semantic_decision: dict[str, Any] = {}
        additional_semantic_decision: dict[str, Any] = {}
        responsibility_decision: dict[str, Any] = {}
        title_analysis: Any = None
        title_decision: dict[str, Any] = {}
        semantic_leaf_match: Any = None
        title_leaf_match: Any = None
        leaf_override: dict[str, Any] | None = None
        hierarchy_validation: dict[str, Any] = {"status": "not_run"}
        occupation_paths: list[OccupationPath] = []
        occupation_path_metadata: dict[str, Any] = {"status": "not_run"}
        occupation_path_flags: list[str] = []
        # Keep the raw title for evidence, but expose the same conservative
        # metadata-stripped form used by semantic retrieval for matching.
        normalized_title = normalize_occupation_title(title_model) or title_model
        deterministic_complete = False
        if self.knowledge_base is not None:
            title_match = self.knowledge_base.normalize_title(title)
            if title_match["status"] in {"resolved_title", "resolved_title_with_alternatives"}:
                normalized_title = title_match["normalized_title"]
                job_family = title_match["family_id"]
                job_parent = title_match["parent_id"]
                job_leaf = title_match["leaf_id"]
                family_tier = 1
                family_method = "reviewed_kb_title"
                family_abstention = ""
                title_decision = {
                    "status": title_match["status"],
                    "candidate_paths": title_match.get("candidate_paths", []),
                    "deterministic_reviewed": True,
                    "model_name": "reviewed-kb-title",
                }
                warnings.append("family_confidence_tier:1")
            else:
                candidate_title_set = title_match["status"] in {
                    "candidate_title_requires_description",
                    "candidate_title_parent_only",
                }
                if candidate_title_set:
                    normalized_title = title_match.get("normalized_title") or normalized_title
                    job_family = str(title_match.get("family_id") or "UNKNOWN")
                    job_parent = str(title_match.get("parent_id") or "UNKNOWN")
                    job_leaf = None
                    family_tier = 2
                    family_method = "reviewed_title_candidate_set"
                    family_abstention = "reviewed title candidate set requires description validation"
                    title_decision = {
                        "status": title_match["status"],
                        "candidate_paths": title_match.get("candidate_paths", []),
                        "candidate_set": True,
                        "deterministic_reviewed": False,
                        "model_name": "reviewed-kb-title-candidate-set",
                    }
                    warnings.append("reviewed_title_candidate_set_requires_description")
                else:
                    regex_candidates = collect_candidates(title)
                    regex_parent, regex_leaf, regex_best = resolve_candidates(regex_candidates)
                    regex_family = regex_best.kb_family_id if regex_best else "UNKNOWN"
                    if regex_best is None:
                        fuzzy_candidates = collect_fuzzy_candidates(title)
                        fuzzy_parent, fuzzy_leaf, fuzzy_best = resolve_candidates(fuzzy_candidates, min_priority=90)
                        if fuzzy_best is not None:
                            regex_family, regex_parent, regex_leaf, regex_best = (
                                fuzzy_best.kb_family_id or "UNKNOWN",
                                fuzzy_parent,
                                fuzzy_leaf,
                                fuzzy_best,
                            )
                            family_method = "title_fuzzy"
                            warnings.append(f"family_fuzzy_match:{fuzzy_best.matched_text}")
                    source_paths = title_match.get("source_candidates") or []
                    esco_paths = {(p.get("family_id"), p.get("parent_id"), p.get("leaf_id")) for p in source_paths if p.get("family_id") and p.get("parent_id")}
                    if regex_best and regex_leaf != "UNKNOWN":
                        if esco_paths and any((regex_best.kb_family_id, regex_best.kb_parent_id, regex_leaf) == path for path in esco_paths):
                            job_family, job_parent, job_leaf = regex_family, regex_parent, regex_leaf
                            family_tier, family_method, family_abstention = 2, "regex_esco_agree", ""
                        elif not esco_paths:
                            job_family, job_parent, job_leaf = regex_family, regex_parent, regex_leaf
                            family_tier, family_method, family_abstention = 3, "regex_only", "ESCO/KB occupation path unavailable"
                        else:
                            family_conflict = True
                            warnings.append("family_conflict:regex_vs_esco")
                            # A cross-source disagreement never silently emits a leaf.
                            job_family, job_parent, job_leaf = next(iter(esco_paths))
                            family_tier, family_method, family_abstention = 4, "esco_context_only", "regex and ESCO/KB paths disagree"
                    elif len(esco_paths) == 1:
                        job_family, job_parent, job_leaf = next(iter(esco_paths))
                        family_tier, family_method, family_abstention = 3, "esco_deterministic", ""
                    elif structured.occupation_method == "TITLE_ALIAS" and structured.occupation_family:
                        family_tier, family_method = 3, "esco_deterministic"
                        family_abstention = "ESCO alias has no KB family path"
                    elif self.tfidf_parent is not None:
                        parent_hit = self.tfidf_parent.predict(title_model, description_model)
                        if parent_hit is not None and parent_hit.confidence >= 0.65:
                            parent_id = str(parent_hit.value)
                            parent_rows = self.knowledge_base.rows(
                                "SELECT family_id FROM parent WHERE parent_id=?", (parent_id,)
                            )
                            if len(parent_rows) == 1:
                                job_family, job_parent, job_leaf = parent_rows[0]["family_id"], parent_id, None
                                family_tier, family_method, family_abstention = 1, "tfidf_parent_fallback", "semantic leaf not attempted after parent fallback"
                                warnings.append(f"tfidf_parent_confidence:{parent_hit.confidence:.4f}")
                # Easy titles stop here. The title model runs only when this
                # pass has no family, parent, and leaf.
                deterministic_complete = (
                    job_family not in ("", "UNKNOWN")
                    and job_parent not in ("", "UNKNOWN")
                    and bool(job_leaf)
                )
                if not deterministic_complete and self.title_vector_resolver is not None:
                    skill_text = self._nesta_skill_text(skill_entities, description)
                    title_hit = None
                    if skill_text:
                        with self._semantic_lock:
                            title_hit = self.title_vector_resolver.resolve_from_skills(skill_text)
                            title_warning = self.title_vector_resolver.warning
                            title_decision = dict(self.title_vector_resolver.last_decision)
                            if title_decision.get("model_name"):
                                title_decision["model_name"] = public_model_identifier(
                                    title_decision["model_name"]
                                )
                        if title_warning:
                            warnings.append(title_warning)
                    if title_hit is not None:
                        title_leaf_match = title_hit
                        job_family = title_hit.family_id
                        job_parent = title_hit.parent_id
                        job_leaf = title_hit.leaf_id
                        family_tier, family_method, family_abstention = 2, "reviewed_title_skill_chunks", ""
                        family_semantic_score, family_semantic_margin = title_hit.score, title_hit.margin
                        warnings.extend([
                            f"title_skill_score:{title_hit.score:.4f}",
                            f"title_skill_margin:{title_hit.margin:.4f}",
                            f"title_skill_match:{title_hit.title_id}:{title_hit.matched_title}",
                        ])
                    if title_decision:
                        warnings.append(_compact_decision_warning("title_vector_decision", title_decision))
                # A calibrated global leaf gate must not erase a highly
                # specific, evidence-backed testing decision.  This narrow
                # override is evaluated only after both semantic candidates
                # have run and still enforces the relational hierarchy.
                override_candidate = None if family_only else next(
                    (
                        candidate
                        for candidate in (semantic_leaf_match, title_leaf_match)
                        if _automation_evidence_gate(
                            title,
                            description,
                            skill_entities,
                            candidate,
                            self.leaf_policy,
                            family=job_family,
                            parent=job_parent,
                        )
                    ),
                    None,
                )
                if override_candidate is not None:
                    job_family = str(override_candidate.family_id)
                    job_parent = str(override_candidate.parent_id)
                    job_leaf = str(override_candidate.leaf_id)
                    family_tier = 2
                    family_method = "automation_evidence_leaf_override"
                    family_abstention = ""
                    family_semantic_score = float(override_candidate.score)
                    family_semantic_margin = float(override_candidate.margin)
                    leaf_override = {
                        "leaf_id": job_leaf,
                        "reason": "automation_phrase_and_tool_evidence",
                        "score": family_semantic_score,
                        "margin": family_semantic_margin,
                    }
                    if semantic_decision:
                        semantic_decision["initial_status"] = semantic_decision.get("status")
                        semantic_decision["status"] = "accepted_by_evidence_gate"
                        semantic_decision["reason"] = "automation_phrase_and_tool_evidence"
                        warnings[:] = [
                            warning
                            for warning in warnings
                            if not warning.startswith("semantic_decision:")
                        ]
                        warnings.append(
                            _compact_decision_warning("semantic_decision", semantic_decision)
                        )
                    warnings.append("semantic_leaf_accepted_by_automation_evidence")
                # UNKNOWN is terminal only after every enabled tier has run.
                # Never expose a deterministic method when it did not resolve
                # a family path.
                if job_family == "UNKNOWN":
                    family_tier = 5
                    family_method = "abstain"
                    family_abstention = "all deterministic, fuzzy, TF-IDF, and semantic tiers abstained"
                # Validate every emitted prefix against the relational KB.  A
                # semantic score can never manufacture a leaf→parent→family
                # path, and an invalid path is safer as UNKNOWN than as a
                # plausible-looking taxonomy label.
                if job_leaf:
                    rows = self.knowledge_base.rows(
                        "SELECT l.leaf_id, l.parent_id, p.family_id FROM leaf l JOIN parent p ON p.parent_id=l.parent_id WHERE l.leaf_id=?",
                        (job_leaf,),
                    )
                    hierarchy_validation = {"status": "valid" if any(r["parent_id"] == job_parent and r["family_id"] == job_family for r in rows) else "invalid_leaf_path"}
                    if hierarchy_validation["status"] != "valid":
                        warnings.append("family_path_invalid:leaf")
                        job_leaf = None
                if job_parent and job_parent != "UNKNOWN":
                    rows = self.knowledge_base.rows("SELECT family_id FROM parent WHERE parent_id=?", (job_parent,))
                    if not any(r["family_id"] == job_family for r in rows):
                        hierarchy_validation = {"status": "invalid_parent_path"}
                        warnings.append("family_path_invalid:parent")
                        job_parent, job_leaf = "UNKNOWN", None
                if job_family and job_family != "UNKNOWN":
                    rows = self.knowledge_base.rows("SELECT family_id FROM family WHERE family_id=?", (job_family,))
                    if not rows:
                        hierarchy_validation = {"status": "invalid_family"}
                        warnings.append("family_path_invalid:family")
                        job_family, job_parent, job_leaf = "UNKNOWN", "UNKNOWN", None
                warnings.append(f"family_confidence_tier:{family_tier}")
            warnings.append(f"family_resolver_method:{family_method}")
            if family_conflict:
                warnings.append("family_conflict_flag:true")
            if family_abstention:
                warnings.append(f"family_abstention_reason:{family_abstention}")
        else:
            warnings.append("family_abstention_reason:knowledge_base_unavailable")
        if family_only:
            if self.knowledge_base is not None and job_family not in ("", "UNKNOWN"):
                rows = self.knowledge_base.rows(
                    "SELECT family_id FROM family WHERE family_id=?", (job_family,)
                )
                if not rows:
                    warnings.append("family_path_invalid:family")
                    job_family = "UNKNOWN"
                    family_tier = 5
                    family_method = "abstain"
                    family_abstention = "family id is not in the knowledge base"
            if not structured.occupation_uri:
                abstentions.append("esco_occupation")
            decision = FamilyDecision(
                job_family=str(job_family or "UNKNOWN"),
                job_parent="UNKNOWN",
                job_leaf=None,
                family_tier=family_tier,
                family_method=family_method,
                family_semantic_score=family_semantic_score,
                family_semantic_margin=family_semantic_margin,
                normalized_title=normalized_title,
                occupation_paths=[],
                semantic_decision=semantic_decision,
                additional_semantic_decision={},
                responsibility_decision={},
                title_decision=title_decision,
                title_analysis=None,
                leaf_override=None,
                hierarchy_validation={"status": "family_only"},
                occupation_path_metadata={"status": "not_run"},
            )
            decision.warnings = list(warnings[warn_from:])
            decision.abstentions = list(abstentions[abstain_from:])
            return decision
        occupation_segments: dict[str, float] = {}
        if normalized_title:
            occupation_segments[normalized_title] = 1.0
        for item in title_decision.get("candidate_paths", []) or []:
            if isinstance(item, dict):
                matched = item.get("matched_title") or item.get("title")
                if matched:
                    occupation_segments[str(matched)] = max(
                        float(item.get("score") or 0.0),
                        occupation_segments.get(str(matched), 0.0),
                    )
        title_analysis = analyze_title(
            title,
            occupation_segments=occupation_segments,
            technology_terms=[skill.name for skill in skill_entities if skill.category == "TECHNOLOGY"],
        )
        # Resolve each non-context title segment independently.  A slash or
        # pipe often separates two real occupations (for example
        # ``Backend Engineer / Data Analyst``); silently keeping only the
        # first segment loses the secondary role.  Segment matches are
        # candidate-only until the description supplies a second evidence
        # axis.
        if self.knowledge_base is not None and len(title_analysis.segments) > 1:
            segment_paths: list[dict[str, Any]] = []
            for segment in title_analysis.segments:
                if segment.casefold() == title.strip().casefold():
                    continue
                if segment in (
                    title_analysis.domain_context_segments
                    + title_analysis.technology_segments
                    + title_analysis.seniority_segments
                    + title_analysis.location_segments
                ):
                    # A product/domain/location segment (e.g. ``Client
                    # Platform``) is context, not an occupation.
                    continue
                segment_match = self.knowledge_base.normalize_title(segment)
                if segment_match.get("status") not in {"resolved_title", "resolved_title_with_alternatives"}:
                    continue
                for path in segment_match.get("candidate_paths", []) or []:
                    if not isinstance(path, dict) or not path.get("leaf_id"):
                        continue
                    candidate = dict(path)
                    candidate.update({
                        "segment_candidate": True,
                        "segment": segment,
                        "matched_title": segment,
                        "score": max(0.75, float(candidate.get("score") or 0.0)),
                        "lexical_title_overlap": 1.0,
                        "lexical_detail_overlap": 0.0,
                        "requires_description_validation": True,
                    })
                    segment_paths.append(candidate)
                    occupation_segments[segment] = max(
                        occupation_segments.get(segment, 0.0),
                        float(candidate.get("score") or 0.0),
                    )
            if segment_paths:
                title_decision.setdefault("candidate_paths", []).extend(segment_paths)
                title_decision["segment_candidates"] = True
                title_analysis = analyze_title(
                    title,
                    occupation_segments=occupation_segments,
                    technology_terms=[skill.name for skill in skill_entities if skill.category == "TECHNOLOGY"],
                )
        # Resolved KB titles take the fast path above and do not enter the
        # fallback branch where validation normally runs. Validate that path
        # as well so every emitted hierarchy has an auditable status.
        if (
            self.knowledge_base is not None
            and hierarchy_validation["status"] == "not_run"
            and job_family != "UNKNOWN"
        ):
            if job_leaf:
                rows = self.knowledge_base.rows(
                    "SELECT l.leaf_id, l.parent_id, p.family_id FROM leaf l JOIN parent p ON p.parent_id=l.parent_id WHERE l.leaf_id=?",
                    (job_leaf,),
                )
                if any(r["parent_id"] == job_parent and r["family_id"] == job_family for r in rows):
                    hierarchy_validation = {"status": "valid"}
                else:
                    hierarchy_validation = {"status": "invalid_leaf_path"}
                    warnings.append("family_path_invalid:leaf")
                    job_leaf = None
            elif job_parent != "UNKNOWN":
                rows = self.knowledge_base.rows(
                    "SELECT family_id FROM parent WHERE parent_id=?", (job_parent,)
                )
                if any(r["family_id"] == job_family for r in rows):
                    hierarchy_validation = {"status": "valid_prefix"}
                else:
                    hierarchy_validation = {"status": "invalid_parent_path"}
                    warnings.append("family_path_invalid:parent")
                    job_parent, job_leaf = "UNKNOWN", None
            else:
                rows = self.knowledge_base.rows(
                    "SELECT family_id FROM family WHERE family_id=?", (job_family,)
                )
                if rows:
                    hierarchy_validation = {"status": "valid_prefix"}
                else:
                    hierarchy_validation = {"status": "invalid_family"}
                    warnings.append("family_path_invalid:family")
                    job_family, job_parent, job_leaf = "UNKNOWN", "UNKNOWN", None
        # Build the optional multi-path view only after all legacy resolver
        # tiers have run. This keeps the existing single-path fields stable
        # while exposing additional, close and evidence-backed branches.
        occupation_paths, occupation_path_metadata, occupation_path_flags = _build_occupation_paths(
            title=title,
            description=description,
            skills=skill_entities,
            job_family=str(job_family or "UNKNOWN"),
            job_parent=str(job_parent or "UNKNOWN"),
            job_leaf=job_leaf,
            family_method=family_method,
            family_semantic_score=family_semantic_score,
            semantic_decision=semantic_decision,
            additional_semantic_decision=additional_semantic_decision,
            responsibility_decision=responsibility_decision,
            title_analysis=title_analysis,
            title_decision=title_decision,
            knowledge_base=self.knowledge_base,
            # Semantic resolvers are candidate generators.  Promotion remains
            # gated inside the decision layer by independent evidence and
            # calibrated thresholds, so this does not enable raw semantic
            # leaves globally in production.
            allow_semantic=bool(self.semantic_resolver or self.title_vector_resolver),
            policy=self.leaf_policy,
        )
        # If a permitted semantic path is the only resolved output, project
        # its best valid path back into the legacy identity fields too.
        if occupation_paths and (
            job_family == "UNKNOWN"
            or job_parent == "UNKNOWN"
            or not job_leaf
            or occupation_path_metadata.get("primary_replaced")
        ):
            best_path = occupation_paths[0]
            job_family, job_parent, job_leaf = best_path.job_family, best_path.job_parent, best_path.job_leaf
            family_semantic_score = best_path.score
            family_semantic_margin = (
                best_path.score - occupation_paths[1].score if len(occupation_paths) > 1 else None
            )
            if family_method == "abstain" or occupation_path_metadata.get("primary_replaced"):
                family_method = "occupation_path_aggregation"
                family_tier = 2
                family_abstention = ""
        for flag in occupation_path_flags:
            warnings.append(flag)
        if not structured.occupation_uri:
            abstentions.append("esco_occupation")
        if not job_leaf or job_leaf in ("", "UNKNOWN"):
            abstentions.append("job_leaf")
            job_leaf = None
        decision = FamilyDecision(
            job_family=str(job_family or "UNKNOWN"),
            job_parent=str(job_parent or "UNKNOWN"),
            job_leaf=str(job_leaf) if job_leaf else None,
            family_tier=family_tier,
            family_method=family_method,
            family_semantic_score=family_semantic_score,
            family_semantic_margin=family_semantic_margin,
            normalized_title=normalized_title,
            occupation_paths=occupation_paths,
            semantic_decision=semantic_decision,
            additional_semantic_decision=additional_semantic_decision,
            responsibility_decision=responsibility_decision,
            title_decision=title_decision,
            title_analysis=title_analysis,
            leaf_override=leaf_override,
            hierarchy_validation=hierarchy_validation,
            occupation_path_metadata=occupation_path_metadata,
        )
        decision.warnings = list(warnings[warn_from:])
        decision.abstentions = list(abstentions[abstain_from:])
        return decision

    def extract(
        self,
        title: str,
        description: str,
        country: str = "",
        *,
        job_id: str = "",
        source: str = "",
        source_id: str | None = None,
        source_fields: dict[str, Any] | None = None,
        _language_trusted: object | None = None,
        _family: FamilyDecision | None = None,
    ) -> NormalizedJobOffer:
        # Callers that skip the preprocessing gate still hit this stopword check.
        # A boolean or request field does not satisfy the identity test.
        if _language_trusted is not LANGUAGE_TRUST:
            lang = classify_language(f"{title}\n{description}")
            if lang != "en":
                return NormalizedJobOffer(
                    identity=JobIdentity(job_id=job_id, title=title, normalized_title=title, source=source, source_id=source_id),
                    location=JobLocation(country=country or ""),
                    quality=JobQuality(
                        language=lang,
                        status="unsupported_language",
                        warnings=[f"language_gate_rejected:{lang}"],
                        extractor_version=SCHEMA_VERSION,
                    ),
                )

        title_model, description_model = to_model_text(title, description)
        full_title = title_model
        full_desc = description_model
        warnings: list[str] = []
        warnings.extend(self.startup_warnings)
        if self.semantic_resolver is not None and self.semantic_resolver.warning:
            warnings.append(self.semantic_resolver.warning)
        abstentions: list[str] = []

        # --- Skills (frozen stack) ---
        skill_entities: list[JobSkillEntity] = []
        raw_skills: list[dict[str, Any]] = []
        if self.en_skills is not None:
            try:
                raw_skills = self.en_skills.extract(full_desc, title=full_title)
                warnings.extend(self.en_skills.warnings)
                for e in raw_skills:
                    raw_cat = e.get("entity_type") or "SKILL"
                    cat = raw_cat
                    if cat == "PROFESSIONAL_SKILL":
                        cat = "SKILL"
                    elif cat not in ("SKILL", "KNOWLEDGE", "TECHNOLOGY"):
                        cat = "SKILL"
                    name = canonicalize_skill_name(e.get("name") or e.get("canonical") or e.get("surface") or "")
                    if not name:
                        continue
                    tax_id = e.get("taxonomy_id") or ""
                    kb_skill = None
                    if self.knowledge_base is not None:
                        if tax_id.startswith("TECH::"):
                            kb_skill = self.knowledge_base.normalize_skill({"skill_id": tax_id})
                        elif "NESTA" not in (e.get("sources") or []):
                            kb_skill = self.knowledge_base.normalize_skill({"label": name})
                    # The runtime technology taxonomy is authoritative for
                    # display spelling.  KB labels can lag an additive alias
                    # update (for example Azure DevOps), while the stable
                    # TECH::* identifier remains unchanged.
                    normalized_skill = (
                        name
                        if tax_id.startswith("TECH::")
                        else (kb_skill or {}).get("label") or name
                    )
                    skill_kind = (kb_skill or {}).get("kind") or (
                        "professional_skill" if raw_cat == "PROFESSIONAL_SKILL" else cat.casefold()
                    )
                    raw_esco = e.get("esco_uri")
                    if isinstance(raw_esco, str) and raw_esco.startswith("TECH::"):
                        raw_esco = None
                    if not raw_esco and tax_id.startswith("TECH::"):
                        raw_esco = None
                    elif not raw_esco and tax_id and not tax_id.startswith("TECH::"):
                        raw_esco = tax_id
                    skill_entities.append(
                        JobSkillEntity(
                            name=name,
                            canonical_id=(kb_skill or {}).get("skill_id")
                            or tax_id
                            or (professional_skill_id(name) if raw_cat == "PROFESSIONAL_SKILL" else name),
                            normalized_skill=normalized_skill,
                            skill_kind=skill_kind,
                            category=cat,  # type: ignore[arg-type]
                            esco_uri=raw_esco or None,
                            requirement=e.get("requirement") or "UNSPECIFIED",  # type: ignore[arg-type]
                            extraction_confidence=float(e.get("confidence") or 0.0),
                            requirement_confidence=float(e.get("requirement_confidence") or 0.0),
                            sources=list(e.get("sources") or []),
                            surface=e.get("surface") or "",
                            evidence=(e.get("sentence") or e.get("surface") or "")[:200],
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"en_skill_stack_failed:{exc}")

        # --- Structured fields V1 (source-first, no training) ---
        structured = extract_structured_fields(
            full_title,
            full_desc,
            skills=raw_skills,
            source_fields=source_fields,
            country=country,
        )

        if _family is None:
            _family = self._resolve_family(
                title,
                description,
                title_model,
                description_model,
                skill_entities,
                structured,
                warnings,
                abstentions,
            )
        else:
            warnings.extend(_family.warnings)
            abstentions.extend(_family.abstentions)
        job_family = _family.job_family
        job_parent = _family.job_parent
        job_leaf = _family.job_leaf
        family_tier = _family.family_tier
        family_method = _family.family_method
        family_semantic_score = _family.family_semantic_score
        family_semantic_margin = _family.family_semantic_margin
        normalized_title = _family.normalized_title
        occupation_paths = _family.occupation_paths
        semantic_decision = _family.semantic_decision
        additional_semantic_decision = _family.additional_semantic_decision
        responsibility_decision = _family.responsibility_decision
        title_decision = _family.title_decision
        title_analysis = _family.title_analysis
        leaf_override = _family.leaf_override
        hierarchy_validation = _family.hierarchy_validation
        occupation_path_metadata = _family.occupation_path_metadata

        # Run the standalone deterministic extraction pipeline for the six
        # requested fields.  Structured V1 remains the fallback for source
        # metadata, location, schedule and language requirement/level details.
        standalone_contract = self._extract_contract(full_title, full_desc, source_fields)
        standalone_education_result = self._extract_education_result(full_title, full_desc, country)
        standalone_education = self._education_public_level(standalone_education_result)
        standalone_contract_hint = standalone_contract or structured.contract.contract
        standalone_seniority, standalone_experience_bracket = self._extract_seniority(
            full_title, full_desc, standalone_contract_hint
        )
        standalone_work_mode = self._extract_work_mode(full_title, full_desc)
        standalone_languages = self._extract_languages(full_title, full_desc)

        # Contract and seniority are cross-field values in the public schema:
        # an internship is always an intern role with zero required prior
        # experience, and an INTERN seniority always means INTERNSHIP.
        resolved_contract_type = standalone_contract or structured.contract.contract
        if normalize_contract_type is not None:
            resolved_contract_type = normalize_contract_type(resolved_contract_type)
        resolved_seniority = standalone_seniority or "UNKNOWN"
        resolved_experience_bracket = (
            standalone_experience_bracket
            if standalone_experience_bracket is not None
            else (
                months_to_bracket(structured.experience.months_min).value
                if months_to_bracket is not None
                else "UNKNOWN"
            )
        )
        internship_rule_signal = (
            str(resolved_contract_type or "").upper() == "INTERNSHIP"
            or str(resolved_seniority or "").upper() == "INTERN"
        )
        missing_experience_before_rule = resolved_experience_bracket == "UNKNOWN"
        if enforce_internship_consistency is not None:
            (
                resolved_contract_type,
                resolved_seniority,
                resolved_experience_bracket,
                _cross_field_values_changed,
            ) = enforce_internship_consistency(
                resolved_contract_type,
                resolved_seniority,
                resolved_experience_bracket,
            )
            internship_consistency_applied = internship_rule_signal
            experience_default_applied = (
                not internship_rule_signal
                and missing_experience_before_rule
                and resolved_experience_bracket != "UNKNOWN"
            )
        else:  # pragma: no cover - only relevant to stripped deployments
            internship_consistency_applied = False
            experience_default_applied = False

        work_mode_value = standalone_work_mode or structured.work_mode.mode
        work_modes = [work_mode_value] if work_mode_value else []

        # Publisher/source education metadata is the most direct signal and
        # must outrank text mentions (which may occur in boilerplate).  A
        # non-NOT_STATED standalone decision is authoritative otherwise, even
        # when its public scalar is null (preferred-only or explicit no
        # requirement).
        source_education = structured.education.level if any(
            getattr(span, "source_text", "") == "SOURCE" for span in structured.education.evidence
        ) else "UNKNOWN"
        if source_education not in (None, "", "UNKNOWN"):
            edu_level = source_education
        elif standalone_education_result is not None and standalone_education_result.status != "NOT_STATED":
            edu_level = standalone_education
        else:
            edu_level = standalone_education or structured.education.level
        if edu_level == "UNKNOWN":
            edu_level = None

        structured_langs = [JobLanguage(language=h.language) for h in structured.languages]
        # Standalone language extraction supplies the authoritative names.
        if standalone_languages:
            by_name = {str(item.language).upper(): item for item in structured_langs}
            langs = [
                by_name.get(name, JobLanguage(language=name))
                for name in standalone_languages
            ]
        else:
            langs = structured_langs

        # Certifications: keep existing rule extractor (not in structured V1 core six, but schema needs it)
        certifications = extract_certifications(full_title, full_desc)
        cert_payload = certifications.value if isinstance(certifications.value, dict) else {}
        cert_all = cert_payload.get("all", []) if isinstance(cert_payload, dict) else []
        certs = [JobCertification(name=str(c), required=False, evidence="") for c in cert_all if c]

        if structured.occupation_method == "ABSTAIN":
            warnings.append("esco_occupation_abstain")

        def span_payload(span: Any) -> dict[str, str]:
            return {
                "text": _human_evidence_text(getattr(span, "raw_surface", "")),
                "source": _human_evidence_text(getattr(span, "source_text", "DESCRIPTION")) or "DESCRIPTION",
                "section": _human_evidence_text(getattr(span, "section", "OTHER")) or "OTHER",
                "method": _human_evidence_text(getattr(span, "method", "RULE")) or "RULE",
            }

        def fallback_evidence(field: str, value: Any) -> list[dict[str, str]]:
            """Keep an auditable text cue when the standalone adapter has no spans."""
            if value in (None, "", [], "UNKNOWN"):
                return []
            import re
            patterns = {
                "contract_type": r"\b(?:permanent|cdi|fixed[- ]term|cdd|freelance|freelancer|contractor|internship|intern|trainee|stagiaire|temporary|interim)\b",
                "education": r"\b(?:bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|doctorate|engineering degree|engineer diploma|bac\s*\+\s*[235])\b",
                "minimum_experience_bracket": r"\b\d+(?:\.\d+)?\s*(?:years?|months?|ans?|mois)\b",
                "work_mode": r"\b(?:remote|hybrid|onsite|on[- ]site|work from home|teletravail|office[- ]based)\b",
                "languages": r"\b(?:english|french|français|german|allemand|spanish|arabic|italian|dutch)\b",
            }
            m = re.search(patterns.get(field, r"$^"), f"{title}\n{description}", re.I)
            return [{"text": m.group(0), "source": "TITLE_OR_DESCRIPTION", "section": "OTHER", "method": "standalone_adapter_evidence"}] if m else []

        standalone_education_evidence = []
        if standalone_education_result is not None:
            standalone_education_evidence = [
                {
                    "text": _human_evidence_text(span.text),
                    "source": "TITLE_OR_DESCRIPTION",
                    "section": "OTHER",
                    "method": standalone_education_result.method,
                }
                for span in standalone_education_result.evidence
                if _human_evidence_text(span.text)
            ]
        field_evidence: dict[str, list[dict[str, str]]] = {
            "contract_type": [span_payload(x) for x in structured.contract.evidence],
            "education": [span_payload(x) for x in structured.education.evidence
                           if getattr(x, "source_text", "") == "SOURCE"]
            or _dedupe_evidence(standalone_education_evidence)
            or [span_payload(x) for x in structured.education.evidence],
            "minimum_experience_bracket": [span_payload(x) for x in structured.experience.evidence]
            or _dedupe_evidence(getattr(self, "_last_experience_evidence", [])),
            "work_mode": [span_payload(x) for x in structured.work_mode.evidence],
            "languages": [span_payload(x.evidence) for x in structured.languages if x.evidence],
            "seniority": _dedupe_evidence(getattr(self, "_last_seniority_evidence", [])),
            "family_parent_leaf": ([{"text": title, "source": "TITLE", "section": "TITLE", "method": family_method}] if job_family != "UNKNOWN" else []),
            "skills": _dedupe_evidence([
                {"text": s.evidence, "source": ",".join(s.sources), "section": "OTHER", "method": "NESTA+TECH_V2"}
                for s in skill_entities
            ]),
        }
        for field, value in {
            "contract_type": resolved_contract_type,
            "education": edu_level,
            "minimum_experience_bracket": resolved_experience_bracket,
            "work_mode": work_mode_value,
            "languages": standalone_languages or [x.language for x in structured.languages],
        }.items():
            # The standalone rules already validate exact spans. Do not
            # recreate experience or seniority evidence with a loose regex.
            if field in {"minimum_experience_bracket", "seniority"}:
                continue
            if not field_evidence[field]:
                field_evidence[field] = fallback_evidence(field, value)
        field_methods = {
            "contract_type": "source_or_structured_rule" if field_evidence["contract_type"] else "abstain",
            "education": "source_or_structured_rule" if field_evidence["education"] else "abstain",
            "minimum_experience_bracket": "structured_rule" if field_evidence["minimum_experience_bracket"] else "abstain",
            "work_mode": "source_or_structured_rule" if field_evidence["work_mode"] else "abstain",
            "languages": "structured_rule" if field_evidence["languages"] else "abstain",
            "seniority": "standalone_deterministic" if resolved_seniority != "UNKNOWN" else "abstain",
            "family_parent_leaf": family_method,
            "occupation_paths": "bottom_up_leaf_aggregation" if occupation_paths else "abstain",
            "skills": "NESTA+TECH_V2" if skill_entities else "abstain",
        }
        if internship_consistency_applied:
            for field in ("contract_type", "seniority", "minimum_experience_bracket"):
                field_methods[field] = "internship_consistency_rule"
            field_methods["seniority"] = "internship_consistency_rule"
            field_methods["minimum_experience_bracket"] = "internship_consistency_rule"
        elif experience_default_applied:
            field_methods["minimum_experience_bracket"] = "seniority_experience_default"

        return NormalizedJobOffer(
            schema_version=SCHEMA_VERSION,
            identity=JobIdentity(
                job_id=job_id,
                title=title,
                normalized_title=normalized_title,
                job_family=str(job_family or "UNKNOWN"),
                job_parent=str(job_parent or "UNKNOWN"),
                job_leaf=str(job_leaf) if job_leaf else None,
                esco_occupation_uri=structured.occupation_uri,
                esco_occupation_label=structured.occupation_label,
                source=source,
                source_id=source_id,
            ),
            location=JobLocation(
                country=structured.country or "",
                city=structured.city,
                work_modes=work_modes,  # type: ignore[arg-type]
            ),
            requirements=JobRequirements(
                contract_type=resolved_contract_type,
                # Contract extraction intentionally excludes hours/schedule;
                # retain the legacy field as UNKNOWN for API compatibility.
                work_schedule="UNKNOWN",
                seniority=resolved_seniority,
                minimum_experience_bracket=resolved_experience_bracket,
                education_level=edu_level,  # type: ignore[arg-type]
                education_requirement=structured.education.requirement,
            ),
            skills=skill_entities,
            languages=langs,
            occupation_paths=occupation_paths,
            certifications=certs,
            quality=JobQuality(
                language="en",
                warnings=warnings,
                abstentions=abstentions,
                extractor_version=SCHEMA_VERSION,
                family_resolver_method=family_method,
                family_semantic_score=family_semantic_score,
                family_semantic_margin=family_semantic_margin,
                field_evidence=field_evidence,
                field_methods=field_methods,
                decision_metadata={
                    "family": {
                        "startup": self.startup_metadata,
                        "method": family_method,
                        "tier": family_tier,
                        "semantic_score": family_semantic_score,
                        "semantic_margin": family_semantic_margin,
                        "semantic_decision": semantic_decision,
                        "responsibility_decision": responsibility_decision,
                        "title_analysis": title_analysis.as_dict() if hasattr(title_analysis, "as_dict") else title_analysis,
                        # Keep the unconstrained semantic shortlist visible for
                        # audit/output consumers. It is computed after a
                        # deterministic path to expose plausible alternatives
                        # without changing the accepted legacy identity.
                        "additional_semantic_decision": additional_semantic_decision,
                        "title_vector_decision": title_decision,
                        "policy_id": self.leaf_policy.policy_id,
                        "knowledge_base_version": self.knowledge_base_version,
                        "semantic_leaf_allowed": self.semantic_leaf_allowed,
                        "semantic_corroboration_enabled": True,
                        "decision_layer": "occupation_decision_v2_1",
                        "leaf_mode": self.leaf_mode,
                        "leaf_override": leaf_override,
                        "hierarchy_validation": hierarchy_validation,
                        "occupation_paths": occupation_path_metadata,
                        "education": (
                            standalone_education_result.to_rich_dict()
                            if standalone_education_result is not None
                            else None
                        ),
                    }
                },
                status="ok",
            ),
        )

    def _extract_contract(self, title: str, description: str, source_fields: dict[str, Any] | None) -> str | None:
        if self.contract_extractor is None:
            return None
        try:
            result = self.contract_extractor.extract(title, description, source_fields)
            values = result.to_dict().get("contract_types", [])
            # The public NormalizedJobOffer schema has one canonical contract
            # field.  The standalone extractor's deterministic ordering makes
            # the first value the stable projection of a multi-signal result.
            if not values:
                return None
            # Keep the standalone vocabulary and the public matching schema
            # compatible at this adapter boundary.
            if normalize_contract_type is not None:
                return normalize_contract_type(str(values[0]))
            return str(values[0])
        except Exception:
            return None

    def _extract_education_result(self, title: str, description: str, country: str):
        try:
            # Education rules are country-sensitive; create this lightweight
            # extractor with the request country rather than caching one.
            extractor = _education_extractor_for_country(country or "")
            return extractor.extract(title, description) if extractor else None
        except Exception:
            return None

    @staticmethod
    def _education_public_level(result: Any) -> str | None:
        if result is None:
            return None
        value = getattr(result, "value", None)
        if value in (None, "", "UNKNOWN", "NO_FORMAL_REQUIREMENT"):
            return None
        mapping = {
            "UNKNOWN": "UNKNOWN",
            "SECONDARY": "UNKNOWN",
            "SHORT_CYCLE_TERTIARY": "ASSOCIATE",
            "BACHELOR": "BACHELOR",
            "ENGINEERING_DEGREE": "MASTER_OR_HIGHER",
            "MASTER": "MASTER_OR_HIGHER",
            "MASTER_OR_HIGHER": "MASTER_OR_HIGHER",
            "DOCTORATE": "MASTER_OR_HIGHER",
        }
        if str(value) in mapping:
            return mapping[str(value)]
        return str(value)

    def _extract_education(self, title: str, description: str, country: str) -> str | None:
        """Backward-compatible scalar adapter for callers outside ``extract``."""
        result = self._extract_education_result(title, description, country)
        if result is not None and getattr(result, "status", "NOT_STATED") != "NOT_STATED":
            return self._education_public_level(result)
        if result is not None and getattr(result, "value", None):
            return self._education_public_level(result)
        levels = result.to_dict().get("required_education_levels", []) if result is not None else []
        if not levels:
            return None
        # The public schema has one level; preserve the strongest detected
        # level while the standalone result retains all alternatives. Do not
        # use list order: a description may mention Bachelor before Master.
        mapping = {
            "UNKNOWN": "UNKNOWN",
            "SECONDARY": "UNKNOWN",
            "SHORT_CYCLE_TERTIARY": "ASSOCIATE",
            "BACHELOR": "BACHELOR",
            "ENGINEERING_DEGREE": "MASTER_OR_HIGHER",
            "MASTER": "MASTER_OR_HIGHER",
            "MASTER_OR_HIGHER": "MASTER_OR_HIGHER",
            "DOCTORATE": "MASTER_OR_HIGHER",
        }
        rank = {"UNKNOWN": 0, "ASSOCIATE": 1, "BACHELOR": 2, "MASTER_OR_HIGHER": 3,
                # Accept legacy values from older serialized extractor results.
                "HIGH_SCHOOL": 0, "VOCATIONAL_DIPLOMA": 1, "PROFESSIONAL_DIPLOMA": 1,
                "ENGINEERING_DEGREE": 3, "MASTER": 3, "DOCTORATE": 3}
        strongest = max((str(level) for level in levels), key=lambda value: rank.get(value, 0), default="UNKNOWN")
        return mapping.get(strongest, None)

    def _extract_seniority(
        self, title: str, description: str, contract_type: str | None = None
    ) -> tuple[str | None, str | None]:
        if self.seniority_experience_extractor is None:
            self._last_seniority_evidence = []
            self._last_experience_evidence = []
            return None, None
        try:
            result = self.seniority_experience_extractor.extract(title, description, contract_type)
            bracket = result.min_experience_bracket.value
            value = getattr(getattr(result, "_seniority", None), "value", None)
            # ``MID_LEVEL`` is the standalone extractor's precise label; the
            # normalized public contract historically calls it ``MID``.
            seniority = {"MID_LEVEL": "MID"}.get(str(value), str(value) if value and value != "UNSPECIFIED" else None)
            evidence_text = _human_evidence_text(getattr(result, "evidence_text", None))
            evidence_source = _human_evidence_text(getattr(result, "evidence_source", None))
            span = {"text": evidence_text, "source": evidence_source or "DESCRIPTION", "section": "TITLE" if evidence_source == "TITLE" else "OTHER", "method": "standalone_deterministic"}
            self._last_experience_evidence = [span] if evidence_text and bracket != "UNKNOWN" else []
            self._last_seniority_evidence = [span] if evidence_text and seniority not in (None, "UNKNOWN") else []
            return seniority, str(bracket) if bracket else "UNKNOWN"
        except Exception:
            self._last_seniority_evidence = []
            self._last_experience_evidence = []
            return None, None

    def _extract_work_mode(self, title: str, description: str) -> str | None:
        if self.work_mode_extractor is None:
            return None
        try:
            values = self.work_mode_extractor.extract(title, description).to_dict().get("work_modes", [])
            return str(values[0]) if values else None
        except Exception:
            return None

    @staticmethod
    def _extract_languages(title: str, description: str) -> list[str]:
        if extract_languages_src is None:
            return []
        try:
            return [str(value) for value in extract_languages_src(title, description).get("languages", [])]
        except Exception:
            return []

    def extract_v1(
        self,
        title: str,
        description: str,
        country: str = "",
        *,
        _language_trusted: object | None = None,
        _family: FamilyDecision | None = None,
    ) -> NormalizedJobProfileV1:
        """Compatibility shim — maps EN_V1 offer into legacy flat V1 profile."""
        offer = self.extract(
            title, description, country=country, _language_trusted=_language_trusted, _family=_family
        )
        if offer.quality.status == "unsupported_language":
            return validate(
                NormalizedJobProfileV1(
                    pipeline_version=self.pipeline_version,
                    location=Location(country=country or None),
                )
            )
        required = [s.name for s in offer.skills if s.requirement == "REQUIRED"]
        preferred = [s.name for s in offer.skills if s.requirement == "PREFERRED"]
        unspecified = [s.name for s in offer.skills if s.requirement == "UNSPECIFIED"]
        preferred = preferred + unspecified
        wm = offer.location.work_modes[0] if offer.location.work_modes else "UNKNOWN"
        result = NormalizedJobProfileV1(
            job_family_parent=offer.identity.job_parent,
            job_family_leaf=offer.identity.job_leaf or "UNKNOWN",
            seniority=offer.requirements.seniority,
            contract_type=offer.requirements.contract_type,
            work_mode=wm,
            minimum_experience_bracket=offer.requirements.minimum_experience_bracket,
            education_level=offer.requirements.education_level or "UNKNOWN",
            education_requirement=offer.requirements.education_requirement or "UNKNOWN",
            required_skills=required,
            preferred_skills=preferred,
            certifications=[c.name for c in offer.certifications],
            certification_requirements=CertificationRequirements(),
            languages=[str(lg.language) for lg in offer.languages],
            location=Location(country=offer.location.country or None),
            evidence=[],
            pipeline_version=self.pipeline_version,
        )
        return validate(result)

    def extract_skills_only(
        self,
        title: str,
        description: str,
        *,
        _language_trusted: object | None = None,
    ) -> dict[str, list[dict]]:
        """Extract only NESTA professional skills and Technology V2 technologies.

        This is the stable skills-only view. It intentionally has no REQUIRED,
        PREFERRED, or UNSPECIFIED buckets.
        """
        return self.extract(title, description, _language_trusted=_language_trusted).skills_only()

    def _predict_seniority(self, title: str, description: str) -> RuleHit | None:
        if self.seniority_model is None:
            return None
        return self.seniority_model.predict(title, description)


_SERVICE: JobNLPService | None = None


def get_service() -> JobNLPService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = JobNLPService()
    return _SERVICE


def extract_job(title: str, description: str, country: str = "") -> dict:
    return get_service().extract(title, description, country=country).model_dump(mode="json")
