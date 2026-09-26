"""Job-family taxonomy candidate engine (regex = evidence only)."""
from __future__ import annotations

import json
import sqlite3
import re
import unicodedata
from functools import lru_cache

from rapidfuzz import fuzz

from job_nlp.paths import KNOWLEDGE_BASE_DIR, TAXONOMY_JSON
from job_nlp.pipeline.schemas import TaxonomyCandidate


def normalize_rule_title(title: str) -> str:
    text = unicodedata.normalize("NFKC", title or "")
    text = text.casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text


@lru_cache(maxsize=1)
def _load_entries() -> tuple[dict, ...]:
    if not TAXONOMY_JSON.exists():
        return ()
    data = json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))
    return tuple(data.get("entries", []))

@lru_cache(maxsize=1)
def _load_reassignments() -> dict[tuple[str, str], tuple[str, str, str]]:
    db_path = KNOWLEDGE_BASE_DIR / "it_knowledge.sqlite"
    if not db_path.exists(): return {}
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as db:
        # Optional table: older production KB snapshots do not contain it.
        # The live resolver does not depend on this catalogue, so absence is
        # an empty mapping rather than a startup failure.
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='leaf_reassignment'").fetchone() is None:
            return {}
        return {(str(leaf), str(pattern)): (str(family), str(parent), str(leaf)) for leaf, pattern, kb_leaf, parent, family in db.execute("SELECT job_nlp_leaf_id,job_nlp_pattern_id,kb_leaf_id,kb_parent_id,kb_family_id FROM leaf_reassignment WHERE kb_leaf_id IS NOT NULL")}


@lru_cache(maxsize=1)
def _load_live_leaf_paths() -> dict[str, tuple[str, str]]:
    """Return the current leaf→parent→family paths from the production KB.

    The title-pattern JSON is a legacy alias catalogue and contains historical
    parent/family IDs.  Candidate resolution must inherit the live relational
    path, otherwise valid aliases such as ``Scrum Master`` are rejected later
    as stale hierarchy paths.
    """
    db_path = KNOWLEDGE_BASE_DIR / "it_knowledge.sqlite"
    if not db_path.exists():
        return {}
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as db:
        rows = db.execute(
            """
            SELECT l.leaf_id, l.parent_id, p.family_id
            FROM leaf AS l
            JOIN parent AS p ON p.parent_id = l.parent_id
            """
        ).fetchall()
    return {str(leaf): (str(parent), str(family)) for leaf, parent, family in rows}


def _live_candidate_path(entry: dict) -> tuple[str | None, str | None, str | None, bool]:
    """Return a legacy entry's current KB IDs without inventing a label.

    Both the regex and fuzzy alias catalogues predate the production
    8-family taxonomy.  They therefore may contain a correct leaf with an
    obsolete parent/family (for example ``CLOUD_ENGINEERING`` instead of
    ``CLOUD_AND_PLATFORM``).  The relational KB is authoritative for the
    hierarchy; aliases remain evidence only.  ``unresolved`` stays true when
    neither the catalogued leaf ID nor the alias leaf name exists in the live
    KB.
    """
    raw_leaf_id = str(entry.get("kb_leaf_id") or "")
    live_paths = _load_live_leaf_paths()
    live_path = live_paths.get(raw_leaf_id)
    if live_path is None and not raw_leaf_id:
        fallback_leaf_id = str(entry.get("leaf") or "")
        live_path = live_paths.get(fallback_leaf_id)
        if live_path is not None:
            raw_leaf_id = fallback_leaf_id
    parent_id = live_path[0] if live_path else entry.get("kb_parent_id")
    family_id = live_path[1] if live_path else entry.get("kb_family_id")
    leaf_id = raw_leaf_id or entry.get("kb_leaf_id")
    unresolved = bool(entry.get("unresolved", not leaf_id)) or live_path is None
    return leaf_id, parent_id, family_id, unresolved


def collect_candidates(title: str, *, allowed_parent: str | None = None) -> list[TaxonomyCandidate]:
    rule_title = normalize_rule_title(title)
    if not rule_title:
        return []

    candidates: list[TaxonomyCandidate] = []
    for entry in _load_entries():
        if allowed_parent and entry.get("parent") != allowed_parent:
            continue
        pattern = entry.get("title_regex") or ""
        if not pattern:
            continue
        try:
            match = re.search(pattern, rule_title)
        except re.error:
            continue
        if not match:
            continue
        # Rehydrate a legacy candidate with the current production hierarchy.
        # Keep unresolved aliases unresolved; only a live leaf ID can provide
        # a safe path and no new taxonomy label is invented here.
        kb_leaf_id, kb_parent_id, kb_family_id, unresolved = _live_candidate_path(entry)
        candidates.append(
            TaxonomyCandidate(
                leaf=entry["leaf"],
                parent=entry["parent"] or "UNKNOWN",
                priority=int(entry.get("priority", 0)),
                matched_text=match.group(0),
                pattern_id=entry.get("pattern_id", f"{entry['parent']}.{entry['leaf']}"),
                kb_leaf_id=kb_leaf_id,
                kb_parent_id=kb_parent_id,
                kb_family_id=kb_family_id,
                unresolved=unresolved,
            )
        )
    return candidates


