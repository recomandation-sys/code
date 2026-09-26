"""Phase 1 builder for the job_nlp-to-IT-KB leaf reassignment table."""
from __future__ import annotations

import json
import sqlite3
import csv
import difflib
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from job_nlp.paths import KNOWLEDGE_BASE_DIR, TAXONOMY_JSON
from job_nlp.taxonomy.engine import collect_candidates, rank_candidates

KB_PATH = KNOWLEDGE_BASE_DIR / "it_knowledge.sqlite"

@lru_cache(maxsize=1)
def _crosswalk() -> dict[str, tuple[str, str, str]]:
    """Return only exact canonical leaf-ID matches; unmatched leaves abstain."""
    entries = json.loads(TAXONOMY_JSON.read_text(encoding="utf-8")).get("entries", [])
    source = {str(e.get("leaf")) for e in entries if e.get("leaf")}
    if not KB_PATH.exists(): return {}
    with sqlite3.connect(f"file:{KB_PATH.as_posix()}?mode=ro", uri=True) as db:
        rows = db.execute("SELECT l.leaf_id,l.parent_id,p.family_id FROM leaf l JOIN parent p ON p.parent_id=l.parent_id").fetchall()
    return {leaf: (parent, family, leaf) for leaf, parent, family in rows if leaf in source}

def resolve_title_crosswalk(title: str) -> tuple[str, str, str, str] | None:
    candidates = rank_candidates(collect_candidates(title))
    for candidate in candidates:
        path = _crosswalk().get(candidate.leaf)
        if path:
            parent, family, leaf = path
            return family, parent, leaf, candidate.pattern_id
    return None

def build_leaf_reassignment(db_path: Path = KB_PATH, queue_path: Path | None = None) -> dict[str, int]:
    """Seed only deterministic exact-ID/lexical matches; never auto-assign fuzzy matches."""
    entries = json.loads(TAXONOMY_JSON.read_text(encoding="utf-8")).get("entries", [])
    queue_path = queue_path or db_path.with_name("manual_review_queue.csv")
    with sqlite3.connect(db_path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS leaf_reassignment (
            job_nlp_leaf_id TEXT NOT NULL, job_nlp_pattern_id TEXT NOT NULL,
            kb_leaf_id TEXT, kb_parent_id TEXT, kb_family_id TEXT,
            method TEXT NOT NULL CHECK(method IN ('exact_id','esco_code_anchor','lexical_alias','manual')),
            confidence TEXT NOT NULL, reviewer TEXT, evidence TEXT, created_at TEXT NOT NULL,
            source_version TEXT NOT NULL, PRIMARY KEY(job_nlp_leaf_id, job_nlp_pattern_id),
            FOREIGN KEY(kb_leaf_id,kb_parent_id) REFERENCES leaf(leaf_id,parent_id)
        )""")
        leaves = {r[0]: (r[1], r[2]) for r in db.execute("SELECT l.leaf_id,l.parent_id,p.family_id FROM leaf l JOIN parent p ON p.parent_id=l.parent_id")}
        aliases: dict[str, set[str]] = {}
        for leaf, in db.execute("SELECT leaf_id FROM leaf"):
            aliases.setdefault(leaf, set()).add(leaf)
        for leaf, label in db.execute("SELECT leaf_id,label FROM leaf"):
            aliases.setdefault(leaf, set()).add(label)
        for leaf, label in db.execute("""SELECT c.leaf_id,a.label FROM occupation_alias a JOIN occupation_classification c USING(occupation_id) WHERE c.leaf_id IS NOT NULL"""):
            aliases.setdefault(leaf, set()).add(label)
        def norm(s: str) -> str:
            return " ".join("".join(ch if ch.isalnum() else " " for ch in s.casefold()).split())
        normalized_aliases: dict[str, set[str]] = {leaf: {norm(x) for x in vals} for leaf, vals in aliases.items()}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        unresolved=[]; counts={"exact_id":0,"esco_code_anchor":0,"lexical_alias":0,"manual":0,"unresolved":0}
        for entry in entries:
            leaf, pattern = str(entry["leaf"]), str(entry.get("pattern_id") or f"{entry['parent']}.{entry['leaf']}")
            target=None; method=None; evidence=""
            if leaf in leaves:
                target=leaf; method="exact_id"; evidence="canonical leaf ID equality"
            else:
                candidates=[kb for kb, vals in normalized_aliases.items() if norm(leaf.replace("_", " ")) in vals]
                if len(candidates)==1:
                    target=candidates[0]; method="lexical_alias"; evidence="exact normalized canonical-label match"
            if target:
                parent,family=leaves[target]
                db.execute("INSERT OR REPLACE INTO leaf_reassignment VALUES (?,?,?,?,?,?,?,?,?,?,?)",(leaf,pattern,target,parent,family,method,"high" if method=="exact_id" else "medium","phase1",evidence,now,"job_family_taxonomy_v1_1"))
                counts[method]+=1
            else:
                counts["unresolved"]+=1
                labels=sorted(leaves, key=lambda x: difflib.SequenceMatcher(None,norm(leaf.replace("_"," ")),norm(x.replace("_"," "))).ratio(), reverse=True)[:3]
                unresolved.append((pattern,leaf,entry.get("parent",""),"; ".join(labels),entry.get("aliases", "")))
        db.commit()
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["job_nlp_pattern_id","job_nlp_label","job_nlp_parent_label","top_3_kb_leaf_labels","regex_example_titles"]); w.writerows(unresolved)
    (queue_path.with_name("leaf_reassignment_coverage.json")).write_text(json.dumps({"total_patterns":len(entries),**counts},indent=2),encoding="utf-8")
    return {"total_patterns":len(entries),**counts}

def import_manual_review(db_path: Path, csv_path: Path, reviewer: str) -> int:
    """Apply only reviewer-completed queue rows to the reassignment table."""
    count = 0
    with sqlite3.connect(db_path) as db, csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            leaf = (row.get("kb_leaf_id") or "").strip()
            if not leaf: continue
            path = db.execute("SELECT parent_id FROM leaf WHERE leaf_id=?", (leaf,)).fetchone()
            if not path: raise ValueError(f"unknown KB leaf: {leaf}")
            family = db.execute("SELECT family_id FROM parent WHERE parent_id=?", (path[0],)).fetchone()[0]
            db.execute("INSERT OR REPLACE INTO leaf_reassignment VALUES (?,?,?,?,?,?,?,?,?,?,?)", (row["job_nlp_leaf_id"], row["job_nlp_pattern_id"], leaf, path[0], family, "manual", "reviewed", reviewer, row.get("evidence") or "manual review", datetime.now(timezone.utc).isoformat(timespec="seconds"), "job_family_taxonomy_v1_1"))
            count += 1
        db.commit()
    return count

def export_feedback(rows: list[dict], output: Path) -> int:
    """Export UNKNOWN/conflict outputs for analyst review and later re-import."""
    fields = ["title", "description", "family", "parent", "leaf", "confidence_tier", "resolver_method", "conflict_flag", "abstention_reason", "evidence_ids"]
    output.parent.mkdir(parents=True, exist_ok=True)
    selected = [r for r in rows if r.get("conflict_flag") or str(r.get("leaf") or "UNKNOWN") == "UNKNOWN"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in selected: writer.writerow({f: row.get(f, "") for f in fields})
    return len(selected)

if __name__ == "__main__":
    print(json.dumps(build_leaf_reassignment()))
