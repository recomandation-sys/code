"""Apply the residual core-IT taxonomy corrections.

The migration removes the two single-leaf parents, merges the obsolete
``Computer Programmer`` leaf into the general software-developer leaf, and
turns the two generic data/systems leaves into explicit parent-only
abstentions.  Distinct sustainable-IT and hardware-support occupations are
retained as leaves under the functional support parents; deleting those leaves
would lose routing information.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "it_knowledge.sqlite"
REPORT = ROOT.parent / "artifacts" / "reports" / "residual_taxonomy_consolidation.json"
VERSION = "IT_KB_2.5.0_RESIDUAL_TAXONOMY"

PARENT_MOVES = {
    "SERVICE_GOVERNANCE": "SYSTEMS_OPERATIONS",
    "HARDWARE_SUPPORT": "USER_APPLICATION_SUPPORT",
}
LEAF_MERGES = {
    "COMPUTER_PROGRAMMER": "SYSTEMS_PROGRAMMER",
}
GENERIC_SINKS = {
    "DATA_SPECIALIST_GENERAL": "DATA_ENGINEERING",
    "SYSTEMS_SPECIALIST_GENERAL": "SYSTEMS_ANALYSIS",
}

LEAF_DEFINITIONS = {
    "SYSTEMS_ENGINEER": (
        "Systems integration and model-based systems engineering (MBSE): "
        "integrate distributed computing systems, interfaces and technical "
        "models. This leaf is not a generic Linux/Windows server-administration role."
    ),
    "EMBEDDED_DESIGNER": (
        "Embedded hardware design: microcontroller and board architecture, "
        "schematics, PCB layout and hardware bring-up. Firmware-only work belongs "
        "to Embedded Software Developer."
    ),
    "EMBEDDED_DEVELOPER": (
        "Embedded software and firmware development using C/C++, real-time "
        "operating systems and device-level software. PCB schematics and circuit "
        "layout belong to Embedded System Designer."
    ),
}

CONFUSION_PAIRS = (
    (
        "CP:SYSTEMS_ENGINEER:SYSTEM_ADMIN",
        "SYSTEMS_ENGINEER",
        "SYSTEM_ADMIN",
        "Integration architecture and MBSE versus server administration and runtime operations.",
        "Prefer SYSTEM_ADMIN for Linux/Windows servers, patching, backups, identity or uptime; use SYSTEMS_ENGINEER for system integration, interfaces or MBSE.",
    ),
    (
        "CP:SYSTEM_ADMIN:SYSTEMS_ENGINEER",
        "SYSTEM_ADMIN",
        "SYSTEMS_ENGINEER",
        "Server and runtime operations versus integration architecture and MBSE.",
        "Do not route a server-administration posting to SYSTEMS_ENGINEER without explicit integration or MBSE evidence.",
    ),
    (
        "CP:EMBEDDED_DESIGNER:EMBEDDED_DEVELOPER",
        "EMBEDDED_DESIGNER",
        "EMBEDDED_DEVELOPER",
        "Electronics/PCB design versus firmware and embedded software.",
        "PCB, schematics, circuit and hardware bring-up support EMBEDDED_DESIGNER; C/C++, firmware or RTOS support EMBEDDED_DEVELOPER.",
    ),
    (
        "CP:EMBEDDED_DEVELOPER:EMBEDDED_DESIGNER",
        "EMBEDDED_DEVELOPER",
        "EMBEDDED_DESIGNER",
        "Firmware and embedded software versus electronics/PCB design.",
        "Do not route firmware-only evidence to EMBEDDED_DESIGNER unless board or circuit design is explicit.",
    ),
)


def _placeholders(values: tuple[str, ...]) -> str:
    return ",".join("?" for _ in values)


def _counts(con: sqlite3.Connection) -> dict[str, int]:
    return {
        "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
        "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
        "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
        "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
        "assigned_title_paths": con.execute(
            "SELECT count(*) FROM title_classification WHERE leaf_id IS NOT NULL"
        ).fetchone()[0],
        "parent_only_title_paths": con.execute(
            "SELECT count(*) FROM title_classification WHERE leaf_id IS NULL"
        ).fetchone()[0],
        "source_occupations": con.execute("SELECT count(*) FROM occupation").fetchone()[0],
    }


def _move_parent(con: sqlite3.Connection, old: str, new: str) -> None:
    """Move every operational parent reference, then remove the old parent."""
    old_rows = con.execute(
        "SELECT domain_id,relation,review_status,rule_id FROM domain_parent_candidate WHERE parent_id=?",
        (old,),
    ).fetchall()
    con.execute("DELETE FROM domain_parent_candidate WHERE parent_id=?", (old,))
    for domain_id, relation, review_status, rule_id in old_rows:
        con.execute(
            "INSERT OR IGNORE INTO domain_parent_candidate(domain_id,parent_id,relation,review_status,rule_id) VALUES(?,?,?,?,?)",
            (domain_id, new, relation, review_status, f"residual_parent_move:{domain_id}:{new}"),
        )

    # These tables have no generated duplicate parent identity in the current
    # database; the updates preserve all title, occupation and document rows.
    for table in (
        "leaf",
        "occupation_group_edge",
        "occupation_classification",
        "title_classification",
        "domain_edge",
        "activity_edge",
        "document_role",
    ):
        con.execute(f"UPDATE {table} SET parent_id=? WHERE parent_id=?", (new, old))
    con.execute("DELETE FROM parent WHERE parent_id=?", (old,))


def _merge_leaf(con: sqlite3.Connection, old: str, new: str) -> None:
    """Move a leaf's classifications/evidence to an existing target leaf."""
    old_parent = con.execute("SELECT parent_id FROM leaf WHERE leaf_id=?", (old,)).fetchone()[0]
    new_parent = con.execute("SELECT parent_id FROM leaf WHERE leaf_id=?", (new,)).fetchone()[0]
    if old_parent != new_parent:
        raise RuntimeError(f"leaf merge crosses parents: {old_parent} -> {new_parent}")

    # Title and occupation classifications have a single row per identity;
    # retain an existing target row if one already exists.
    rows = con.execute("SELECT title_id FROM title_classification WHERE leaf_id=?", (old,)).fetchall()
    for (title_id,) in rows:
        if con.execute(
            "SELECT 1 FROM title_classification WHERE title_id=? AND parent_id=? AND leaf_id=?",
            (title_id, new_parent, new),
        ).fetchone():
            con.execute("DELETE FROM title_classification WHERE title_id=? AND leaf_id=?", (title_id, old))
        else:
            con.execute("UPDATE title_classification SET leaf_id=? WHERE title_id=? AND leaf_id=?", (new, title_id, old))
    rows = con.execute("SELECT occupation_id FROM occupation_classification WHERE leaf_id=?", (old,)).fetchall()
    for (occupation_id,) in rows:
        if con.execute("SELECT 1 FROM occupation_classification WHERE occupation_id=? AND leaf_id=?", (occupation_id, new)).fetchone():
            con.execute("DELETE FROM occupation_classification WHERE occupation_id=? AND leaf_id=?", (occupation_id, old))
        else:
            con.execute("UPDATE occupation_classification SET leaf_id=? WHERE occupation_id=? AND leaf_id=?", (new, occupation_id, old))

    # Evidence tables have leaf_id in their composite key.  INSERT OR IGNORE
    # keeps any existing human-reviewed target evidence and avoids collisions.
    for table, columns in (
        ("leaf_title_evidence", "title_id,leaf_id,title,method,review_status,evidence_strength,evidence_quote,taxonomy_version"),
        ("leaf_source_occupation", "leaf_id,occupation_id,source_id,native_id,preferred_label,mapping_relation,mapping_method,review_status,evidence_id"),
        ("leaf_alias", "leaf_id,alias_id,source_id,alias,alias_type,evidence_id,provenance"),
        ("leaf_task_evidence", "leaf_id,occupation_id,task_id,source_id,task_type,description,verb,object_text,context_text,evidence_tier,evidence_id"),
        ("leaf_skill_profile", "leaf_id,occupation_id,skill_id,source_id,normalized_label,kind,relation,hot_technology,in_demand,evidence_tier,evidence_id"),
        ("leaf_technology_profile", "leaf_id,occupation_id,skill_id,source_id,technology_label,relation,role_context,evidence_id"),
    ):
        select_cols = columns.replace("leaf_id", "?")
        con.execute(
            f"INSERT OR IGNORE INTO {table}({columns}) SELECT {select_cols} FROM {table} WHERE leaf_id=?",
            (new, old),
        )
        con.execute(f"DELETE FROM {table} WHERE leaf_id=?", (old,))
    con.execute("DELETE FROM leaf_confusion_pair WHERE leaf_id=? OR sibling_leaf_id=?", (old, old))
    con.execute("DELETE FROM leaf_profile WHERE leaf_id=?", (old,))
    con.execute("DELETE FROM leaf WHERE leaf_id=?", (old,))


