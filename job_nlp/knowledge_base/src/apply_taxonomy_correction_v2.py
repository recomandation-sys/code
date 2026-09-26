"""Apply the reviewed taxonomy-correction-v2 workbook export to the KB."""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "it_knowledge.sqlite"
CORRECTION = ROOT.parent / "taxonomy" / "corrections" / "title_leaf_parent_family_v2_manual_complete.json"
CANONICAL_FAMILIES = {
    "ARCHITECTURE_ANALYSIS", "COMPUTER_HARDWARE", "DATA_AI", "NETWORKS",
    "PLATFORM_INFRASTRUCTURE", "SECURITY", "SOFTWARE", "SUPPORT",
}
RETIRED_LEAVES = {
    "CTO", "CIO", "CDO", "CISO", "ENGINEERING_MANAGER", "DATA_MANAGER",
    "SECURITY_MANAGER", "IT_OPERATIONS_MANAGER", "SUPPORT_MANAGER",
    "TELECOM_MANAGER", "IT_QA_MANAGER", "BUSINESS_ANALYSIS_MANAGER",
    "DOCUMENTATION_MANAGER", "IT_RESEARCH_MANAGER", "IT_MANAGER",
    "DIGITAL_TRANSFORMATION_MANAGER", "SERVICE_DELIVERY_MANAGER",
    "CHANGE_CONFIG_MANAGER", "IT_KNOWLEDGE_MANAGER",
    "COMPUTER_PROGRAMMER", "DATA_SPECIALIST_GENERAL", "SYSTEMS_SPECIALIST_GENERAL",
    # Removed generic development/security/telecom/generalist sinks. Their
    # titles are routed to functional leaves or remain parent-only by the
    # generic-leaf retirement migration.
    "APPLICATION_DEVELOPER", "SECURITY_SPECIALIST_GENERAL",
    "TELECOM_SPECIALIST_GENERAL", "IT_GENERALIST", "WEB_DEVELOPER",
    "MOBILE_DEVELOPER",
}
RETIRED_PARENTS = {
    "PROJECT_PRODUCT", "IT_MANAGEMENT", "OPERATIONAL_TECHNOLOGY",
    "CLOUD_ENGINEERING", "DEVOPS_PLATFORM", "SERVICE_GOVERNANCE", "HARDWARE_SUPPORT",
}


def apply() -> dict:
    payload = json.loads(CORRECTION.read_text(encoding="utf-8"))
    backup = DB.with_name("it_knowledge.sqlite.pre_taxonomy_correction_v2.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
    relations = payload["taxonomy_relations"]
    titles = payload["titles"]
    payload_families = {str(r["family_id"]) for r in relations}
    retired = payload_families - CANONICAL_FAMILIES
    if retired:
        raise RuntimeError(
            "Refusing to reintroduce retired family IDs: "
            + ", ".join(sorted(retired))
            + ". Use apply_eight_family_consolidation.py or a v2.1 payload."
        )
    retired_leaves = {str(r["leaf_id"]) for r in relations} & RETIRED_LEAVES
    if retired_leaves:
        raise RuntimeError(
            "Refusing to reintroduce retired leaves: "
            + ", ".join(sorted(retired_leaves))
            + ". Position/seniority is extracted independently; use functional subdomain mappings."
        )
    old_parents = {str(r["parent_id"]) for r in relations} & RETIRED_PARENTS
    if old_parents:
        raise RuntimeError(
            "Refusing retired parent IDs: " + ", ".join(sorted(old_parents))
            + "; use the current functional parent IDs."
        )
    with sqlite3.connect(DB) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN")
        try:
            # Add corrected ontology nodes while preserving existing definitions.
            for r in relations:
                db.execute(
                    "INSERT OR IGNORE INTO family(family_id,label,definition,taxonomy_version) VALUES(?,?,?,?)",
                    (r["family_id"], r["family"], f"{r['family']} occupational family.", r["taxonomy_version"]),
                )
                db.execute(
                    "INSERT OR IGNORE INTO parent(parent_id,family_id,label,definition) VALUES(?,?,?,?)",
                    (r["parent_id"], r["family_id"], r["parent"], f"IT occupational parent covering {r['parent']} roles."),
                )
                # The production schema intentionally exposes only operational
                # core/conditional leaves. Exclusion labels are retained as
                # conditional taxonomy nodes so excluded input titles remain
                # traceable without entering operational lookup.
                leaf_scope = r["scope"] if r["scope"] in {"core", "conditional"} else "conditional"
                db.execute(
                    "INSERT OR IGNORE INTO leaf(leaf_id,parent_id,label,definition,scope,status) VALUES(?,?,?,?,?,?)",
                    (r["leaf_id"], r["parent_id"], r["leaf"], f"IT occupational role: {r['leaf']}.", leaf_scope, r["status"]),
                )
            # The corrected JSON's first path is the reviewed primary path.
            db.execute("DELETE FROM title_classification")
            for title in titles:
                paths = title.get("possible_paths") or []
                if not paths:
                    raise ValueError(f"missing primary path for {title['title_id']}")
                path = paths[0]
                family_id = path["family"]["id"]
                parent_id = path["parent"]["id"]
                leaf_id = path["leaf"]["id"]
                db.execute(
                    "INSERT INTO title_classification(title_id,family_id,parent_id,leaf_id,method,rule_id,review_status) VALUES(?,?,?,?,?,?,?)",
                    (title["title_id"], family_id, parent_id, leaf_id, title["mapping_method"], "taxonomy_correction_v2", "manual_complete"),
                )
            db.execute(
                "INSERT INTO metadata(key,value) VALUES('taxonomy_correction_v2_applied_at',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (datetime.now(timezone.utc).isoformat(),),
            )
            db.execute(
                "INSERT INTO metadata(key,value) VALUES('taxonomy_version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                ("IT_KB_1.1.0_MANUAL_COMPLETE",),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"backup": str(backup), "families": len({r['family_id'] for r in relations}), "parents": len({r['parent_id'] for r in relations}), "leaves": len({r['leaf_id'] for r in relations}), "titles": len(titles)}


if __name__ == "__main__":
    print(json.dumps(apply(), indent=2))
