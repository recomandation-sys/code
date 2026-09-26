"""Consolidate the canonical taxonomy to the eight approved IT families.

The five non-technical top-level groups are either reassigned to the nearest
approved technical family or archived as excluded scope. Original IDs and
excluded title mappings are preserved in taxonomy_v2_excluded_* tables.
"""

from __future__ import annotations

import csv
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from apply_taxonomy_v2_evidence_migration import apply as apply_evidence_layer


KB_ROOT = Path(__file__).resolve().parents[1]
DB = KB_ROOT / "it_knowledge.sqlite"
REPORT_DIR = KB_ROOT.parent / "artifacts" / "reports"
VERSION = "IT_KB_2.5.1_MANAGEMENT_ABSTENTION"

FAMILIES = {
    "ARCHITECTURE_ANALYSIS": ("Architecture and Systems Analysis", "Requirements, solution/system design, technical architecture and analysis."),
    "COMPUTER_HARDWARE": ("Computer Hardware", "Physical computing systems, embedded/computer hardware and hardware engineering."),
    "DATA_AI": ("Data, Analytics and AI", "Data platforms, databases, analytics, data science and AI/ML engineering."),
    "NETWORKS": ("Networks and Telecommunications", "Enterprise networking, communications and telecommunications."),
    "PLATFORM_INFRASTRUCTURE": ("Cloud, Platforms and IT Operations", "Cloud platforms, DevOps/platform engineering and systems operations."),
    "SECURITY": ("Cybersecurity", "Security engineering, operations, governance and offensive security."),
    "SOFTWARE": ("Software Engineering", "Application/software development, specialized development and software quality/testing."),
    "SUPPORT": ("IT Support", "End-user, application and hardware support."),
}

# Parent-level mapping is safer than assigning the whole old family to one
# target. It keeps project/product roles separate from service operations.
PARENT_TARGETS = {
    "DIGITAL_EXPERIENCE": ("SOFTWARE", "Digital product design is retained as a software-adjacent parent."),
    "DOMAIN_INFORMATICS": ("DATA_AI", "Domain informatics is data/analytics-led."),
    "OPERATIONAL_TECHNOLOGY": ("PLATFORM_INFRASTRUCTURE", "OT/SCADA is platform and operational infrastructure."),
    "IT_MANAGEMENT": ("PLATFORM_INFRASTRUCTURE", "IT operations and service leadership are infrastructure governance."),
    "AGILE_PRODUCT_AND_PROJECT_DELIVERY": ("SOFTWARE", "The retained product/project parent is a functional agile delivery domain."),
    "SERVICE_GOVERNANCE": ("PLATFORM_INFRASTRUCTURE", "Service governance belongs with IT operations."),
    "TECHNICAL_ENABLEMENT": ("SUPPORT", "Technical enablement is user/customer support and enablement."),
}

EXCLUDED_FAMILY = "EXCLUSIONS"


DDL = """
CREATE TABLE IF NOT EXISTS taxonomy_v2_excluded_node (
    old_family_id TEXT NOT NULL, old_family_label TEXT NOT NULL,
    old_parent_id TEXT NOT NULL, old_parent_label TEXT NOT NULL,
    old_leaf_id TEXT NOT NULL, old_leaf_label TEXT NOT NULL,
    old_scope TEXT NOT NULL, old_status TEXT NOT NULL,
    exclusion_reason TEXT NOT NULL, archived_at TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    PRIMARY KEY(old_family_id,old_parent_id,old_leaf_id)
);
CREATE TABLE IF NOT EXISTS taxonomy_v2_excluded_title (
    title_id TEXT NOT NULL, title TEXT NOT NULL, old_family_id TEXT NOT NULL,
    old_parent_id TEXT NOT NULL, old_leaf_id TEXT NOT NULL, method TEXT NOT NULL,
    rule_id TEXT NOT NULL, review_status TEXT NOT NULL, exclusion_reason TEXT NOT NULL,
    archived_at TEXT NOT NULL, taxonomy_version TEXT NOT NULL,
    PRIMARY KEY(title_id,old_leaf_id)
);
"""


