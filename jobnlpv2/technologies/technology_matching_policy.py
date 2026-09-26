"""Technology matching policy — SAFE / CONTEXT_REQUIRED acceptance gates.

Production name for the former D.2 precision helpers. Ordinary English lemmas
must not become technologies solely via lowercase alias equality.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_LEMMA_PATH = Path(__file__).resolve().parent / "english_common_lemmas.txt"

_LIST_LINE_HINT = re.compile(
    r"(technolog|stack|frameworks?|langages?|platforms?|libraries|"
    r"database|cloud|outils?|environnement|\btools?\b|"
    r"experience with|knowledge of|familiar with|proficient in|hands[- ]on)",
    re.IGNORECASE,
)
_LANGUAGE_AFTER = re.compile(
    r"^\s*(english|french|arabic|german|spanish|italian|mandarin|dutch|"
    r"portuguese|chinese|japanese|korean|russian|turkish|hindi)\b",
    re.IGNORECASE,
)
_PROSE_ANTIPATTERNS = [
    re.compile(r"(?i)\bfluent\s+(english|french|german|arabic|spanish|italian)\b"),
    re.compile(r"(?i)\b(basic|good|solid|strong)\s+(knowledge|understanding|skills?|grasp)\b"),
    re.compile(r"(?i)\bmake\s+(sure|adjustments|decisions|recommendations|progress)\b"),
    re.compile(r"(?i)\banaly[sz]e\s+(and|the|data|processes|requirements|customer)\b"),
    re.compile(r"(?i)\bembrace\s+(design|change|new|our|the|a)\b"),
    re.compile(r"(?i)\bkeep\s+(up|track|in\s+mind|your|the|our)\b"),
    re.compile(r"(?i)\bplay\s+(an?\s+)?(important|key|active|critical|major)\b"),
    re.compile(r"(?i)\bmove\s+(to|into|forward|quickly|fast)\b"),
    re.compile(r"(?i)\bscale\s+(up|down|our|the|your)\b"),
    re.compile(r"(?i)\bclear\s+(communication|understanding|vision|objectives)\b"),
    re.compile(r"(?i)\bprocessing\s+(of|data|information|requests)\b"),
    re.compile(r"(?i)\bunstructured\s+(data|text|information)\b"),
    re.compile(r"(?i)\bjust\s+(a|an|the|need|want|have|to)\b"),
    re.compile(r"(?i)\bkind\s+of\b"),
    re.compile(r"(?i)\bman\s+(page|pages)\b"),  # allow "man page" as tech context elsewhere
]

# Canonicals that stay matchable even if the lemma is also English (IT job default sense).
_TECH_STRONG_SAFE = frozenset({
    "Python", "Java", "JavaScript", "TypeScript", "Docker", "Kubernetes",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "React", "Angular", "Vue.js",
    "Node.js", "Django", "Flask", "Amazon Web Services", "Microsoft Azure",
    "Google Cloud Platform", "Git", "GitHub", "GitLab", "Jenkins", "Terraform",
    "Ansible", "Nginx", "Apache", "Kafka", "HTML", "CSS", "SQL", "NoSQL",
    "Linux", "PHP", "C#", "C++", "Go", "Rust", "Swift", "Kotlin", "Ruby",
    "Symfony", "Laravel", "Flutter", "Datadog", "Prometheus", "Grafana",
    "CMake", "Makefile",
})

_TECH_STRONG_SAFE_LOWER = frozenset(x.lower() for x in _TECH_STRONG_SAFE)

# Job-ad English missing from the 10k frequency list (fluent, analyze, …).
_EXTRA_COMMON = frozenset(
    """fluent basic analyze analyse analyzing analyzed embrace keep play
    move make making made clear just kind less man reach score choices
    processing unstructured scale reason factor fear fish gas spring star
    edge near red reduce
    """.split()
)


@lru_cache(maxsize=1)
def load_common_lemmas() -> frozenset[str]:
    path = _LEMMA_PATH
    base = set()
    if path.exists():
        base = {ln.strip().lower() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}
    return frozenset(base | _EXTRA_COMMON)


def is_strong_safe_tech(canonical: str, alias: str = "") -> bool:
    for x in (canonical, alias):
        if not x:
            continue
        if x in _TECH_STRONG_SAFE or x.lower() in _TECH_STRONG_SAFE_LOWER:
            return True
    return False


def is_common_english_lemma(text: str) -> bool:
    key = text.strip().lower()
    if not key:
        return False
    return key in load_common_lemmas()


def assign_matching_policy(
    canonical: str,
    aliases: list[str],
    *,
    source_count: int,
    hot: bool,
    demand: bool,
    category: str,
    any_it_rel: bool,
) -> str:
    """Build-time policy assignment for lexicon rows."""
    if not any_it_rel:
        return "DISABLED_BY_DEFAULT"
    names = [canonical, *aliases]
    if any(is_strong_safe_tech(canonical, a) for a in names):
        return "SAFE"

    keys = {n.strip().lower() for n in names if n.strip()}
    if any(len(k) <= 2 for k in keys):
        return "CONTEXT_REQUIRED"

    canon_l = canonical.strip().lower()
    common_collision = any(is_common_english_lemma(k) for k in keys)
    if common_collision:
        if is_common_english_lemma(canon_l) and source_count <= 1 and category in {"OTHER_IT_TECH", "SECURITY_TOOL"}:
            return "DISABLED_BY_DEFAULT"
        return "CONTEXT_REQUIRED"

    if source_count >= 2 or hot or demand or category != "OTHER_IT_TECH":
        return "SAFE"
    return "CONTEXT_REQUIRED"


# Aliases that are ordinary English and must not index a different product name.
_BLOCK_GENERIC_ALIASES = frozenset(
    "make just man gas red near fish fear score reach kind clear keep play "
    "move scale reason edge spring star factor embrace fluent basic analyze analyse "
    "processing unstructured choices".split()
)


def skip_generic_english_alias(alias: str, canonical: str) -> bool:
    """Do not index ordinary English as an alias of a different product (make→Makefile)."""
    al = alias.strip().lower()
    if al not in _BLOCK_GENERIC_ALIASES:
        return False
    if is_strong_safe_tech(canonical, alias):
        return False
    return al != canonical.strip().lower()


def _line_window(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    return text[line_start:line_end]


def _strict_tech_context(
    text: str,
    start: int,
    end: int,
    confirmed: list[tuple[int, int]],
) -> bool:
    line = _line_window(text, start, end)
    if _LIST_LINE_HINT.search(line):
        return True
    # Same-line neighbour confirmed tech (not self)
    for a, b in confirmed:
        if a == start and b == end:
            continue
        ls = text.rfind("\n", 0, a) + 1
        le = text.find("\n", b)
        if le < 0:
            le = len(text)
        if ls <= start < le and a < end + 30 and b > start - 30:
            return True
    return False


def matches_prose_antipattern(text: str, start: int, end: int) -> bool:
    base = max(0, start - 15)
    window = text[base : min(len(text), end + 40)]
    for p in _PROSE_ANTIPATTERNS:
        m = p.search(window)
        if not m:
            continue
        # Require the antipattern to overlap this candidate span (not a neighbour).
        abs_start = base + m.start()
        abs_end = base + m.end()
        if abs_start < end and abs_end > start:
            return True
    return False


def has_distinctive_tech_casing(surface: str, alias: str, canonical: str) -> bool:
    """True when surface looks like intentional tech naming, not prose."""
    if not surface:
        return False
    if re.fullmatch(r"[A-Z0-9][A-Z0-9+#./_-]{1,}", surface):
        return True
    if any(ch in surface for ch in "+#./"):
        return True
    ref = canonical or alias
    if ref and surface.lower() == ref.lower() and surface != surface.lower():
        return True
    if alias and surface == alias:
        return True
    return False


def _comma_list_local(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 40) : min(len(text), end + 40)]
    return any(sep in window for sep in (",", ";", "|", "•", "/"))


def accept_tech_match(
    surface: str,
    alias: str,
    canonical: str,
    policy: str,
    text: str,
    start: int,
    end: int,
    confirmed: list[tuple[int, int]],
) -> tuple[bool, str]:
    """Runtime gate. Returns (accept, reject_reason)."""
    if policy == "DISABLED_BY_DEFAULT":
        return False, "disabled_by_default"

    alias_l = alias.strip().lower()
    surface_l = surface.strip().lower()
    strong = is_strong_safe_tech(canonical, alias) or is_strong_safe_tech(canonical, surface)
    common = (is_common_english_lemma(alias_l) or is_common_english_lemma(surface_l)) and not strong

    if matches_prose_antipattern(text, start, end):
        return False, "prose_antipattern"

    after = text[end : end + 24]
    if _LANGUAGE_AFTER.match(after):
        return False, "language_proficiency"

    if " " in surface.strip() and common and not _strict_tech_context(text, start, end, confirmed):
        return False, "common_multiword_prose"

    if common:
        if surface == surface.lower():
            return False, "common_lowercase"
        # ALLCAPS in a comma/stack list is often a real token (LESS, REST).
        if surface.isupper() and len(surface) >= 3 and (
            _strict_tech_context(text, start, end, confirmed) or _comma_list_local(text, start, end)
        ):
            return True, ""
        if not _strict_tech_context(text, start, end, confirmed):
            return False, "common_no_tech_context"

    elif policy == "CONTEXT_REQUIRED":
        if not _strict_tech_context(text, start, end, confirmed):
            if not has_distinctive_tech_casing(surface, alias, canonical):
                return False, "context_required"
            if len(alias_l) <= 5 and not _LIST_LINE_HINT.search(_line_window(text, start, end)):
                return False, "short_alias_no_list"

    return True, ""


def audit_alias_collisions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return collision audit records for active lexicon rows."""
    out: list[dict[str, str]] = []
    for row in rows:
        canon = row.get("canonical_name") or ""
        policy = row.get("matching_policy") or "SAFE"
        aliases = [canon] + [a.strip() for a in (row.get("aliases") or "").split("|") if a.strip()]
        for alias in aliases:
            al = alias.lower()
            if not is_common_english_lemma(al):
                continue
            out.append(
                {
                    "alias": alias,
                    "canonical": canon,
                    "policy": policy,
                    "category": row.get("category") or "",
                    "strong_safe": str(is_strong_safe_tech(canon)),
                    "recommended_policy": assign_matching_policy(
                        canon,
                        [a for a in aliases if a != canon],
                        source_count=int(row.get("source_count") or 0),
                        hot=(row.get("onet_hot_technology") or "") == "Y",
                        demand=(row.get("onet_in_demand") or "") == "Y",
                        category=row.get("category") or "",
                        any_it_rel=(row.get("active_for_it_matching") or "") == "Y",
                    ),
                }
            )
    return out
