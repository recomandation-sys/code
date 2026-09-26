"""Apply the non-destructive IT_KB_2.0.0 evidence/profile layer.

The existing family/parent/leaf taxonomy and runtime mappings are preserved.
This migration only adds provenance tables, role tracks, derived evidence rows,
and CSV readiness reports.  It never invents a source mapping or task/skill
relationship.
"""

from __future__ import annotations

import csv
import json
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]  # job_nlp/knowledge_base
DB = ROOT / "it_knowledge.sqlite"
REPORT_DIR = ROOT.parent / "artifacts" / "reports"
VERSION = "IT_KB_2.5.1_MANAGEMENT_ABSTENTION"


DDL = """
CREATE TABLE IF NOT EXISTS role_track (
    track_id TEXT PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    definition TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','conditional','excluded')),
    taxonomy_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS family_role_track (
    family_id TEXT NOT NULL REFERENCES family,
    track_id TEXT NOT NULL REFERENCES role_track,
    relation TEXT NOT NULL,
    rationale TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    PRIMARY KEY(family_id, track_id)
);
CREATE TABLE IF NOT EXISTS leaf_profile (
    leaf_id TEXT PRIMARY KEY REFERENCES leaf,
    taxonomy_version TEXT NOT NULL,
    definition TEXT NOT NULL,
    primary_outcome TEXT NOT NULL DEFAULT '',
    in_scope_json TEXT NOT NULL CHECK(json_valid(in_scope_json)),
    out_of_scope_json TEXT NOT NULL CHECK(json_valid(out_of_scope_json)),
    profile_status TEXT NOT NULL CHECK(profile_status IN ('ACTIVE','CONDITIONAL','REVIEW_ONLY','MARKET_DERIVED')),
    evidence_level TEXT NOT NULL CHECK(evidence_level IN ('SOURCE_MAPPED_PROPOSAL','NONE','MARKET_DERIVED')),
    readiness_reason TEXT NOT NULL,
    reviewer TEXT NOT NULL DEFAULT '',
    reviewed_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS leaf_source_occupation (
    leaf_id TEXT NOT NULL REFERENCES leaf,
    occupation_id TEXT NOT NULL REFERENCES occupation,
    source_id TEXT NOT NULL REFERENCES source,
    native_id TEXT NOT NULL,
    preferred_label TEXT NOT NULL,
    mapping_relation TEXT NOT NULL,
    mapping_method TEXT NOT NULL,
    review_status TEXT NOT NULL,
    evidence_id TEXT REFERENCES evidence,
    PRIMARY KEY(leaf_id, occupation_id)
);
CREATE TABLE IF NOT EXISTS leaf_alias (
    leaf_id TEXT NOT NULL REFERENCES leaf,
    alias_id TEXT NOT NULL REFERENCES occupation_alias,
    source_id TEXT NOT NULL REFERENCES source,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    evidence_id TEXT REFERENCES evidence,
    provenance TEXT NOT NULL DEFAULT 'source_occupation_alias',
    PRIMARY KEY(leaf_id, alias_id)
);
CREATE TABLE IF NOT EXISTS leaf_task_evidence (
    leaf_id TEXT NOT NULL REFERENCES leaf,
    occupation_id TEXT NOT NULL REFERENCES occupation,
    task_id TEXT NOT NULL REFERENCES task,
    source_id TEXT NOT NULL REFERENCES source,
    task_type TEXT,
    description TEXT NOT NULL,
    verb TEXT NOT NULL DEFAULT '',
    object_text TEXT NOT NULL DEFAULT '',
    context_text TEXT NOT NULL DEFAULT '',
    evidence_tier TEXT NOT NULL DEFAULT 'source_occupation_task',
    evidence_id TEXT NOT NULL REFERENCES evidence,
    PRIMARY KEY(leaf_id, occupation_id, task_id)
);
CREATE TABLE IF NOT EXISTS leaf_skill_profile (
    leaf_id TEXT NOT NULL REFERENCES leaf,
    occupation_id TEXT NOT NULL REFERENCES occupation,
    skill_id TEXT NOT NULL REFERENCES skill,
    source_id TEXT NOT NULL REFERENCES source,
    normalized_label TEXT NOT NULL,
    kind TEXT NOT NULL,
    relation TEXT NOT NULL,
    hot_technology INTEGER,
    in_demand INTEGER,
    evidence_tier TEXT NOT NULL DEFAULT 'source_occupation_skill',
    evidence_id TEXT NOT NULL REFERENCES evidence,
    PRIMARY KEY(leaf_id, occupation_id, skill_id, relation)
);
CREATE TABLE IF NOT EXISTS leaf_technology_profile (
    leaf_id TEXT NOT NULL REFERENCES leaf,
    occupation_id TEXT NOT NULL REFERENCES occupation,
    skill_id TEXT NOT NULL REFERENCES skill,
    source_id TEXT NOT NULL REFERENCES source,
    technology_label TEXT NOT NULL,
    relation TEXT NOT NULL,
    role_context TEXT NOT NULL DEFAULT 'source_occupation_context',
    evidence_id TEXT NOT NULL REFERENCES evidence,
    PRIMARY KEY(leaf_id, occupation_id, skill_id, relation)
);
CREATE TABLE IF NOT EXISTS leaf_confusion_pair (
    pair_id TEXT PRIMARY KEY,
    leaf_id TEXT NOT NULL REFERENCES leaf,
    sibling_leaf_id TEXT NOT NULL REFERENCES leaf,
    disambiguator TEXT NOT NULL,
    hard_negative_rule TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    reviewer TEXT NOT NULL DEFAULT '',
    review_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
    CHECK(leaf_id <> sibling_leaf_id)
);
CREATE TABLE IF NOT EXISTS leaf_title_evidence (
    title_id TEXT NOT NULL REFERENCES input_title,
    leaf_id TEXT NOT NULL REFERENCES leaf,
    title TEXT NOT NULL,
    method TEXT NOT NULL,
    review_status TEXT NOT NULL,
    evidence_strength TEXT NOT NULL DEFAULT 'title_classification_only',
    evidence_quote TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    PRIMARY KEY(title_id, leaf_id)
);
CREATE TABLE IF NOT EXISTS taxonomy_v2_crosswalk (
    old_level TEXT NOT NULL CHECK(old_level IN ('family','parent','leaf')),
    old_id TEXT NOT NULL,
    new_level TEXT NOT NULL CHECK(new_level IN ('family','parent','leaf','role_track')),
    new_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    rationale TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    PRIMARY KEY(old_level, old_id, new_level, new_id)
);
CREATE TABLE IF NOT EXISTS taxonomy_v2_excluded_node (
    old_family_id TEXT NOT NULL,
    old_family_label TEXT NOT NULL,
    old_parent_id TEXT NOT NULL,
    old_parent_label TEXT NOT NULL,
    old_leaf_id TEXT NOT NULL,
    old_leaf_label TEXT NOT NULL,
    old_scope TEXT NOT NULL,
    old_status TEXT NOT NULL,
    exclusion_reason TEXT NOT NULL,
    archived_at TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    PRIMARY KEY(old_family_id, old_parent_id, old_leaf_id)
);
CREATE TABLE IF NOT EXISTS taxonomy_v2_excluded_title (
    title_id TEXT NOT NULL,
    title TEXT NOT NULL,
    old_family_id TEXT NOT NULL,
    old_parent_id TEXT NOT NULL,
    old_leaf_id TEXT NOT NULL,
    method TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    review_status TEXT NOT NULL,
    exclusion_reason TEXT NOT NULL,
    archived_at TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    PRIMARY KEY(title_id, old_leaf_id)
);
CREATE INDEX IF NOT EXISTS leaf_source_occupation_source_idx ON leaf_source_occupation(source_id);
CREATE INDEX IF NOT EXISTS leaf_task_evidence_task_idx ON leaf_task_evidence(task_id);
CREATE INDEX IF NOT EXISTS leaf_skill_profile_skill_idx ON leaf_skill_profile(skill_id);
CREATE INDEX IF NOT EXISTS leaf_title_evidence_leaf_idx ON leaf_title_evidence(leaf_id);
CREATE VIEW IF NOT EXISTS v_leaf_evidence_summary AS
WITH so AS (SELECT leaf_id,COUNT(DISTINCT occupation_id) n,GROUP_CONCAT(DISTINCT source_id) sources FROM leaf_source_occupation GROUP BY leaf_id),
     te AS (SELECT leaf_id,COUNT(DISTINCT task_id) n FROM leaf_task_evidence GROUP BY leaf_id),
     sp AS (SELECT leaf_id,COUNT(DISTINCT skill_id) n FROM leaf_skill_profile GROUP BY leaf_id),
     tp AS (SELECT leaf_id,COUNT(DISTINCT skill_id) n FROM leaf_technology_profile GROUP BY leaf_id),
     ti AS (SELECT leaf_id,COUNT(DISTINCT title_id) n FROM leaf_title_evidence GROUP BY leaf_id),
     cp AS (SELECT leaf_id,COUNT(DISTINCT pair_id) n FROM leaf_confusion_pair GROUP BY leaf_id)
SELECT l.leaf_id,p.parent_id,pa.family_id,
       COALESCE(so.n,0) source_occupation_count,COALESCE(te.n,0) task_count,
       COALESCE(sp.n,0) skill_count,COALESCE(tp.n,0) technology_count,
       COALESCE(ti.n,0) reviewed_title_count,COALESCE(cp.n,0) confusion_pair_count,
       so.sources source_ids
FROM leaf l JOIN parent p ON p.parent_id=l.parent_id JOIN family pa ON pa.family_id=p.family_id
LEFT JOIN so ON so.leaf_id=l.leaf_id LEFT JOIN te ON te.leaf_id=l.leaf_id
LEFT JOIN sp ON sp.leaf_id=l.leaf_id LEFT JOIN tp ON tp.leaf_id=l.leaf_id
LEFT JOIN ti ON ti.leaf_id=l.leaf_id LEFT JOIN cp ON cp.leaf_id=l.leaf_id;
"""