def _abstain_generic_leaf(con: sqlite3.Connection, leaf: str, parent: str) -> int:
    """Keep parent routing but remove an uninformative leaf assignment."""
    title_ids = [r[0] for r in con.execute("SELECT title_id FROM title_classification WHERE leaf_id=?", (leaf,))]
    con.execute(
        "UPDATE title_classification SET leaf_id=NULL,method='parent_only_abstention_residual_sink',rule_id='taxonomy_residual_generic_sink' WHERE leaf_id=?",
        (leaf,),
    )
    con.execute(
        "UPDATE occupation_classification SET leaf_id=NULL,method='parent_only_abstention_residual_sink',rule_id='taxonomy_residual_generic_sink' WHERE leaf_id=?",
        (leaf,),
    )
    if title_ids:
        con.executemany("UPDATE input_title SET resolution_status='parent_only' WHERE title_id=?", [(x,) for x in title_ids])
    for table in (
        "leaf_title_evidence",
        "leaf_source_occupation",
        "leaf_alias",
        "leaf_task_evidence",
        "leaf_skill_profile",
        "leaf_technology_profile",
    ):
        con.execute(f"DELETE FROM {table} WHERE leaf_id=?", (leaf,))
    con.execute("DELETE FROM leaf_confusion_pair WHERE leaf_id=? OR sibling_leaf_id=?", (leaf, leaf))
    con.execute("DELETE FROM leaf_profile WHERE leaf_id=?", (leaf,))
    con.execute("DELETE FROM leaf WHERE leaf_id=?", (leaf,))
    return len(title_ids)


