"""Load technologies_best.csv, normalize, exact lookup, bounded full-text recovery."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from technology_matching_policy import accept_tech_match, is_strong_safe_tech

RUNTIME_CSV = Path(__file__).resolve().parents[1] / "leaf" / "inputs" / "technologies_best.csv"
_TOKEN_RE = re.compile(r"[\w][\w+#./_-]*", re.UNICODE)


def normalize_key(text: str) -> str:
    s = (text or "").strip().lower()
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"[^\w+#./\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace(" / ", "/").replace(" - ", "-")


@dataclass(frozen=True)
class TechRec:
    tech_id: str
    canonical: str
    alias: str
    policy: str
    category: str


@dataclass
class TechHit:
    surface: str
    canonical: str
    taxonomy_id: str
    start: int
    end: int
    matching_policy: str
    match_type: str
    source: str
    sentence: str = ""
    source_text: str = "DESCRIPTION"  # TITLE | DESCRIPTION


class _TrieNode:
    __slots__ = ("children", "terminal")

    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.terminal: list[TechRec] = []


@dataclass
class TaxonomyIndex:
    by_key: dict[str, tuple[TechRec, ...]]
    trie: _TrieNode
    recs: tuple[TechRec, ...]


def _tokenize(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]


def _is_boundary(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    return not before.isalnum() and not after.isalnum()


@lru_cache(maxsize=1)
def load_taxonomy(path: str | None = None) -> TaxonomyIndex:
    csv_path = Path(path) if path else RUNTIME_CSV
    by_key: dict[str, list[TechRec]] = {}
    all_recs: list[TechRec] = []
    root = _TrieNode()
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            policy = (row.get("matching_policy") or "SAFE").strip()
            if policy in {"DISABLED", "DISABLED_BY_DEFAULT"}:
                continue
            canon = (row.get("canonical_name") or row.get("technology") or "").strip()
            tid = (row.get("tech_id") or row.get("technology_id") or "").strip()
            cat = (row.get("category") or "").strip()
            aliases = [canon] + [
                a.strip() for a in re.split(r"[|;]", row.get("aliases") or "") if a.strip()
            ]
            for alias in aliases:
                al = alias.strip()
                if len(al) < 2:
                    continue
                base = al.rstrip("*+#").strip()
                # Single/double letter cores (F, F*, R, …) collide with prose.
                if len(base) <= 2 and base.isalnum() and not is_strong_safe_tech(canon, al):
                    continue
                rec = TechRec(tid, canon, al, policy, cat)
                all_recs.append(rec)
                by_key.setdefault(normalize_key(alias), []).append(rec)
                toks = [t.lower() for t in _TOKEN_RE.findall(alias)]
                if not toks:
                    continue
                node = root
                for t in toks:
                    node = node.children.setdefault(t, _TrieNode())
                node.terminal.append(rec)
    frozen: dict[str, tuple[TechRec, ...]] = {}
    for k, lst in by_key.items():
        lst.sort(
            key=lambda r: (
                0 if r.policy == "SAFE" else 1,
                0 if is_strong_safe_tech(r.canonical, r.alias) else 1,
                -len(r.alias),
            )
        )
        frozen[k] = tuple(lst)
    return TaxonomyIndex(by_key=frozen, trie=root, recs=tuple(all_recs))


def lookup_exact(surface: str, index: TaxonomyIndex | None = None) -> tuple[TechRec | None, str]:
    idx = index or load_taxonomy()
    keys = [normalize_key(surface)]
    stripped = surface.strip(" .,;:|()[]")
    if stripped:
        keys.append(normalize_key(stripped))
    spaced = normalize_key(surface).replace(" ", "/")
    if spaced not in keys:
        keys.append(spaced)
    for key in keys:
        recs = idx.by_key.get(key)
        if not recs:
            continue
        rec = recs[0]
        if normalize_key(rec.canonical) == key:
            mt = "CANONICAL_EXACT"
        elif key != normalize_key(surface):
            mt = "NORMALIZED_EXACT"
        else:
            mt = "ALIAS_EXACT"
        return rec, mt
    return None, "NO_TECH_MATCH"


def _try_accept(
    surface: str, rec: TechRec, text: str, start: int, end: int, confirmed: list[tuple[int, int]]
) -> bool:
    ok, _ = accept_tech_match(surface, rec.alias, rec.canonical, rec.policy, text, start, end, confirmed)
    return ok


def classify_nesta_span(
    surface: str,
    text: str,
    start: int,
    end: int,
    confirmed: list[tuple[int, int]],
    index: TaxonomyIndex | None = None,
) -> tuple[TechHit | None, list[TechHit]]:
    idx = index or load_taxonomy()
    contained: list[TechHit] = []
    rec, mt = lookup_exact(surface, idx)
    if rec is not None and _try_accept(surface, rec, text, start, end, confirmed):
        return (
            TechHit(
                surface=surface,
                canonical=rec.canonical,
                taxonomy_id=rec.tech_id,
                start=start,
                end=end,
                matching_policy=rec.policy,
                match_type=mt,
                source="NESTA",
            ),
            contained,
        )

    if " " in surface.strip() or "/" in surface:
        for m in _TOKEN_RE.finditer(surface):
            tok = m.group(0)
            if len(tok) < 2:
                continue
            crec, _cmt = lookup_exact(tok, idx)
            if crec is None:
                continue
            cs, ce = start + m.start(), start + m.end()
            if not _try_accept(tok, crec, text, cs, ce, confirmed):
                continue
            contained.append(
                TechHit(
                    surface=tok,
                    canonical=crec.canonical,
                    taxonomy_id=crec.tech_id,
                    start=cs,
                    end=ce,
                    matching_policy=crec.policy,
                    match_type="CONTAINED_EXACT",
                    source="NESTA",
                )
            )
    return None, contained


def recover_full_text(
    text: str,
    occupied: list[tuple[int, int]] | None = None,
    *,
    source_text: str = "DESCRIPTION",
) -> list[TechHit]:
    """Bounded V2 recovery: slash aliases, slash compounds, trie exact. Technologies only.

    Offsets are relative to ``text``. ``source_text`` records whether that text is
    TITLE or DESCRIPTION (caller responsibility).
    """
    idx = load_taxonomy()
    occupied = list(occupied or [])
    hits: list[TechHit] = []

    # 0) Aliases that themselves contain '/' (Oracle PL/SQL, CI/CD, …) — longest first
    slash_aliases = sorted(
        {r.alias: r for r in idx.recs if "/" in r.alias}.values(),
        key=lambda r: len(r.alias),
        reverse=True,
    )
    for rec in slash_aliases:
        try:
            pat = re.compile(
                rf"(?<![A-Za-z0-9+#]){re.escape(rec.alias)}(?![A-Za-z0-9+#])",
                re.IGNORECASE,
            )
        except re.error:
            continue
        for m in pat.finditer(text):
            start, end = m.start(), m.end()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            surface = text[start:end]
            if not _try_accept(surface, rec, text, start, end, occupied):
                continue
            occupied.append((start, end))
            hits.append(
                TechHit(
                    surface=surface,
                    canonical=rec.canonical,
                    taxonomy_id=rec.tech_id,
                    start=start,
                    end=end,
                    matching_policy=rec.policy,
                    match_type="SLASH_ALIAS",
                    source="FULL_TEXT_RECOVERY",
                )
            )

    # 1) Slash compounds: Python/Django, Git/Bitbucket, PLSQL/Oracle
    for m in re.finditer(r"[\w+#.][\w+#./_-]*(?:/[\w+#./_-]+)+", text):
        compound = m.group(0)
        base = m.start()
        pieces: list[tuple[str, int, int]] = []
        offset = 0
        for part in compound.split("/"):
            if not part:
                offset += 1
                continue
            a, b = base + offset, base + offset + len(part)
            pieces.append((part, a, b))
            offset += len(part) + 1
        pieces.append((compound, m.start(), m.end()))
        siblings = [(a, b) for _, a, b in pieces]
        local = occupied + siblings
        for surface, start, end in pieces:
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            rec, _mt = lookup_exact(surface, idx)
            if rec is None or not _try_accept(surface, rec, text, start, end, local):
                continue
            occupied.append((start, end))
            hits.append(
                TechHit(
                    surface=surface,
                    canonical=rec.canonical,
                    taxonomy_id=rec.tech_id,
                    start=start,
                    end=end,
                    matching_policy=rec.policy,
                    match_type="SLASH_COMPOUND",
                    source="FULL_TEXT_RECOVERY",
                )
            )

    toks = _tokenize(text)
    i = 0
    while i < len(toks):
        node = idx.trie
        j = i
        best: tuple[int, TechRec] | None = None
        while j < len(toks):
            nxt = node.children.get(toks[j][0].lower())
            if nxt is None:
                break
            node = nxt
            if node.terminal:
                rec = sorted(node.terminal, key=lambda r: (len(r.alias), r.alias), reverse=True)[0]
                best = (j, rec)
            j += 1
        if best is None:
            i += 1
            continue
        end_idx, rec = best
        start, end = toks[i][1], toks[end_idx][2]
        if not _is_boundary(text, start, end):
            i += 1
            continue
        if any(not (end <= a or start >= b) for a, b in occupied):
            i += 1
            continue
        surface = text[start:end]
        if not _try_accept(surface, rec, text, start, end, occupied):
            i += 1
            continue
        occupied.append((start, end))
        hits.append(
            TechHit(
                surface=surface,
                canonical=rec.canonical,
                taxonomy_id=rec.tech_id,
                start=start,
                end=end,
                matching_policy=rec.policy,
                match_type="TRIE_EXACT",
                source="FULL_TEXT_RECOVERY",
            )
        )
        i = end_idx + 1

    by_id: dict[str, TechHit] = {}
    for h in hits:
        h.source_text = source_text
        if h.taxonomy_id not in by_id:
            by_id[h.taxonomy_id] = h
    return list(by_id.values())
