"""Merge cloud/DevOps parents and remove non-core SCADA/OT leaves.

Cloud engineering and DevOps/platform engineering are one production-facing
cloud-platform domain. Operational Technology/SCADA is outside the core IT
scope and is removed with its reviewed title rows. All retained cloud/DevOps
leaves, titles and source mappings are preserved under the new parent.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "it_knowledge.sqlite"
REPORT = ROOT.parent / "artifacts" / "reports" / "cloud_platform_merge_drop_ot.json"
VERSION = "IT_KB_2.4.0_CORE_CLOUD_PLATFORM"
OLD_PARENTS = ("CLOUD_ENGINEERING", "DEVOPS_PLATFORM")
NEW_PARENT = "CLOUD_AND_PLATFORM"
NEW_PARENT_LABEL = "Cloud and Platform Engineering"
OT_LEAVES = ("OT_TECHNICIAN", "SCADA_OT_ENGINEER")
OT_PARENT = "OPERATIONAL_TECHNOLOGY"


def apply() -> dict[str, object]:
    backup = DB.with_name("it_knowledge.sqlite.pre_cloud_platform_merge.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        parent_placeholders = ",".join("?" for _ in OLD_PARENTS)
        leaf_placeholders = ",".join("?" for _ in OT_LEAVES)
        current_parents = {r[0] for r in con.execute("SELECT parent_id FROM parent")}
        if NEW_PARENT in current_parents:
            raise RuntimeError(f"{NEW_PARENT} already exists; migration appears partially applied")
        missing = set(OLD_PARENTS) - current_parents
        if missing:
            raise RuntimeError("cloud/DevOps parents missing: " + ", ".join(sorted(missing)))
        current_leaves = {r[0] for r in con.execute("SELECT leaf_id FROM leaf")}
        missing_leaves = set(OT_LEAVES) - current_leaves
        if missing_leaves:
            raise RuntimeError("OT leaves missing: " + ", ".join(sorted(missing_leaves)))

        ot_titles = [dict(r) for r in con.execute(
            f"""SELECT i.title_id,i.title,i.original_row_number,tc.family_id,tc.parent_id,tc.leaf_id,
                       tc.method,tc.rule_id,tc.review_status
                FROM title_classification tc JOIN input_title i USING(title_id)
                WHERE tc.leaf_id IN ({leaf_placeholders}) ORDER BY i.original_row_number""",
            OT_LEAVES,
        )]
        cloud_leaves = [dict(r) for r in con.execute(
            f"""SELECT l.leaf_id,l.parent_id,l.label,l.scope,l.status,p.family_id,p.label parent
                FROM leaf l JOIN parent p USING(parent_id)
                WHERE l.parent_id IN ({parent_placeholders}) ORDER BY l.parent_id,l.leaf_id""",
            OLD_PARENTS,
        )]
        source_rows = [dict(r) for r in con.execute(
            f"""SELECT oc.occupation_id,o.source_id,o.native_id,o.preferred_label,oc.parent_id,oc.leaf_id
                FROM occupation_classification oc JOIN occupation o USING(occupation_id)
                WHERE oc.parent_id IN ({parent_placeholders}) ORDER BY o.source_id,o.preferred_label""",
            OLD_PARENTS,
        )]
        before = {
            "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
            "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
            "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
            "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
            "assigned_title_paths": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NOT NULL").fetchone()[0],
            "source_occupations": con.execute("SELECT count(*) FROM occupation").fetchone()[0],
        }

        with con:
            # Remove generated evidence for OT leaves before deleting them.
            for table in (
                "leaf_title_evidence", "leaf_source_occupation", "leaf_alias",
                "leaf_task_evidence", "leaf_skill_profile", "leaf_technology_profile",
                "leaf_profile",
            ):
                con.execute(f"DELETE FROM {table} WHERE leaf_id IN ({leaf_placeholders})", OT_LEAVES)
            con.execute(
                f"DELETE FROM leaf_confusion_pair WHERE leaf_id IN ({leaf_placeholders}) OR sibling_leaf_id IN ({leaf_placeholders})",
                OT_LEAVES + OT_LEAVES,
            )
            if ot_titles:
                title_ids = tuple(r["title_id"] for r in ot_titles)
                title_sql = ",".join("?" for _ in title_ids)
                con.execute(f"DELETE FROM title_source_match WHERE title_id IN ({title_sql})", title_ids)
                con.execute(f"DELETE FROM title_classification WHERE title_id IN ({title_sql})", title_ids)
                con.execute(f"DELETE FROM input_title WHERE title_id IN ({title_sql})", title_ids)

            # Remove old identity crosswalks, then preserve explicit migration
            # records for audit and legacy-ID translation.
            con.execute(
                f"""DELETE FROM taxonomy_v2_crosswalk
                    WHERE (old_level='leaf' AND old_id IN ({leaf_placeholders}))
                       OR (new_level='leaf' AND new_id IN ({leaf_placeholders}))
                       OR (old_level='parent' AND old_id IN ({parent_placeholders}))
                       OR (new_level='parent' AND new_id IN ({parent_placeholders}))
                       OR (old_level='parent' AND old_id=?)
                       OR (new_level='parent' AND new_id=?)""",
                OT_LEAVES + OT_LEAVES + OLD_PARENTS + OLD_PARENTS + (OT_PARENT, OT_PARENT),
            )

            # Create the merged parent using the existing platform family.
            con.execute(
                "INSERT INTO parent(parent_id,family_id,label,definition) VALUES(?,?,?,?)",
                (NEW_PARENT, "PLATFORM_INFRASTRUCTURE", NEW_PARENT_LABEL,
                 "Design, build and operate cloud platforms, DevOps delivery systems, SRE and release infrastructure."),
            )
            # The same functional domain may point to both old parents. Merge
            # those candidate rows explicitly before the parent-key rewrite so
            # the composite primary key remains unique.
            domain_rows = con.execute(
                f"""SELECT domain_id,MIN(relation),MIN(review_status)
                    FROM domain_parent_candidate
                    WHERE parent_id IN ({parent_placeholders})
                    GROUP BY domain_id""",
                OLD_PARENTS,
            ).fetchall()
            con.execute(f"DELETE FROM domain_parent_candidate WHERE parent_id IN ({parent_placeholders})", OLD_PARENTS)
            con.executemany(
                "INSERT INTO domain_parent_candidate(domain_id,parent_id,relation,review_status,rule_id) VALUES(?,?,?,?,?)",
                [(r[0], NEW_PARENT, r[1], r[2], f"domain_parent:{r[0].split(':')[-1]}:{NEW_PARENT}") for r in domain_rows],
            )
            for table in (
                "leaf", "occupation_group_edge", "occupation_classification",
                "title_classification", "domain_edge", "activity_edge",
                "domain_parent_candidate", "document_role",
            ):
                con.execute(f"UPDATE {table} SET parent_id=? WHERE parent_id IN ({parent_placeholders})", (NEW_PARENT,) + OLD_PARENTS)
            con.execute(f"DELETE FROM parent WHERE parent_id IN ({parent_placeholders})", OLD_PARENTS)

            # Remove OT leaves after their title/evidence references are gone.
            con.execute(f"DELETE FROM leaf WHERE leaf_id IN ({leaf_placeholders})", OT_LEAVES)
            con.execute("DELETE FROM parent WHERE parent_id=?", (OT_PARENT,))

            con.executemany(
                "INSERT INTO taxonomy_v2_crosswalk VALUES(?,?,?,?,?,?,?)",
                [
                    ("parent", old, "parent", NEW_PARENT, "functional_parent_merge",
                     "Cloud engineering and DevOps/platform engineering are one cloud-platform domain.", VERSION)
                    for old in OLD_PARENTS
                ] + [
                    ("leaf", leaf, "role_track", "EXCLUDED", "non_core_scope_exclusion",
                     "SCADA/operational technology is outside the core IT taxonomy.", VERSION)
                    for leaf in OT_LEAVES
                ] + [
                    ("parent", OT_PARENT, "role_track", "EXCLUDED", "non_core_scope_exclusion",
                     "SCADA/operational technology is outside the core IT taxonomy.", VERSION)
                ],
            )
            con.execute("UPDATE family SET taxonomy_version=?", (VERSION,))
            con.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    ("taxonomy_version", VERSION),
                    ("taxonomy_v2_version", VERSION),
                    ("core_it_leaf_policy", "SCADA/OT is excluded; cloud and DevOps/platform roles share CLOUD_AND_PLATFORM."),
                    ("cloud_platform_parent", NEW_PARENT),
                    ("cloud_platform_merge_at", now),
                    ("operational_technology_removal_at", now),
                ],
            )
            con.execute("PRAGMA user_version=114")

        con.execute("PRAGMA foreign_keys=ON")
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign-key violations after migration: {violations[:5]}")
        after = {
            "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
            "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
            "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
            "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
            "assigned_title_paths": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NOT NULL").fetchone()[0],
            "source_occupations": con.execute("SELECT count(*) FROM occupation").fetchone()[0],
        }
        report = {
            "taxonomy_version": VERSION,
            "removed_at": now,
            "reason": "Core IT only: SCADA/OT is excluded; cloud engineering and DevOps/platform engineering are merged.",
            "removed_parent": "OPERATIONAL_TECHNOLOGY",
            "removed_leaves": OT_LEAVES,
            "removed_titles": ot_titles,
            "merged_parents": {"old": OLD_PARENTS, "new": NEW_PARENT, "label": NEW_PARENT_LABEL},
            "retained_cloud_platform_leaves": cloud_leaves,
            "affected_source_occupations": source_rows,
            "counts_before": before,
            "counts_after": after,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"backup": str(backup), "report": str(REPORT), **after}
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(apply(), indent=2))