ROLE_TRACKS = [
    ("DIGITAL_PRODUCT_DESIGN", "Digital Product Design", "Design and research of digital products and interfaces.", "active"),
    ("DELIVERY_GOVERNANCE", "Delivery and Governance", "Project, product, service, quality and IT governance work.", "active"),
    ("TECHNICAL_ENABLEMENT", "Technical Enablement", "Training, documentation, knowledge and customer enablement.", "active"),
    ("SPECIALIZED_INFORMATICS", "Specialized Informatics", "IT capabilities applied to a domain such as health, GIS or OT.", "conditional"),
    ("EXCLUDED", "Excluded Scope", "Non-occupational labels or records outside the IT occupation scope.", "excluded"),
]

FAMILY_TRACKS = {
    "DIGITAL_DESIGN": ("DIGITAL_PRODUCT_DESIGN", "Cross-functional design track; not a technical family."),
    "IT_DELIVERY": ("DELIVERY_GOVERNANCE", "Cross-functional delivery and governance track."),
    "IT_ENABLEMENT": ("TECHNICAL_ENABLEMENT", "Cross-functional technical enablement track."),
    "SPECIALIZED_IT": ("SPECIALIZED_INFORMATICS", "Domain facet for specialized informatics roles."),
    "EXCLUSIONS": ("EXCLUDED", "Scope status; never an autonomous IT occupation family."),
}


