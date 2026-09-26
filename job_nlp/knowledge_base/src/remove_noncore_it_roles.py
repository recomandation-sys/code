"""Remove explicitly non-core IT roles from the canonical knowledge base.

This is intentionally destructive inside the working SQLite snapshot because
the product policy says these roles must never be emitted. A dated SQLite
backup and an external JSON deletion report are created before the transaction.
Raw source files outside SQLite are untouched.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "it_knowledge.sqlite"
REPORT = ROOT.parent / "artifacts" / "reports" / "removed_noncore_it_roles.json"
VERSION = "IT_KB_2.2.0_CORE_IT_ONLY"
TARGET_LEAVES = (
    "TELECOM_INSTALLER_REPAIRER",
    "TELECOM_TECHNICIAN",
    "TELECOM_OPERATOR",
    "MOBILE_REPAIR",
    "COMPUTER_REPAIR",
)


def _placeholders(values: tuple[str, ...]) -> str:
    return ",".join("?" for _ in values)


def apply() -> dict[str, object]:
    backup = DB.with_name("it_knowledge.sqlite.pre_noncore_it_role_removal.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        leaves_sql = _placeholders(TARGET_LEAVES)
        leaf_rows = [dict(r) for r in con.execute(
            f"""SELECT l.leaf_id,l.parent_id,l.label,l.scope,l.status,p.family_id,p.label parent,f.label family
                FROM leaf l JOIN parent p ON p.parent_id=l.parent_id JOIN family f ON f.family_id=p.family_id
                WHERE l.leaf_id IN ({leaves_sql}) ORDER BY l.leaf_id""", TARGET_LEAVES
        )]
        if not leaf_rows:
            raise RuntimeError("None of the requested non-core leaves exists in the database")

        title_rows = [dict(r) for r in con.execute(
            f"""SELECT i.title_id,i.title,i.original_row_number,tc.family_id,tc.parent_id,tc.leaf_id,tc.method,tc.rule_id,tc.review_status
                FROM title_classification tc JOIN input_title i USING(title_id)
                WHERE tc.leaf_id IN ({leaves_sql}) ORDER BY i.original_row_number""", TARGET_LEAVES
        )]
        occupation_rows = [dict(r) for r in con.execute(
            f"""SELECT o.occupation_id,o.source_id,o.native_id,o.preferred_label,o.description,o.group_id,o.scope,o.scope_reason,o.evidence_id,
                       oc.family_id,oc.parent_id,oc.leaf_id
                FROM occupation_classification oc JOIN occupation o USING(occupation_id)
                WHERE oc.leaf_id IN ({leaves_sql}) ORDER BY o.source_id,o.native_id""", TARGET_LEAVES
        )]
        occupation_ids = tuple(r["occupation_id"] for r in occupation_rows)
        title_ids = tuple(r["title_id"] for r in title_rows)
        alias_ids: tuple[str, ...] = ()
        if occupation_ids:
            occ_sql = _placeholders(occupation_ids)
            alias_ids = tuple(r[0] for r in con.execute(
                f"SELECT alias_id FROM occupation_alias WHERE occupation_id IN ({occ_sql})", occupation_ids
            ))

        report = {
            "taxonomy_version": VERSION,
            "removed_at": now,
            "reason": "User policy: only core IT fields; outside-plant telecom, manual telecom operators, storefront mobile repair and computer repair are excluded.",
            "leaf_ids": list(TARGET_LEAVES),
            "leaves": leaf_rows,
            "titles": title_rows,
            "source_occupations": occupation_rows,
            "counts_before": {
                "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
                "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
                "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
                "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
                "source_occupations": con.execute("SELECT count(*) FROM occupation").fetchone()[0],
            },
        }

        with con:
            # Delete title evidence and title rows for these non-core roles.
            if title_ids:
                title_sql = _placeholders(title_ids)
                con.execute(f"DELETE FROM leaf_title_evidence WHERE title_id IN ({title_sql})", title_ids)
                con.execute(f"DELETE FROM title_source_match WHERE title_id IN ({title_sql})", title_ids)
                con.execute(f"DELETE FROM title_classification WHERE title_id IN ({title_sql})", title_ids)
                con.execute(f"DELETE FROM input_title WHERE title_id IN ({title_sql})", title_ids)

            # Remove all leaf/profile/crosswalk references first.
            con.execute(f"DELETE FROM leaf_confusion_pair WHERE leaf_id IN ({leaves_sql}) OR sibling_leaf_id IN ({leaves_sql})", TARGET_LEAVES + TARGET_LEAVES)
            for table in ("leaf_profile", "leaf_source_occupation", "leaf_alias", "leaf_task_evidence", "leaf_skill_profile", "leaf_technology_profile"):
                con.execute(f"DELETE FROM {table} WHERE leaf_id IN ({leaves_sql})", TARGET_LEAVES)
            con.execute(
                f"DELETE FROM taxonomy_v2_crosswalk WHERE (old_level='leaf' AND old_id IN ({leaves_sql})) OR (new_level='leaf' AND new_id IN ({leaves_sql}))",
                TARGET_LEAVES + TARGET_LEAVES,
            )
            con.execute(f"DELETE FROM occupation_classification WHERE leaf_id IN ({leaves_sql})", TARGET_LEAVES)

            # Remove source occupation profiles that existed solely to support
            # these deleted roles, including their aliases and source indexes.
            if occupation_ids:
                occ_sql = _placeholders(occupation_ids)
                con.execute(f"DELETE FROM related_occupation WHERE occupation_id IN ({occ_sql}) OR related_occupation_id IN ({occ_sql})", occupation_ids + occupation_ids)
                con.execute(f"DELETE FROM occupation_skill WHERE occupation_id IN ({occ_sql})", occupation_ids)
                con.execute(f"DELETE FROM task_rating WHERE occupation_id IN ({occ_sql})", occupation_ids)
                con.execute(f"DELETE FROM task_activity WHERE occupation_id IN ({occ_sql})", occupation_ids)
                con.execute(f"DELETE FROM occupation_task WHERE occupation_id IN ({occ_sql})", occupation_ids)
                con.execute(f"DELETE FROM occupation_rating WHERE occupation_id IN ({occ_sql})", occupation_ids)
                con.execute(f"DELETE FROM occupation_metadata WHERE occupation_id IN ({occ_sql})", occupation_ids)
                con.execute(f"DELETE FROM occupation_job_zone WHERE occupation_id IN ({occ_sql})", occupation_ids)
                con.execute(f"DELETE FROM occupation_search WHERE occupation_id IN ({occ_sql})", occupation_ids)
                if alias_ids:
                    alias_sql = _placeholders(alias_ids)
                    con.execute(f"DELETE FROM title_source_match WHERE alias_id IN ({alias_sql})", alias_ids)
                    con.execute(f"DELETE FROM occupation_alias WHERE alias_id IN ({alias_sql})", alias_ids)
                con.execute(f"DELETE FROM occupation WHERE occupation_id IN ({occ_sql})", occupation_ids)

            # Remove the five canonical leaf nodes themselves.
            con.execute(f"DELETE FROM leaf WHERE leaf_id IN ({leaves_sql})", TARGET_LEAVES)

            con.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    ("taxonomy_version", VERSION),
                    ("taxonomy_v2_version", VERSION),
                    ("core_it_leaf_policy", "Outside-plant telecom, manual telecom operators, mobile repair and computer repair are excluded."),
                    ("core_it_leaf_removal_at", now),
                ],
            )
            con.execute("PRAGMA user_version=112")

        # Remove now-unreferenced task rows only after all occupation links are gone.
        with con:
            orphan_tasks = [r[0] for r in con.execute(
                "SELECT task_id FROM task t WHERE NOT EXISTS (SELECT 1 FROM occupation_task ot WHERE ot.task_id=t.task_id)"
            )]
            if orphan_tasks:
                task_sql = _placeholders(tuple(orphan_tasks))
                con.execute(f"DELETE FROM task_rating WHERE task_id IN ({task_sql})", orphan_tasks)
                con.execute(f"DELETE FROM task_activity WHERE task_id IN ({task_sql})", orphan_tasks)
                con.execute(f"DELETE FROM task_domain WHERE task_id IN ({task_sql})", orphan_tasks)
                con.execute(f"DELETE FROM skill_task_evidence WHERE task_id IN ({task_sql})", orphan_tasks)
                con.execute(f"DELETE FROM task WHERE task_id IN ({task_sql})", orphan_tasks)
            report["orphan_tasks_removed"] = len(orphan_tasks)

        con.execute("PRAGMA foreign_keys=ON")
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign-key violations after removal: {violations[:5]}")
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
