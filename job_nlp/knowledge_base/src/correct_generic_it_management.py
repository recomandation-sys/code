"""Route generic IT-management titles to a parent-only operational path.

Position/seniority is extracted independently. Generic CIO/IT/MIS manager and
director titles do not provide evidence for the Enterprise Architect leaf, so
they remain at the Systems Operations parent with ``leaf_id = NULL``.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "it_knowledge.sqlite"
REPORT = ROOT.parent / "artifacts" / "reports" / "generic_it_management_abstention.json"
VERSION = "IT_KB_2.5.1_MANAGEMENT_ABSTENTION"
TARGET_FAMILY = "PLATFORM_INFRASTRUCTURE"
TARGET_PARENT = "SYSTEMS_OPERATIONS"


def apply() -> dict[str, object]:
    backup = DB.with_name("it_knowledge.sqlite.pre_generic_management_abstention.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        title_rows = con.execute(
            """
            SELECT tc.title_id,i.title,tc.family_id,tc.parent_id,tc.leaf_id,tc.method,tc.rule_id
            FROM title_classification tc JOIN input_title i USING(title_id)
            WHERE tc.leaf_id='ENTERPRISE_ARCHITECT' AND tc.method='position_leaf_functional_remap_v1'
            ORDER BY i.original_row_number,tc.title_id
            """
        ).fetchall()
        occupation_rows = con.execute(
            """
            SELECT occupation_id,family_id,parent_id,leaf_id,method,rule_id
            FROM occupation_classification
            WHERE leaf_id='ENTERPRISE_ARCHITECT' AND method='position_leaf_functional_remap_v1'
            ORDER BY occupation_id
            """
        ).fetchall()
        if not title_rows and not occupation_rows:
            raise RuntimeError("No Enterprise Architect position-remap rows found; migration already applied")

        title_ids = [r["title_id"] for r in title_rows]
        occupation_ids = [r["occupation_id"] for r in occupation_rows]
        with con:
            for row in title_rows:
                con.execute(
                    """
                    UPDATE title_classification
                    SET family_id=?,parent_id=?,leaf_id=NULL,
                        method='generic_management_parent_only_v1',
                        rule_id='generic_management_abstention_v1'
                    WHERE title_id=?
                    """,
                    (TARGET_FAMILY, TARGET_PARENT, row["title_id"]),
                )
                con.execute(
                    "UPDATE input_title SET resolution_status='parent_only' WHERE title_id=?",
                    (row["title_id"],),
                )
            for row in occupation_rows:
                con.execute(
                    """
                    UPDATE occupation_classification
                    SET family_id=?,parent_id=?,leaf_id=NULL,
                        method='generic_management_parent_only_v1',
                        rule_id='generic_management_abstention_v1',
                        mapping_relation='parent_only'
                    WHERE occupation_id=?
                    """,
                    (TARGET_FAMILY, TARGET_PARENT, row["occupation_id"]),
                )

            if title_ids:
                marks = ",".join("?" for _ in title_ids)
                con.execute(f"DELETE FROM leaf_title_evidence WHERE title_id IN ({marks})", title_ids)
            if occupation_ids:
                marks = ",".join("?" for _ in occupation_ids)
                for table in (
                    "leaf_source_occupation",
                    "leaf_task_evidence",
                    "leaf_skill_profile",
                    "leaf_technology_profile",
                ):
                    con.execute(f"DELETE FROM {table} WHERE occupation_id IN ({marks})", occupation_ids)
                alias_ids = [
                    row[0] for row in con.execute(
                        f"SELECT alias_id FROM occupation_alias WHERE occupation_id IN ({marks})",
                        occupation_ids,
                    )
                ]
                if alias_ids:
                    alias_marks = ",".join("?" for _ in alias_ids)
                    con.execute(f"DELETE FROM leaf_alias WHERE alias_id IN ({alias_marks})", alias_ids)

            con.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    ("taxonomy_version", VERSION),
                    ("taxonomy_v2_version", VERSION),
                    ("generic_management_abstention_at", now),
                    ("generic_management_policy", "Generic CIO/IT/MIS management titles route to SYSTEMS_OPERATIONS parent-only; seniority is independent."),
                ],
            )
            con.execute("UPDATE family SET taxonomy_version=?", (VERSION,))
            con.execute("PRAGMA user_version=116")
        con.execute("PRAGMA foreign_keys=ON")
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign-key violations after migration: {violations[:5]}")
        report = {
            "taxonomy_version": VERSION,
            "applied_at": now,
            "target": {"family_id": TARGET_FAMILY, "parent_id": TARGET_PARENT, "leaf_id": None},
            "title_count": len(title_rows),
            "occupation_count": len(occupation_rows),
            "titles": [dict(r) for r in title_rows],
            "occupations": [dict(r) for r in occupation_rows],
            "rollback_backup": str(backup),
            "reason": "Generic management/C-level titles describe organizational responsibility, not Enterprise Architect duties.",
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"backup": str(backup), "report": str(REPORT), "titles": len(title_rows), "occupations": len(occupation_rows)}
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(apply(), indent=2))