def _count_map(connection: sqlite3.Connection, query: str) -> dict[str, int]:
    return {str(k): int(v) for k, v in connection.execute(query)}


def apply() -> dict[str, int]:
    if not DB.exists():
        raise FileNotFoundError(DB)
    backup = DB.with_name("it_knowledge.sqlite.pre_taxonomy_v2_evidence.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    try:
        with con:
            con.executescript(DDL)
            con.executemany(
                "INSERT OR IGNORE INTO role_track(track_id,label,definition,status,taxonomy_version) VALUES(?,?,?,?,?)",
                [(a, b, c, d, VERSION) for a, b, c, d in ROLE_TRACKS],
            )
            existing_families = {r[0] for r in con.execute("SELECT family_id FROM family")}
            con.executemany(
                "INSERT OR IGNORE INTO family_role_track(family_id,track_id,relation,rationale,taxonomy_version) VALUES(?,?,?,?,?)",
                [(family, track, "orthogonal_track", rationale, VERSION) for family, (track, rationale) in FAMILY_TRACKS.items() if family in existing_families],
            )

            # All migration tables are append-only.  This makes a rerun safe
            # after a human reviewer has enriched a profile or confusion pair.

            con.execute(
                """INSERT OR IGNORE INTO leaf_source_occupation
                SELECT oc.leaf_id,o.occupation_id,o.source_id,o.native_id,o.preferred_label,
                       oc.mapping_relation,oc.method,oc.review_status,o.evidence_id
                FROM occupation_classification oc JOIN occupation o USING(occupation_id)
                WHERE oc.leaf_id IS NOT NULL"""
            )
            con.execute(
                """INSERT OR IGNORE INTO leaf_alias
                SELECT DISTINCT oc.leaf_id,oa.alias_id,o.source_id,oa.label,oa.alias_type,oa.evidence_id,
                       'source_occupation_alias'
                FROM occupation_classification oc
                JOIN occupation_alias oa USING(occupation_id)
                JOIN occupation o USING(occupation_id)
                WHERE oc.leaf_id IS NOT NULL"""
            )
            con.execute(
                """INSERT OR IGNORE INTO leaf_task_evidence
                SELECT oc.leaf_id,ot.occupation_id,ot.task_id,t.source_id,ot.task_type,t.description,
                       '','','','source_occupation_task',ot.evidence_id
                FROM occupation_task ot
                JOIN task t USING(task_id)
                JOIN occupation_classification oc USING(occupation_id)
                WHERE oc.leaf_id IS NOT NULL"""
            )
            con.execute(
                """INSERT OR IGNORE INTO leaf_skill_profile
                SELECT oc.leaf_id,os.occupation_id,os.skill_id,s.source_id,s.normalized_label,s.kind,
                       os.relation,os.hot_technology,os.in_demand,'source_occupation_skill',os.evidence_id
                FROM occupation_skill os
                JOIN skill s USING(skill_id)
                JOIN occupation_classification oc USING(occupation_id)
                WHERE oc.leaf_id IS NOT NULL"""
            )
            con.execute(
                """INSERT OR IGNORE INTO leaf_technology_profile
                SELECT oc.leaf_id,os.occupation_id,os.skill_id,s.source_id,s.preferred_label,
                       os.relation,'source_occupation_context',os.evidence_id
                FROM occupation_skill os
                JOIN skill s USING(skill_id)
                JOIN occupation_classification oc USING(occupation_id)
                WHERE oc.leaf_id IS NOT NULL AND s.kind IN ('technology','software_example')"""
            )
            con.execute(
                """INSERT OR IGNORE INTO leaf_title_evidence
                SELECT tc.title_id,tc.leaf_id,i.title,tc.method,tc.review_status,
                       'title_classification_only',i.title,?
                FROM title_classification tc JOIN input_title i USING(title_id)
                WHERE tc.leaf_id IS NOT NULL""",
                (VERSION,),
            )

            # Identity crosswalk preserves every current ID. Track mappings are additive.
            con.executemany(
                "INSERT OR IGNORE INTO taxonomy_v2_crosswalk VALUES(?,?,?,?,?,?,?)",
                [("family", r[0], "family", r[0], "identity", "Existing family retained.", VERSION) for r in con.execute("SELECT family_id FROM family")]
                + [("parent", r[0], "parent", r[0], "identity", "Existing parent retained.", VERSION) for r in con.execute("SELECT parent_id FROM parent")]
                + [("leaf", r[0], "leaf", r[0], "identity", "Existing leaf ID retained; evidence status is separate.", VERSION) for r in con.execute("SELECT leaf_id FROM leaf")]
                + [("family", family, "role_track", track, "orthogonal_track", rationale, VERSION) for family, (track, rationale) in FAMILY_TRACKS.items()]
            )

            rows = con.execute("SELECT leaf_id,label,definition,scope,status FROM leaf ORDER BY leaf_id").fetchall()
            count_queries = {
                "source_occupation_count": "SELECT leaf_id,COUNT(DISTINCT occupation_id) FROM leaf_source_occupation GROUP BY leaf_id",
                "task_count": "SELECT leaf_id,COUNT(DISTINCT task_id) FROM leaf_task_evidence GROUP BY leaf_id",
                "skill_count": "SELECT leaf_id,COUNT(DISTINCT skill_id) FROM leaf_skill_profile GROUP BY leaf_id",
                "technology_count": "SELECT leaf_id,COUNT(DISTINCT skill_id) FROM leaf_technology_profile GROUP BY leaf_id",
                "reviewed_title_count": "SELECT leaf_id,COUNT(DISTINCT title_id) FROM leaf_title_evidence GROUP BY leaf_id",
                "confusion_pair_count": "SELECT leaf_id,COUNT(DISTINCT pair_id) FROM leaf_confusion_pair GROUP BY leaf_id",
            }
            counts = {name: _count_map(con, query) for name, query in count_queries.items()}
            profiles = []
            readiness = []
            for r in rows:
                values = {name: counts[name].get(r["leaf_id"], 0) for name in counts}
                missing = []
                if values["source_occupation_count"] < 1:
                    missing.append("source occupation mapping")
                if values["task_count"] < 5:
                    missing.append("5 task signatures")
                if values["skill_count"] < 10:
                    missing.append("10 source skills/knowledge records")
                if values["technology_count"] < 5:
                    missing.append("5 technology anchors or a reviewed technology-free rationale")
                if values["reviewed_title_count"] < 5:
                    missing.append("5 reviewed title examples")
                if values["confusion_pair_count"] < 3:
                    missing.append("3 sibling confusion pairs")
                profile_status = "CONDITIONAL" if values["source_occupation_count"] else "REVIEW_ONLY"
                evidence_level = "SOURCE_MAPPED_PROPOSAL" if values["source_occupation_count"] else "NONE"
                reason = "Ready gates missing: " + ", ".join(missing) if missing else "All structural gates present; human review still required."
                profiles.append((r["leaf_id"], VERSION, r["definition"], "", "[]", "[]", profile_status, evidence_level, reason, "", ""))
                readiness.append({
                    "leaf_id": r["leaf_id"],
                    "label": r["label"],
                    **values,
                    "profile_status": profile_status,
                    "evidence_level": evidence_level,
                    "missing": missing,
                })
            con.executemany("INSERT OR IGNORE INTO leaf_profile VALUES(?,?,?,?,?,?,?,?,?,?,?)", profiles)
            con.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    ("taxonomy_v2_version", VERSION),
                    ("taxonomy_v2_migration_status", "applied_non_destructively"),
                    ("taxonomy_v2_applied_at", now),
                    ("taxonomy_v2_leaf_policy", "No leaf is ACTIVE without an evidence card and human review."),
                ],
            )
            con.execute("PRAGMA user_version = 110")

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        with (REPORT_DIR / "taxonomy_v2_leaf_readiness.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(readiness[0]))
            writer.writeheader()
            for row in readiness:
                row = dict(row)
                row["missing"] = " | ".join(row["missing"])
                writer.writerow(row)
        with (REPORT_DIR / "taxonomy_v2_leaf_source_provenance.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["leaf_id", "occupation_id", "source_id", "native_id", "preferred_label", "mapping_relation", "mapping_method", "review_status", "evidence_id"])
            writer.writerows(con.execute("SELECT leaf_id,occupation_id,source_id,native_id,preferred_label,mapping_relation,mapping_method,review_status,evidence_id FROM leaf_source_occupation ORDER BY leaf_id,source_id,native_id"))
        template_path = REPORT_DIR / "taxonomy_v2_leaf_enrichment_template_residual_taxonomy.csv"
        if not template_path.exists():
            with template_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    "family_id", "parent_id", "leaf_id", "leaf_label", "current_definition",
                    "source_ids_to_add", "primary_outcome", "in_scope_json", "out_of_scope_json",
                    "task_signatures_json", "skill_ids_json", "technology_ids_json",
                    "confusion_pairs_json", "reviewer", "review_status", "evidence_urls_or_ids",
                ])
                writer.writerows(con.execute("""
                    SELECT f.family_id,p.parent_id,l.leaf_id,l.label,l.definition,
                           '', '', '[]', '[]', '[]', '[]', '[]', '[]', '', 'REVIEW_REQUIRED', ''
                    FROM leaf l JOIN parent p ON p.parent_id=l.parent_id JOIN family f ON f.family_id=p.family_id
                    ORDER BY f.family_id,p.parent_id,l.leaf_id
                """))

        con.row_factory = None
        return {
            "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
            "profiles": con.execute("SELECT count(*) FROM leaf_profile").fetchone()[0],
            "source_mapped_leaves": con.execute("SELECT count(*) FROM leaf_profile WHERE evidence_level='SOURCE_MAPPED_PROPOSAL'").fetchone()[0],
            "review_only_leaves": con.execute("SELECT count(*) FROM leaf_profile WHERE profile_status='REVIEW_ONLY'").fetchone()[0],
            "source_occupation_links": con.execute("SELECT count(*) FROM leaf_source_occupation").fetchone()[0],
            "task_evidence_rows": con.execute("SELECT count(*) FROM leaf_task_evidence").fetchone()[0],
            "skill_evidence_rows": con.execute("SELECT count(*) FROM leaf_skill_profile").fetchone()[0],
            "technology_evidence_rows": con.execute("SELECT count(*) FROM leaf_technology_profile").fetchone()[0],
        }
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(apply(), indent=2))