def _archive_and_consolidate() -> dict[str, int]:
    backup = DB.with_name("it_knowledge.sqlite.pre_eight_family_consolidation.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB)
    # SQLite cannot update a composite parent key while children still point
    # at the old value. Disable enforcement only for this short, backed-up
    # rewrite, then run a full foreign-key check before returning.
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        with con:
            con.executescript(DDL)

            con.execute("""
                INSERT OR IGNORE INTO taxonomy_v2_excluded_node
                SELECT f.family_id,f.label,p.parent_id,p.label,l.leaf_id,l.label,l.scope,l.status,
                       'Excluded/non-occupational scope; not part of the eight-family production taxonomy.',?,?
                FROM family f JOIN parent p ON p.family_id=f.family_id JOIN leaf l ON l.parent_id=p.parent_id
                WHERE f.family_id=?
            """, (now, VERSION, EXCLUDED_FAMILY))
            con.execute("""
                INSERT OR IGNORE INTO taxonomy_v2_excluded_title
                SELECT tc.title_id,i.title,tc.family_id,tc.parent_id,tc.leaf_id,tc.method,tc.rule_id,tc.review_status,
                       'Excluded/non-occupational title; retained for audit only.',?,?
                FROM title_classification tc JOIN input_title i USING(title_id)
                WHERE tc.family_id=?
            """, (now, VERSION, EXCLUDED_FAMILY))

            # Preserve an explicit crosswalk for every moved parent and old family.
            for parent_id, (target_family, rationale) in PARENT_TARGETS.items():
                con.execute(
                    """INSERT OR IGNORE INTO taxonomy_v2_crosswalk
                       (old_level,old_id,new_level,new_id,relation,rationale,taxonomy_version)
                       VALUES('parent',?,?,?, ?,?,?)""",
                    (parent_id, "parent", parent_id, "reassigned_parent", rationale, VERSION),
                )
            old_family_targets = {
                "DIGITAL_DESIGN": {"SOFTWARE"},
                "IT_DELIVERY": {"SOFTWARE", "PLATFORM_INFRASTRUCTURE"},
                "IT_ENABLEMENT": {"SUPPORT"},
                "SPECIALIZED_IT": {"DATA_AI", "PLATFORM_INFRASTRUCTURE"},
                "EXCLUSIONS": set(),
            }
            for old_family, targets in old_family_targets.items():
                for target in targets:
                    con.execute(
                        """INSERT OR IGNORE INTO taxonomy_v2_crosswalk
                           (old_level,old_id,new_level,new_id,relation,rationale,taxonomy_version)
                           VALUES('family',?,'family',?,?,?,?)""",
                        (old_family, target, "reassigned_by_parent", "Parent-level mapping; no one-to-one family mapping exists.", VERSION),
                    )
                if old_family == EXCLUDED_FAMILY:
                    con.execute(
                        """INSERT OR IGNORE INTO taxonomy_v2_crosswalk
                           (old_level,old_id,new_level,new_id,relation,rationale,taxonomy_version)
                           VALUES('family',?,'role_track','EXCLUDED','archived_scope',?,?)""",
                        (old_family, "Excluded records remain available only in audit tables.", VERSION),
                    )

            # Remove excluded mappings and profile rows before deleting excluded
            # leaves. The records remain in taxonomy_v2_excluded_* for audit.
            con.execute("DELETE FROM leaf_title_evidence WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM leaf_confusion_pair WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node) OR sibling_leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM leaf_profile WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM leaf_source_occupation WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM leaf_alias WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM leaf_task_evidence WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM leaf_skill_profile WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM leaf_technology_profile WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM title_classification WHERE family_id=?", (EXCLUDED_FAMILY,))
            con.execute("DELETE FROM occupation_classification WHERE family_id=?", (EXCLUDED_FAMILY,))

            # Reparent the old non-technical parents while foreign keys are
            # deferred. Then update every composite classification reference.
            for parent_id, (target_family, _) in PARENT_TARGETS.items():
                con.execute("UPDATE parent SET family_id=? WHERE parent_id=?", (target_family, parent_id))
                con.execute("UPDATE occupation_classification SET family_id=? WHERE parent_id=?", (target_family, parent_id))
                con.execute("UPDATE title_classification SET family_id=? WHERE parent_id=?", (target_family, parent_id))
                con.execute("UPDATE document_role SET family_id=? WHERE parent_id=?", (target_family, parent_id))

            old_families = set(PARENT_TARGETS)  # only used as a named set below
            con.execute("DELETE FROM family_role_track WHERE family_id NOT IN ({})".format(",".join("?" for _ in ("ARCHITECTURE_ANALYSIS","COMPUTER_HARDWARE","DATA_AI","NETWORKS","PLATFORM_INFRASTRUCTURE","SECURITY","SOFTWARE","SUPPORT"))), ("ARCHITECTURE_ANALYSIS","COMPUTER_HARDWARE","DATA_AI","NETWORKS","PLATFORM_INFRASTRUCTURE","SECURITY","SOFTWARE","SUPPORT"))
            con.execute("DELETE FROM leaf WHERE leaf_id IN (SELECT old_leaf_id FROM taxonomy_v2_excluded_node)")
            con.execute("DELETE FROM parent WHERE parent_id IN ('NON_OCCUPATIONAL_LABEL','OUTSIDE_SCOPE')")
            con.execute("DELETE FROM family WHERE family_id=?", (EXCLUDED_FAMILY,))
            for old_family in ("DIGITAL_DESIGN", "IT_DELIVERY", "IT_ENABLEMENT", "SPECIALIZED_IT"):
                con.execute("DELETE FROM family WHERE family_id=?", (old_family,))

            con.executemany(
                "UPDATE family SET label=?,definition=?,taxonomy_version=? WHERE family_id=?",
                [(label, definition, VERSION, family_id) for family_id, (label, definition) in FAMILIES.items()],
            )
            con.execute("UPDATE leaf_profile SET taxonomy_version=?", (VERSION,))
            con.execute("UPDATE role_track SET taxonomy_version=?", (VERSION,))
            con.execute("UPDATE taxonomy_v2_crosswalk SET taxonomy_version=?", (VERSION,))
            con.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    ("taxonomy_version", VERSION),
                    ("taxonomy_v2_version", VERSION),
                    ("taxonomy_v2_family_policy", "Canonical output is restricted to eight approved technical families."),
                    ("taxonomy_v2_excluded_policy", "Excluded/non-occupational labels are archived outside the canonical hierarchy."),
                    ("taxonomy_v2_eight_family_applied_at", now),
                ],
            )
            con.execute("PRAGMA user_version=111")
        con.execute("PRAGMA foreign_keys=ON")
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign-key violations after consolidation: {violations[:5]}")
        return {
            "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
            "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
            "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
            "excluded_nodes": con.execute("SELECT count(*) FROM taxonomy_v2_excluded_node").fetchone()[0],
            "excluded_titles": con.execute("SELECT count(*) FROM taxonomy_v2_excluded_title").fetchone()[0],
        }
    finally:
        con.close()


