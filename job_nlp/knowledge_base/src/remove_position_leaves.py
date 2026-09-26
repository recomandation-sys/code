"""Replace position-only taxonomy leaves with functional IT subdomains.

The product already extracts seniority/position independently.  This migration
therefore removes C-level and people-manager leaves from the occupational tree,
routes their reviewed titles and source occupations to functional leaves, and
keeps the titles themselves.  It is deliberately deterministic and produces a
rollback backup plus a complete JSON audit.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "it_knowledge.sqlite"
REPORT = ROOT.parent / "artifacts" / "reports" / "removed_position_leaves.json"
VERSION = "IT_KB_2.3.0_FUNCTIONAL_SUBDOMAINS"
OLD_PARENT = "PROJECT_PRODUCT"
NEW_PARENT = "AGILE_PRODUCT_AND_PROJECT_DELIVERY"
NEW_PARENT_LABEL = "Agile Product and Project Delivery"

POSITION_LEAVES = (
    "CTO", "CIO", "CDO", "CISO",
    "ENGINEERING_MANAGER", "DATA_MANAGER", "SECURITY_MANAGER",
    "IT_OPERATIONS_MANAGER", "SUPPORT_MANAGER", "TELECOM_MANAGER",
    "IT_QA_MANAGER", "BUSINESS_ANALYSIS_MANAGER", "DOCUMENTATION_MANAGER",
    "IT_RESEARCH_MANAGER", "IT_MANAGER", "DIGITAL_TRANSFORMATION_MANAGER",
    "SERVICE_DELIVERY_MANAGER", "CHANGE_CONFIG_MANAGER", "IT_KNOWLEDGE_MANAGER",
)

# Safe defaults follow the user's functional-subdomain matrix.  Title-level
# overrides below preserve narrower technical meaning where it is explicit.
DEFAULT_TARGET = {
    "CTO": "SOFTWARE_ARCHITECT",
    "CIO": "ENTERPRISE_ARCHITECT",
    "CDO": "DATA_ARCHITECT",
    "CISO": "SECURITY_GRC",
    # Generic development is represented by a concrete implementation leaf;
    # the retired generic application-development sink is never emitted.
    "ENGINEERING_MANAGER": "BACKEND_DEVELOPER",
    "DATA_MANAGER": "DATA_ENGINEER",
    "SECURITY_MANAGER": "SECURITY_GRC",
    "IT_OPERATIONS_MANAGER": "SYSTEM_ADMIN",
    "SUPPORT_MANAGER": "SUPPORT_ENGINEER",
    "TELECOM_MANAGER": "TELECOM_ENGINEER",
    "IT_QA_MANAGER": "SOFTWARE_TESTER",
    "BUSINESS_ANALYSIS_MANAGER": "BUSINESS_ANALYST",
    "DOCUMENTATION_MANAGER": "TECHNICAL_WRITER",
    "IT_RESEARCH_MANAGER": "COMPUTER_SCIENTIST",
    "IT_MANAGER": "ENTERPRISE_ARCHITECT",
    "DIGITAL_TRANSFORMATION_MANAGER": "CLOUD_ENGINEER",
    "SERVICE_DELIVERY_MANAGER": "SUPPORT_ENGINEER",
    "CHANGE_CONFIG_MANAGER": "SYSTEM_CONFIG",
    "IT_KNOWLEDGE_MANAGER": "TECHNICAL_WRITER",
}


def _norm(value: str) -> str:
    value = str(value or "").casefold().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def route(old_leaf: str, title: str) -> str:
    """Return a valid functional leaf for one reviewed title/source label."""
    t = _norm(title)

    if old_leaf == "DATA_MANAGER":
        if "data center" in t:
            return "DATACENTER_OPERATOR"
        if "database administration project" in t or "database development project" in t:
            return "IT_PROJECT_MANAGER"
        if "database administration" in t or "database manager" in t or "database development" in t:
            return "DATABASE_ADMIN" if "administration" in t or "manager" in t else "DATABASE_DEVELOPER"
        if "business intelligence" in t or "analytics manager" in t or "data analytics" in t:
            return "BI_ANALYST"
        if "data systems" in t:
            return "DATA_ARCHITECT"
        return "DATA_ENGINEER"

    if old_leaf == "IT_OPERATIONS_MANAGER":
        if "cyber security operations" in t or "security operations" in t:
            return "SECURITY_ANALYST"
        if "computer operations" in t:
            return "DATACENTER_OPERATOR"
        return "SYSTEM_ADMIN"

    if old_leaf == "SUPPORT_MANAGER":
        if "application support" in t or "software support" in t:
            return "APPLICATION_SUPPORT"
        if "desktop support" in t:
            return "DESKTOP_SUPPORT"
        if "help desk" in t:
            return "HELPDESK"
        if "network support" in t:
            return "NETWORK_SUPPORT"
        return "SUPPORT_ENGINEER"

    if old_leaf == "IT_MANAGER":
        if "financial systems" in t:
            return "SYSTEMS_ANALYST"
        if "technical solutions" in t:
            return "SOLUTION_ARCHITECT"
        if "portfolio" in t:
            return "IT_PROJECT_MANAGER"
        if "process manager" in t:
            return "SYSTEM_CONFIG"
        if "supervisor" in t or "coordinator" in t:
            return "SUPPORT_ENGINEER"
        return "ENTERPRISE_ARCHITECT"

    if old_leaf == "SERVICE_DELIVERY_MANAGER":
        if "application" in t:
            return "APPLICATION_SUPPORT"
        return "SUPPORT_ENGINEER"

    if old_leaf == "DIGITAL_TRANSFORMATION_MANAGER":
        return "CLOUD_ENGINEER"

    return DEFAULT_TARGET[old_leaf]


def _path(con: sqlite3.Connection, leaf_id: str) -> tuple[str, str]:
    row = con.execute(
        "SELECT p.parent_id,p.family_id FROM leaf l JOIN parent p USING(parent_id) WHERE l.leaf_id=?",
        (leaf_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"target functional leaf does not exist: {leaf_id}")
    parent_id = str(row[0])
    # The delivery parent is renamed in the same migration. Resolve routes
    # against its post-migration ID so title/source updates remain valid.
    if parent_id == OLD_PARENT:
        parent_id = NEW_PARENT
    return parent_id, str(row[1])


def apply() -> dict[str, object]:
    backup = DB.with_name("it_knowledge.sqlite.pre_position_leaf_removal.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        placeholders = ",".join("?" for _ in POSITION_LEAVES)
        existing = {r[0] for r in con.execute("SELECT leaf_id FROM leaf")}
        missing = set(POSITION_LEAVES) - existing
        if missing:
            raise RuntimeError("position leaves missing: " + ", ".join(sorted(missing)))
        if NEW_PARENT in {r[0] for r in con.execute("SELECT parent_id FROM parent")}: 
            raise RuntimeError(f"{NEW_PARENT} already exists; migration appears partially applied")

        # Validate all planned destination leaves before touching the database.
        title_rows = [dict(r) for r in con.execute(
            f"""SELECT tc.title_id,i.title,tc.leaf_id old_leaf_id,tc.family_id old_family_id,
                       tc.parent_id old_parent_id,tc.method,tc.rule_id,tc.review_status
                FROM title_classification tc JOIN input_title i USING(title_id)
                WHERE tc.leaf_id IN ({placeholders}) ORDER BY i.original_row_number""",
            POSITION_LEAVES,
        )]
        occupation_rows = [dict(r) for r in con.execute(
            f"""SELECT oc.occupation_id,o.source_id,o.native_id,o.preferred_label,oc.leaf_id old_leaf_id,
                       oc.family_id old_family_id,oc.parent_id old_parent_id,oc.mapping_relation,
                       oc.method,oc.review_status,oc.rule_id
                FROM occupation_classification oc JOIN occupation o USING(occupation_id)
                WHERE oc.leaf_id IN ({placeholders}) ORDER BY o.source_id,o.preferred_label""",
            POSITION_LEAVES,
        )]
        title_plan = []
        for row in title_rows:
            target = route(row["old_leaf_id"], row["title"])
            parent_id, family_id = _path(con, target)
            title_plan.append({**row, "new_leaf_id": target, "new_parent_id": parent_id, "new_family_id": family_id})
        occupation_plan = []
        for row in occupation_rows:
            target = route(row["old_leaf_id"], row["preferred_label"])
            parent_id, family_id = _path(con, target)
            occupation_plan.append({**row, "new_leaf_id": target, "new_parent_id": parent_id, "new_family_id": family_id})
        # The broad O*NET manager record was parent-only under the now-empty
        # position parent. Give it a functional architecture destination so no
        # source occupation is left attached to a retired parent.
        parent_only_rows = [dict(r) for r in con.execute(
            """SELECT oc.occupation_id,o.source_id,o.native_id,o.preferred_label,oc.leaf_id old_leaf_id,
                       oc.family_id old_family_id,oc.parent_id old_parent_id,oc.mapping_relation,
                       oc.method,oc.review_status,oc.rule_id
                FROM occupation_classification oc JOIN occupation o USING(occupation_id)
                WHERE oc.parent_id='IT_MANAGEMENT' AND oc.leaf_id IS NULL"""
        )]
        parent_only_plan = []
        for row in parent_only_rows:
            parent_id, family_id = _path(con, "ENTERPRISE_ARCHITECT")
            parent_only_plan.append({**row, "new_leaf_id": "ENTERPRISE_ARCHITECT", "new_parent_id": parent_id, "new_family_id": family_id})

        old_leaf_rows = [dict(r) for r in con.execute(
            f"""SELECT l.leaf_id,l.parent_id,l.label,l.scope,l.status,p.family_id,p.label parent,f.label family
                FROM leaf l JOIN parent p USING(parent_id) JOIN family f USING(family_id)
                WHERE l.leaf_id IN ({placeholders}) ORDER BY l.leaf_id""",
            POSITION_LEAVES,
        )]
        report: dict[str, object] = {
            "taxonomy_version": VERSION,
            "removed_at": now,
            "reason": "User policy: position/seniority is extracted separately; the job taxonomy contains functional IT subdomains only.",
            "position_leaf_ids": list(POSITION_LEAVES),
            "parent_rename": {"old_id": OLD_PARENT, "new_id": NEW_PARENT, "label": NEW_PARENT_LABEL},
            "leaves": old_leaf_rows,
            "titles": title_plan,
            "source_occupations": occupation_plan,
            "parent_only_source_occupations": parent_only_plan,
            "counts_before": {
                "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
                "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
                "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
                "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
                "source_occupations": con.execute("SELECT count(*) FROM occupation").fetchone()[0],
            },
        }

        with con:
            # Remove derived evidence for the retired nodes. It is rebuilt from
            # the new title/source classifications by the evidence migration.
            for table in (
                "leaf_title_evidence", "leaf_source_occupation", "leaf_alias",
                "leaf_task_evidence", "leaf_skill_profile", "leaf_technology_profile",
                "leaf_profile",
            ):
                con.execute(f"DELETE FROM {table} WHERE leaf_id IN ({placeholders})", POSITION_LEAVES)
            con.execute(
                f"DELETE FROM leaf_confusion_pair WHERE leaf_id IN ({placeholders}) OR sibling_leaf_id IN ({placeholders})",
                POSITION_LEAVES + POSITION_LEAVES,
            )

            # Retire stale identity crosswalks and preserve explicit functional
            # remaps below, including one-to-many title-level routes.
            con.execute(
                f"""DELETE FROM taxonomy_v2_crosswalk
                    WHERE (old_level='leaf' AND old_id IN ({placeholders}))
                       OR (new_level='leaf' AND new_id IN ({placeholders}))
                       OR (old_level='parent' AND old_id IN (?,?))
                       OR (new_level='parent' AND new_id IN (?,?))""",
                POSITION_LEAVES + POSITION_LEAVES + (OLD_PARENT, "IT_MANAGEMENT", OLD_PARENT, "IT_MANAGEMENT"),
            )

            # Rename the retained functional delivery parent before assigning
            # child rows. Foreign-key checks are disabled only for this atomic
            # key rewrite and are revalidated before returning.
            con.execute("UPDATE parent SET parent_id=?,label=?,definition=? WHERE parent_id=?", (
                NEW_PARENT, NEW_PARENT_LABEL,
                "Plan and coordinate technology products, projects and agile delivery.",
                OLD_PARENT,
            ))
            # Update every operational parent_id reference, including the
            # domain-parent candidate table used by semantic context.
            for table in (
                "leaf", "occupation_group_edge", "occupation_classification",
                "title_classification", "domain_edge", "activity_edge",
                "domain_parent_candidate", "document_role",
            ):
                con.execute(f"UPDATE {table} SET parent_id=? WHERE parent_id=?", (NEW_PARENT, OLD_PARENT))

            # Apply title/source functional routes.
            for row in title_plan:
                con.execute(
                    "UPDATE title_classification SET family_id=?,parent_id=?,leaf_id=?,method=?,rule_id=? WHERE title_id=?",
                    (row["new_family_id"], row["new_parent_id"], row["new_leaf_id"],
                     "position_leaf_functional_remap_v1", "position_leaf_removal_v1", row["title_id"]),
                )
            for row in occupation_plan:
                con.execute(
                    "UPDATE occupation_classification SET family_id=?,parent_id=?,leaf_id=?,method=?,rule_id=? WHERE occupation_id=?",
                    (row["new_family_id"], row["new_parent_id"], row["new_leaf_id"],
                     "position_leaf_functional_remap_v1", "position_leaf_removal_v1", row["occupation_id"]),
                )
            for row in parent_only_plan:
                con.execute(
                    "UPDATE occupation_classification SET family_id=?,parent_id=?,leaf_id=?,mapping_relation=?,method=?,rule_id=? WHERE occupation_id=?",
                    (row["new_family_id"], row["new_parent_id"], row["new_leaf_id"], "source_narrower",
                     "position_leaf_functional_remap_v1", "position_leaf_removal_v1", row["occupation_id"]),
                )

            # Delete the position leaves after all mappings have moved.
            con.execute(f"DELETE FROM leaf WHERE leaf_id IN ({placeholders})", POSITION_LEAVES)
            # IT_MANAGEMENT is now empty and is itself a position-only parent.
            con.execute("DELETE FROM parent WHERE parent_id='IT_MANAGEMENT'")

            crosswalk_rows = []
            for old_leaf in POSITION_LEAVES:
                new_ids = sorted({r["new_leaf_id"] for r in title_plan + occupation_plan if r["old_leaf_id"] == old_leaf})
                for new_leaf in new_ids:
                    crosswalk_rows.append(("leaf", old_leaf, "leaf", new_leaf, "functional_remap",
                                           "Position-only leaf removed; reviewed titles/source occupations routed to a functional subdomain.", VERSION))
            crosswalk_rows.append(("parent", OLD_PARENT, "parent", NEW_PARENT, "functional_parent_rename",
                                   "Product, project and agile delivery is a functional parent, not a position leaf.", VERSION))
            crosswalk_rows.append(("parent", "IT_MANAGEMENT", "parent", "SYSTEMS_ARCHITECTURE", "functional_parent_remap",
                                   "Position-only management parent removed; broad IT management source records route to enterprise architecture.", VERSION))
            con.executemany("INSERT INTO taxonomy_v2_crosswalk VALUES(?,?,?,?,?,?,?)", crosswalk_rows)
            con.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    ("taxonomy_version", VERSION),
                    ("taxonomy_v2_version", VERSION),
                    ("position_leaf_policy", "Position/seniority is extracted independently; taxonomy leaves are functional IT subdomains."),
                    ("position_leaf_removal_at", now),
                    ("functional_delivery_parent", NEW_PARENT),
                ],
            )
            con.execute("UPDATE family SET taxonomy_version=?", (VERSION,))
            con.execute("PRAGMA user_version=113")

        con.execute("PRAGMA foreign_keys=ON")
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign-key violations after migration: {violations[:5]}")
        report["route_counts"] = {
            "titles": dict(Counter(r["new_leaf_id"] for r in title_plan)),
            "source_occupations": dict(Counter(r["new_leaf_id"] for r in occupation_plan + parent_only_plan)),
        }
        report["counts_after"] = {
            "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
            "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
            "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
            "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
            "source_occupations": con.execute("SELECT count(*) FROM occupation").fetchone()[0],
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"backup": str(backup), "report": str(REPORT), **report["counts_after"]}
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(apply(), indent=2))