_TRIVIAL_TITLE_TOKENS = frozenset(
    "senior junior sr jr lead principal staff ii iii iv m f mf remote onsite hybrid"
    .split()
)
_DISTINCTIVE_TITLE_TOKENS = frozenset(
    "devops devsecops etl noc helpdesk kubernetes scrum frontend backend fullstack android ios"
    .split()
)


def title_token_set(title: str) -> set[str]:
    """Normalize title wording for order/spacing/punctuation-robust matching."""
    text = unicodedata.normalize("NFKC", title or "").casefold()
    text = re.sub(r"[()\[\]{}.,:/+&_-]+", " ", text)
    return {t for t in re.findall(r"[a-z0-9]+", text) if t not in _TRIVIAL_TITLE_TOKENS}


def collect_fuzzy_candidates(title: str, *, threshold: int = 90) -> list[TaxonomyCandidate]:
    """Match documented aliases using token-set similarity (Tier 1b)."""
    query = title_token_set(title)
    if not query:
        return []
    out: list[TaxonomyCandidate] = []
    for entry in _load_entries():
        aliases = [entry.get("leaf", ""), entry.get("parent", ""), entry.get("aliases", "")]
        best = 0
        best_text = ""
        for alias_blob in aliases:
            for alias in re.split(r"[;,|]", str(alias_blob or "")):
                alias_tokens = title_token_set(alias)
                if not alias_tokens:
                    continue
                # Token-set similarity is intentionally asymmetric: a short
                # generic query such as ``Software Engineer`` is a subset of
                # many specialised aliases (``Bioinformatics Software
                # Engineer``).  Accepting those supersets creates a false
                # leaf instead of the correct parent-only abstention.  A
                # longer alias is usable only when the query contains a
                # distinctive routing token (DevOps, Kubernetes, etc.).
                if alias_tokens - query and not (query & alias_tokens & _DISTINCTIVE_TITLE_TOKENS):
                    continue
                score = fuzz.token_set_ratio(" ".join(sorted(query)), " ".join(sorted(alias_tokens)))
                if query & alias_tokens & _DISTINCTIVE_TITLE_TOKENS:
                    # A distinctive role token is sufficient to select the
                    # documented role family when modifiers/location tokens
                    # obscure the full alias (e.g. ``Senior Devops France``).
                    score = max(score, 90)
                if score > best:
                    best, best_text = score, alias.strip()
        if best < threshold:
            continue
        path = _live_candidate_path(entry)
        out.append(
            TaxonomyCandidate(
                leaf=entry["leaf"],
                parent=entry["parent"] or "UNKNOWN",
                priority=min(99, int(best)),
                matched_text=best_text,
                pattern_id=entry.get("pattern_id", f"{entry['parent']}.{entry['leaf']}"),
                source="TITLE_FUZZY",
                kb_leaf_id=path[0],
                kb_parent_id=path[1],
                kb_family_id=path[2],
                unresolved=path[3],
            )
        )
    return out


def rank_candidates(candidates: list[TaxonomyCandidate]) -> list[TaxonomyCandidate]:
    return sorted(
        candidates,
        key=lambda c: (c.priority, len(c.matched_text)),
        reverse=True,
    )


def resolve_candidates(
    candidates: list[TaxonomyCandidate],
    *,
    neural_parent: str | None = None,
    min_priority: int = 70,
) -> tuple[str, str, TaxonomyCandidate | None]:
    """Return (parent, leaf, best_candidate). Abstain to UNKNOWN when weak."""
    if not candidates:
        return "UNKNOWN", "UNKNOWN", None

    ranked = rank_candidates([c for c in candidates if not c.unresolved and c.kb_leaf_id])
    if not ranked:
        return "UNKNOWN", "UNKNOWN", None
    best = ranked[0]

    if best.priority < min_priority and len(best.matched_text) < 4:
        return "UNKNOWN", "UNKNOWN", None

    if neural_parent and neural_parent not in ("UNKNOWN", "NON_IT") and best.kb_parent_id != neural_parent:
        # ponytail: parent mismatch → abstain leaf, let neural parent win
        return neural_parent, "UNKNOWN", best

    return best.kb_parent_id or "UNKNOWN", best.kb_leaf_id or "UNKNOWN", best