def _write_eight_family_template() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "taxonomy_v2_leaf_enrichment_template_eight_families.csv"
    con = sqlite3.connect(DB)
    try:
        rows = con.execute("""
            SELECT f.family_id,p.parent_id,l.leaf_id,l.label,l.definition,'','','[]','[]','[]','[]','[]','[]','','REVIEW_REQUIRED',''
            FROM leaf l JOIN parent p ON p.parent_id=l.parent_id JOIN family f ON f.family_id=p.family_id
            ORDER BY f.family_id,p.parent_id,l.leaf_id
        """).fetchall()
    finally:
        con.close()
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["family_id","parent_id","leaf_id","leaf_label","current_definition","source_ids_to_add","primary_outcome","in_scope_json","out_of_scope_json","task_signatures_json","skill_ids_json","technology_ids_json","confusion_pairs_json","reviewer","review_status","evidence_urls_or_ids"])
        writer.writerows(rows)


def apply() -> dict[str, int]:
    # Ensure the evidence/profile layer exists before consolidation.
    con = sqlite3.connect(DB)
    has_profile = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='leaf_profile'").fetchone()[0]
    con.close()
    if not has_profile:
        apply_evidence_layer()
    result = _archive_and_consolidate()
    # Rebuild current reports against the reduced canonical hierarchy.
    apply_evidence_layer()
    con = sqlite3.connect(DB)
    with con:
        con.execute("UPDATE metadata SET value=? WHERE key IN ('taxonomy_version','taxonomy_v2_version')", (VERSION,))
        con.execute("INSERT INTO metadata(key,value) VALUES('taxonomy_v2_family_policy',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("Canonical output is restricted to eight approved technical families.",))
        con.execute("UPDATE leaf_profile SET taxonomy_version=?", (VERSION,))
        con.execute("UPDATE role_track SET taxonomy_version=?", (VERSION,))
        con.execute("UPDATE taxonomy_v2_crosswalk SET taxonomy_version=?", (VERSION,))
        con.execute("PRAGMA user_version=111")
    con.close()
    _write_eight_family_template()
    return result


if __name__ == "__main__":
    print(json.dumps(apply(), indent=2))
