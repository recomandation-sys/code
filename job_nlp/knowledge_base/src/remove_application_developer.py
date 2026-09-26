"""Retire the generic ``APPLICATION_DEVELOPER`` leaf from the live KB.

The generic label is an ambiguity sink: a title such as ``Software Engineer``
does not identify a backend, web, desktop, mobile or systems specialization.
This migration keeps the software-development parent, routes titles with
explicit evidence to the narrowest surviving leaf, and stores valid
alternatives in ``leaf_title_evidence`` for reviewed-title retrieval.  Truly
generic or managerial titles remain parent-only instead of receiving a false
leaf.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "it_knowledge.sqlite"
REPORT = ROOT.parent / "artifacts" / "reports" / "application_developer_retirement.json"
BACKUP = (
    ROOT.parents[1]
    / "archive"
    / "job_nlp"
    / "taxonomy_migrations"
    / "application_developer_retirement"
    / "it_knowledge.sqlite.pre_application_developer_removal.bak"
)
OLD_LEAF = "APPLICATION_DEVELOPER"
VERSION = "IT_KB_2.6.0_REMOVE_GENERIC_APPLICATION_LEAF"
METHOD = "application_developer_retirement_v1"
RULE = "application_developer_retirement_v1"


def _norm(value: str) -> str:
    value = str(value or "").casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9+#.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


# Returned in priority order.  The first entry is the primary reviewed route;
# the remaining entries are retained as valid alternatives for semantic title
# retrieval.  Empty lists intentionally mean parent-only: the title is useful
# context but does not justify inventing a specialization.
def target_leaf_ids(title: str) -> list[str]:
    t = _norm(title)

    # Explicit technical signals are safer than the generic developer noun.
    if "algorithm" in t:
        return ["ML_ENGINEER", "BACKEND_DEVELOPER"]
    if "analyst programmer" in t or "programmer analyst" in t:
        return ["SYSTEMS_ANALYST", "BACKEND_DEVELOPER"]
    if "lotus notes" in t or "office developer" in t:
        return ["DESKTOP_DEVELOPER"]
    if "asp.net" in t or ".net" in t:
        return ["BACKEND_DEVELOPER", "DESKTOP_DEVELOPER"]
    if "c++" in t or re.search(r"\bc developer\b", t) or "computer language" in t:
        return ["SYSTEMS_PROGRAMMER", "BACKEND_DEVELOPER"]
    if "object oriented programmer" in t or "object-oriented programmer" in title.casefold():
        return ["BACKEND_DEVELOPER", "SYSTEMS_PROGRAMMER"]
    if "java" in t or "python" in t:
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER"]
    if "ict system developer" in t or "it programmer" in t:
        return ["SYSTEMS_PROGRAMMER", "BACKEND_DEVELOPER"]
    if "core software" in t:
        return ["SYSTEMS_PROGRAMMER", "BACKEND_DEVELOPER"]
    if "client server" in t:
        return ["BACKEND_DEVELOPER"]
    if "application designer" in t:
        return ["SOFTWARE_ARCHITECT", "FULLSTACK_DEVELOPER"]
    if "application programmer analyst" in t:
        return ["SYSTEMS_ANALYST", "BACKEND_DEVELOPER"]
    if "application programmer" in t:
        return ["BACKEND_DEVELOPER", "SOFTWARE_ARCHITECT"]
    if "solution" in t and "developer" in t:
        return ["SOFTWARE_ARCHITECT", "BACKEND_DEVELOPER"]
    if "cloud" in t and ("developer" in t or "software engineer" in t):
        return ["CLOUD_SOFTWARE_DEVELOPER", "BACKEND_DEVELOPER"]
    if "enterprise application" in t or "business application" in t:
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER"]
    if "application software" in t or "software applications" in t:
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER"]
    if "applications software" in t:
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER"]
    if "applications developer" in t or "application developer" in t:
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER", "FRONTEND_DEVELOPER"]
    if t in {"business programmer", "developer programmer", "software programmer"}:
        return ["BACKEND_DEVELOPER", "SYSTEMS_PROGRAMMER"]
    if t in {"computer programmer", "programmer"}:
        return []
    if t in {"app coder", "app developer", "app programmer"}:
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER", "FRONTEND_DEVELOPER"]
    if "computer applications" in t:
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER"]
    if t in {"developer", "software developer", "software engineer", "senior software engineer"}:
        return []
    if "software development engineer" in t or t == "sde":
        return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER"]
    if "software engineer" in t or "software developer" in t:
        return []
    if "software specialist" in t or "software computer specialist" in t:
        return []
    if any(word in t for word in ("manager", "director", "supervisor")):
        return []
    # Do not guess for a title not covered by an explicit rule.
    return []


def _path(con: sqlite3.Connection, leaf_id: str) -> tuple[str, str]:
    row = con.execute(
        "SELECT p.family_id,p.parent_id FROM leaf l JOIN parent p ON p.parent_id=l.parent_id WHERE l.leaf_id=?",
        (leaf_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"replacement leaf does not exist: {leaf_id}")
    return str(row[0]), str(row[1])


def _insert_title_evidence(
    con: sqlite3.Connection,
    *,
    title_id: str,
    title: str,
    targets: list[str],
) -> None:
    con.execute("DELETE FROM leaf_title_evidence WHERE title_id=? AND leaf_id=?", (title_id, OLD_LEAF))
    for leaf_id in targets:
        con.execute(
            """INSERT OR REPLACE INTO leaf_title_evidence(
                 title_id,leaf_id,title,method,review_status,evidence_strength,
                 evidence_quote,taxonomy_version)
               VALUES(?,?,?,?,?,?,?,?)""",
            (
                title_id,
                leaf_id,
                title,
                METHOD,
                "manual_complete",
                "reviewed_title_alternative" if len(targets) > 1 else "reviewed_title_mapping",
                title,
                VERSION,
            ),
        )


def _repair_existing_parent_only_titles(con: sqlite3.Connection) -> dict[str, int]:
    """Backfill explicit routes when this idempotent migration runs again.

    The first release deliberately left abbreviations such as ``App Developer``
    parent-only.  They are now represented by a reviewed alternative set, while
    genuinely generic/managerial titles remain parent-only.
    """
    rows = [
        dict(row)
        for row in con.execute(
            """SELECT tc.title_id,i.title,tc.family_id,tc.parent_id
               FROM title_classification tc JOIN input_title i USING(title_id)
               WHERE tc.method=? AND tc.leaf_id IS NULL""",
            (METHOD,),
        )
    ]
    if not rows:
        return {"repaired_titles": 0, "repaired_alternatives": 0}
    valid = {row[0] for row in con.execute("SELECT leaf_id FROM leaf")}
    family_id, parent_id = _path(con, "BACKEND_DEVELOPER")
    repaired = alternatives = 0
    for row in rows:
        targets = target_leaf_ids(row["title"])
        targets = [leaf for leaf in targets if leaf in valid and leaf != OLD_LEAF]
        if not targets:
            continue
        primary_family, primary_parent = _path(con, targets[0])
        con.execute(
            """UPDATE title_classification
               SET family_id=?,parent_id=?,leaf_id=?,review_status=?
               WHERE title_id=? AND method=?""",
            (primary_family, primary_parent, targets[0], "manual_complete", row["title_id"], METHOD),
        )
        con.execute(
            "UPDATE input_title SET provided_it_label=?,resolution_status=? WHERE title_id=?",
            (f"{primary_family}/{primary_parent}/{targets[0]}", "source_supported_proposal", row["title_id"]),
        )
        _insert_title_evidence(con, title_id=row["title_id"], title=row["title"], targets=targets)
        repaired += 1
        alternatives += max(0, len(targets) - 1)
    # A manually completed functional route is eligible for deterministic
    # lookup even when the original source row was still marked ``review``.
    # Generic/managerial rows remain review + parent-only.
    con.execute(
        """UPDATE input_title SET scope='core'
           WHERE title_id IN (
             SELECT title_id FROM title_classification
             WHERE method=? AND leaf_id IS NOT NULL
           )""",
        (METHOD,),
    )
    return {"repaired_titles": repaired, "repaired_alternatives": alternatives}


def _clean_custom_profile_references(con: sqlite3.Connection) -> int:
    """Remove retired-leaf sibling rules from active custom-profile JSON."""
    changed = 0
    for row in con.execute("SELECT profile_id,sibling_disambiguators_json FROM leaf_custom_profile"):
        try:
            values = json.loads(row[1])
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(values, list):
            continue
        cleaned = [
            item for item in values
            if not (isinstance(item, dict) and item.get("sibling_leaf_id") == OLD_LEAF)
        ]
        if len(cleaned) != len(values):
            con.execute(
                "UPDATE leaf_custom_profile SET sibling_disambiguators_json=? WHERE profile_id=?",
                (json.dumps(cleaned, ensure_ascii=False), row[0]),
            )
            changed += 1
    return changed


def _clean_evidence_records(con: sqlite3.Connection) -> dict[str, int]:
    """Remove the retired enum from active evidence while preserving sources.

    The migration deletes the retired leaf, but evidence rows are a shared
    catalog and can outlive the row that originally referenced them.  Keep
    evidence still referenced by a live custom profile (after pruning its
    retired sibling rules); discard otherwise-unreferenced migration records.
    """
    referenced: set[str] = set()
    tables = [
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    for table in tables:
        if table == "evidence":
            # The evidence catalog's own primary key is not a consumer
            # reference; counting it would make every row appear live.
            continue
        columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        if "evidence_id" not in columns:
            continue
        referenced.update(
            str(row[0])
            for row in con.execute(f"SELECT evidence_id FROM {table} WHERE evidence_id IS NOT NULL")
        )

    cleaned = deleted = 0
    rows = con.execute(
        """SELECT evidence_id,file_id,record_json FROM evidence
           WHERE instr(record_json,?)>0
              OR (file_id=? AND record_json='null')""",
        (OLD_LEAF, "FILE:TITLE_ENRICHMENT_125_24_8"),
    ).fetchall()
    title_prefix = "EVIDENCE:TITLE_ENRICHMENT:TITLE:"
    for evidence_id, file_id, record_json in rows:
        # Input-title rows retain their source evidence_id.  Rebuild those
        # eight retired enrichment records from the live classification so the
        # catalog stays traceable without retaining the retired enum.
        if str(evidence_id).startswith(title_prefix):
            title_id = "TITLE:" + str(evidence_id)[len(title_prefix) :]
            current = con.execute(
                """SELECT tc.family_id,tc.parent_id,tc.leaf_id,tc.review_status,i.title
                   FROM title_classification tc JOIN input_title i USING(title_id)
                   WHERE tc.title_id=? ORDER BY tc.method LIMIT 1""",
                (title_id,),
            ).fetchone()
            if current:
                family_id, parent_id, leaf_id, review_status, title = current
                replacement = {
                    "title_id": title_id,
                    "title": title,
                    "family_id": family_id,
                    "parent_id": parent_id,
                    "leaf_id": leaf_id,
                    "method": METHOD,
                    "review_status": review_status,
                    "source_artifact": "application_developer_retirement",
                }
                con.execute(
                    "UPDATE evidence SET record_json=? WHERE evidence_id=?",
                    (json.dumps(replacement, ensure_ascii=False), evidence_id),
                )
                cleaned += 1
                continue
        if evidence_id not in referenced:
            con.execute("DELETE FROM evidence WHERE evidence_id=?", (evidence_id,))
            deleted += 1
            continue
        try:
            value = json.loads(record_json)
        except (TypeError, json.JSONDecodeError):
            continue
        value, removed = _prune_retired_json(value)
        if removed:
            con.execute(
                "UPDATE evidence SET record_json=? WHERE evidence_id=?",
                (json.dumps(value, ensure_ascii=False), evidence_id),
            )
            cleaned += 1
    # Older idempotent runs may already have replaced an unreferenced retired
    # record with JSON null.  Remove those tombstones from the active catalog.
    for evidence_id, in con.execute("SELECT evidence_id FROM evidence WHERE record_json='null'").fetchall():
        if evidence_id not in referenced:
            con.execute("DELETE FROM evidence WHERE evidence_id=?", (evidence_id,))
            deleted += 1
    return {"cleaned_evidence_records": cleaned, "deleted_unreferenced_evidence_records": deleted}


def _prune_retired_json(value: object) -> tuple[object, int]:
    """Recursively remove dict records whose leaf/sibling id is retired."""
    removed = 0
    if isinstance(value, list):
        kept = []
        for item in value:
            if isinstance(item, dict) and (
                item.get("leaf_id") == OLD_LEAF or item.get("sibling_leaf_id") == OLD_LEAF
            ):
                removed += 1
                continue
            item, count = _prune_retired_json(item)
            removed += count
            kept.append(item)
        return kept, removed
    if isinstance(value, dict):
        if value.get("leaf_id") == OLD_LEAF:
            return None, 1
        result = {}
        for key, item in value.items():
            item, count = _prune_retired_json(item)
            removed += count
            result[key] = item
        return result, removed
    return value, 0


def apply() -> dict[str, object]:
    if not DB.exists():
        raise FileNotFoundError(DB)
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DB, BACKUP)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        row = con.execute("SELECT 1 FROM leaf WHERE leaf_id=?", (OLD_LEAF,)).fetchone()
        if row is None:
            with con:
                repaired = _repair_existing_parent_only_titles(con)
                cleaned_profiles = _clean_custom_profile_references(con)
                cleaned_evidence = _clean_evidence_records(con)
                con.execute(
                    "UPDATE leaf_title_evidence SET taxonomy_version=? WHERE method=?",
                    (VERSION, METHOD),
                )
                con.execute(
                    """INSERT INTO metadata(key,value) VALUES(?,?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                    ("taxonomy_version", VERSION),
                )
            # Keep the migration audit report synchronized on idempotent runs,
            # including any explicit routes repaired after the first release.
            report = {
                "status": "already_applied",
                "taxonomy_version": VERSION,
                "applied_at": now,
                "removed_leaf": OLD_LEAF,
                "replacement_policy": "specific titles route to the narrowest evidenced leaf; generic titles remain parent-only",
                "titles_remapped": con.execute(
                    "SELECT count(*) FROM title_classification WHERE method=? AND leaf_id IS NOT NULL", (METHOD,)
                ).fetchone()[0],
                "titles_parent_only": con.execute(
                    "SELECT count(*) FROM title_classification WHERE method=? AND leaf_id IS NULL", (METHOD,)
                ).fetchone()[0],
                "title_alternative_paths": max(
                    0,
                    con.execute("SELECT count(*) FROM leaf_title_evidence WHERE method=?", (METHOD,)).fetchone()[0]
                    - con.execute("SELECT count(*) FROM title_classification WHERE method=? AND leaf_id IS NOT NULL", (METHOD,)).fetchone()[0],
                ),
                "source_occupations_parent_only": con.execute(
                    "SELECT count(*) FROM occupation_classification WHERE method=? AND leaf_id IS NULL", (METHOD,)
                ).fetchone()[0],
                "counts_after": {
                    "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
                    "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
                    "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
                    "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
                    "leaf_assigned_titles": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NOT NULL").fetchone()[0],
                    "parent_only_titles": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NULL").fetchone()[0],
                    "reviewed_title_evidence_rows": con.execute("SELECT count(*) FROM leaf_title_evidence").fetchone()[0],
                },
                "backup": str(BACKUP),
                **repaired,
            }
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report["cleaned_custom_profiles"] = cleaned_profiles
            report.update(cleaned_evidence)
            REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return report

        title_rows = [
            dict(row)
            for row in con.execute(
                """SELECT tc.title_id,i.title,tc.family_id,tc.parent_id,tc.leaf_id
                   FROM title_classification tc JOIN input_title i USING(title_id)
                   WHERE tc.leaf_id=? ORDER BY i.original_row_number""",
                (OLD_LEAF,),
            )
        ]
        occupation_rows = [
            dict(row)
            for row in con.execute(
                "SELECT occupation_id,family_id,parent_id,leaf_id FROM occupation_classification WHERE leaf_id=?",
                (OLD_LEAF,),
            )
        ]

        planned: list[dict[str, object]] = []
        valid_leaf_ids = {row[0] for row in con.execute("SELECT leaf_id FROM leaf")}
        software_family, software_parent = _path(con, "BACKEND_DEVELOPER")
        for row in title_rows:
            targets = target_leaf_ids(row["title"])
            invalid = [leaf_id for leaf_id in targets if leaf_id not in valid_leaf_ids or leaf_id == OLD_LEAF]
            if invalid:
                raise RuntimeError(f"invalid replacement for {row['title_id']}: {invalid}")
            if targets:
                family_id, parent_id = _path(con, targets[0])
                leaf_id = targets[0]
            else:
                family_id, parent_id, leaf_id = software_family, software_parent, None
            planned.append({**row, "targets": targets, "family_id_new": family_id, "parent_id_new": parent_id, "leaf_id_new": leaf_id})

        with con:
            for item in planned:
                title_id = str(item["title_id"])
                targets = list(item["targets"])
                con.execute(
                    """UPDATE title_classification
                       SET family_id=?,parent_id=?,leaf_id=?,method=?,rule_id=?,review_status=?
                       WHERE title_id=?""",
                    (
                        item["family_id_new"],
                        item["parent_id_new"],
                        item["leaf_id_new"],
                        METHOD,
                        RULE,
                        "manual_complete" if targets else "parent_only_reviewed",
                        title_id,
                    ),
                )
                provided = "/".join(
                    str(value or "") for value in (item["family_id_new"], item["parent_id_new"], item["leaf_id_new"])
                )
                con.execute(
                    """UPDATE input_title SET provided_it_label=?,resolution_status=?,scope=CASE WHEN ? IS NOT NULL THEN 'core' ELSE scope END
                       WHERE title_id=?""",
                    (provided, "source_supported_proposal" if targets else "parent_only_proposal", targets[0] if targets else None, title_id),
                )
                _insert_title_evidence(con, title_id=title_id, title=str(item["title"]), targets=targets)

            # Also repair explicit abbreviations left parent-only by an older
            # run; generic software/manager titles remain intentionally broad.
            _repair_existing_parent_only_titles(con)
            _clean_custom_profile_references(con)
            cleaned_evidence = _clean_evidence_records(con)
            con.execute(
                "UPDATE leaf_title_evidence SET taxonomy_version=? WHERE method=?",
                (VERSION, METHOD),
            )

            # Source occupations are retained as parent-only observations when
            # no unambiguous functional leaf exists; generic manager skills do
            # not contaminate another leaf's evidence profile.
            con.execute(
                """UPDATE occupation_classification
                   SET family_id=?,parent_id=?,leaf_id=NULL,mapping_relation='parent_only',
                       method=?,review_status='proposed',rule_id=?
                   WHERE leaf_id=?""",
                (software_family, software_parent, METHOD, RULE, OLD_LEAF),
            )
            for table in (
                "leaf_source_occupation",
                "leaf_alias",
                "leaf_task_evidence",
                "leaf_skill_profile",
                "leaf_technology_profile",
                "leaf_profile",
                "leaf_custom_profile",
            ):
                con.execute(f"DELETE FROM {table} WHERE leaf_id=?", (OLD_LEAF,))
            con.execute(
                "DELETE FROM leaf_confusion_pair WHERE leaf_id=? OR sibling_leaf_id=?",
                (OLD_LEAF, OLD_LEAF),
            )
            con.execute(
                "DELETE FROM taxonomy_v2_crosswalk WHERE (old_level='leaf' AND old_id=?) OR (new_level='leaf' AND new_id=?)",
                (OLD_LEAF, OLD_LEAF),
            )
            con.execute("DELETE FROM leaf WHERE leaf_id=?", (OLD_LEAF,))
            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                ("taxonomy_version", VERSION),
            )
            con.execute("PRAGMA user_version=118")

        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")

        report = {
            "status": "applied",
            "taxonomy_version": VERSION,
            "applied_at": now,
            "removed_leaf": OLD_LEAF,
            "replacement_policy": "specific titles route to the narrowest evidenced leaf; generic titles remain parent-only",
            "titles_remapped": sum(bool(item["targets"]) for item in planned),
            "titles_parent_only": sum(not item["targets"] for item in planned),
            "title_alternative_paths": sum(max(0, len(item["targets"]) - 1) for item in planned),
            "source_occupations_parent_only": len(occupation_rows),
            "counts_after": {
                "families": con.execute("SELECT count(*) FROM family").fetchone()[0],
                "parents": con.execute("SELECT count(*) FROM parent").fetchone()[0],
                "leaves": con.execute("SELECT count(*) FROM leaf").fetchone()[0],
                "titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
                "leaf_assigned_titles": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NOT NULL").fetchone()[0],
                "parent_only_titles": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NULL").fetchone()[0],
                "reviewed_title_evidence_rows": con.execute("SELECT count(*) FROM leaf_title_evidence").fetchone()[0],
            },
            "backup": str(BACKUP),
            **cleaned_evidence,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