def apply() -> dict[str, object]:
    if not DB.exists():
        raise FileNotFoundError(DB)
    backup = DB.with_name("it_knowledge.sqlite.pre_residual_taxonomy.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        current_parents = {r[0] for r in con.execute("SELECT parent_id FROM parent")}
        if not set(PARENT_MOVES).issubset(current_parents):
            raise RuntimeError("Residual migration already applied or source parents are missing")
        before = _counts(con)
        with con:
            for old, new in PARENT_MOVES.items():
                _move_parent(con, old, new)

            for old, new in LEAF_MERGES.items():
                _merge_leaf(con, old, new)

            abstained = {
                leaf: _abstain_generic_leaf(con, leaf, parent)
                for leaf, parent in GENERIC_SINKS.items()
            }

            for leaf, definition in LEAF_DEFINITIONS.items():
                con.execute("UPDATE leaf SET definition=? WHERE leaf_id=?", (definition, leaf))
                con.execute("UPDATE leaf_profile SET definition=?,taxonomy_version=? WHERE leaf_id=?", (definition, VERSION, leaf))

            for pair_id, leaf, sibling, disambiguator, hard_negative in CONFUSION_PAIRS:
                con.execute(
                    "INSERT OR IGNORE INTO leaf_confusion_pair(pair_id,leaf_id,sibling_leaf_id,disambiguator,hard_negative_rule,taxonomy_version,reviewer,review_status) VALUES(?,?,?,?,?,?,?,?)",
                    (pair_id, leaf, sibling, disambiguator, hard_negative, VERSION, "taxonomy_review", "REVIEW_REQUIRED"),
                )

            crosswalk_rows = []
            for old, new in PARENT_MOVES.items():
                crosswalk_rows.append(("parent", old, "parent", new, "functional_parent_fold", "Single-leaf parent removed; retained functional leaf under the destination parent.", VERSION))
            for old, new in LEAF_MERGES.items():
                crosswalk_rows.append(("leaf", old, "leaf", new, "functional_leaf_merge", "Programmer is a modern synonym of the general software-developer leaf.", VERSION))
            for old, parent in GENERIC_SINKS.items():
                crosswalk_rows.append(("leaf", old, "parent", parent, "generic_sink_abstention", "Generic title retained at parent level; no specialized leaf evidence.", VERSION))
            con.executemany(
                "INSERT OR REPLACE INTO taxonomy_v2_crosswalk VALUES(?,?,?,?,?,?,?)",
                crosswalk_rows,
            )
            con.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [
                    ("taxonomy_version", VERSION),
                    ("taxonomy_v2_version", VERSION),
                    ("residual_taxonomy_migration_at", now),
                    ("residual_taxonomy_policy", "Fold single-leaf parents; abstain generic sinks; keep sustainable IT and hardware support as functional leaves."),
                    ("systems_engineer_scope", "Systems integration and MBSE; not generic server administration."),
                    ("embedded_boundary", "Embedded designer is hardware/PCB; embedded developer is firmware/software."),
                ],
            )
            con.execute("UPDATE family SET taxonomy_version=?", (VERSION,))
            con.execute("PRAGMA user_version=115")
        con.execute("PRAGMA foreign_keys=ON")
        violations = con.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign-key violations after migration: {violations[:5]}")
        after = _counts(con)
        report = {
            "taxonomy_version": VERSION,
            "applied_at": now,
            "counts_before": before,
            "counts_after": after,
            "parent_folds": PARENT_MOVES,
            "leaf_merges": LEAF_MERGES,
            "generic_sink_abstentions": abstained,
            "clarified_leaves": list(LEAF_DEFINITIONS),
            "confusion_pairs_added": [x[0] for x in CONFUSION_PAIRS],
            "count_note": "The residual stage retained distinct sustainable-IT and hardware-support leaves (24 parents/125 leaves). The follow-up generic-development retirement leaves the current canonical tree at 24 parents/124 leaves.",
            "rollback_backup": str(backup),
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"backup": str(backup), "report": str(REPORT), **after}
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(apply(), indent=2))
