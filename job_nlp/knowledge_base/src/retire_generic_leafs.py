"""Retire broad/generic leaves and preserve only evidenced functional paths.

The live taxonomy uses multi-path occupation output.  Generic security,
telecom, IT, web and mobile buckets therefore add little routing value and
are removed here.  Explicit titles are remapped to surviving leaves; titles
that do not justify a specialization remain parent-only.
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
REPORT = ROOT.parent / "artifacts" / "reports" / "generic_leaf_retirement.json"
BACKUP = (
    ROOT.parents[1]
    / "archive"
    / "job_nlp"
    / "taxonomy_migrations"
    / "generic_leaf_retirement"
    / "it_knowledge.sqlite.pre_generic_leaf_retirement.bak"
)
VERSION = "IT_KB_2.7.0_REMOVE_GENERIC_LEAVES"
METHOD = "generic_leaf_retirement_v1"
RULE = "generic_leaf_retirement_v1"
RETIRED = {
    "SECURITY_SPECIALIST_GENERAL",
    "TELECOM_SPECIALIST_GENERAL",
    "IT_GENERALIST",
    "WEB_DEVELOPER",
    "MOBILE_DEVELOPER",
}


def _norm(value: str) -> str:
    value = str(value or "").casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9+#.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def replacement_leaf_ids(old_leaf: str, title: str) -> list[str]:
    """Return ordered surviving leaves; an empty list means parent-only."""
    t = _norm(title)
    if old_leaf == "SECURITY_SPECIALIST_GENERAL":
        if "forensic" in t:
            return ["DIGITAL_FORENSICS"]
        if "incident" in t or "response" in t:
            return ["INCIDENT_RESPONDER"]
        if "threat" in t or "intelligence" in t:
            return ["THREAT_INTELLIGENCE"]
        if "analyst" in t:
            return ["SECURITY_ANALYST"]
        if "engineer" in t or "engineering" in t or "architect" in t:
            return ["SECURITY_ENGINEER"]
        # A generic security specialist is genuinely ambiguous between
        # operational analysis and security engineering.
        return ["SECURITY_ANALYST", "SECURITY_ENGINEER"]

    if old_leaf == "TELECOM_SPECIALIST_GENERAL":
        if "analyst" in t:
            return ["TELECOM_ANALYST"]
        if "engineer" in t or "engineering" in t:
            return ["TELECOM_ENGINEER"]
        return ["TELECOM_ENGINEER", "TELECOM_ANALYST"]

    if old_leaf == "IT_GENERALIST":
        if "resilience" in t or "disaster recovery" in t:
            return ["DISASTER_RECOVERY"]
        if "advisor" in t or "consult" in t:
            return ["IT_CONSULTANT"]
        # Expert, officer, assistant, generalist and all-other titles have no
        # defensible leaf without duties or technologies.
        return []

    if old_leaf == "WEB_DEVELOPER":
        if "web infrastructure" in t:
            return ["BACKEND_DEVELOPER", "CLOUD_SOFTWARE_DEVELOPER"]
        if "web architect" in t:
            return ["SOFTWARE_ARCHITECT", "FULLSTACK_DEVELOPER"]
        if "web content" in t:
            return ["FRONTEND_DEVELOPER"]
        if "digital media" in t or "multimedia" in t:
            return ["FRONTEND_DEVELOPER"]
        if "specialist" in t and not any(x in t for x in ("developer", "programmer", "engineer")):
            return []
        if "consultant" in t and "web" not in t and "internet" not in t:
            return []
        if "php" in t or "python" in t or "java" in t or ".net" in t or "xml" in t:
            return ["BACKEND_DEVELOPER", "FULLSTACK_DEVELOPER"]
        if "e-commerce" in t or "application" in t or "intranet" in t:
            return ["FULLSTACK_DEVELOPER", "BACKEND_DEVELOPER", "FRONTEND_DEVELOPER"]
        if any(x in t for x in ("web", "website", "internet")):
            return ["FULLSTACK_DEVELOPER", "FRONTEND_DEVELOPER", "BACKEND_DEVELOPER"]
        return []

    if old_leaf == "MOBILE_DEVELOPER":
        if "game" in t:
            return ["GAME_DEVELOPER", "ANDROID_DEVELOPER", "IOS_DEVELOPER"]
        if any(x in t for x in ("mobile", "handheld", "cell phone", "smartphone")):
            return ["ANDROID_DEVELOPER", "IOS_DEVELOPER"]
        return []

    return []


def _path(con: sqlite3.Connection, leaf_id: str) -> tuple[str, str]:
    row = con.execute(
        """SELECT p.family_id,p.parent_id FROM leaf l
           JOIN parent p ON p.parent_id=l.parent_id WHERE l.leaf_id=?""",
        (leaf_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"replacement leaf does not exist: {leaf_id}")
    return str(row[0]), str(row[1])


def _insert_title_evidence(
    con: sqlite3.Connection, *, title_id: str, title: str, targets: list[str]
) -> None:
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


def _prune_json(value: object) -> tuple[object, int]:
    removed = 0
    if isinstance(value, list):
        kept = []
        for item in value:
            if isinstance(item, dict) and (
                item.get("leaf_id") in RETIRED or item.get("sibling_leaf_id") in RETIRED
            ):
                removed += 1
                continue
            item, count = _prune_json(item)
            removed += count
            kept.append(item)
        return kept, removed
    if isinstance(value, dict):
        if value.get("leaf_id") in RETIRED:
            return None, 1
        result = {}
        for key, item in value.items():
            item, count = _prune_json(item)
            removed += count
            result[key] = item
        return result, removed
    return value, 0


def _clean_custom_profile_references(con: sqlite3.Connection) -> int:
    changed = 0
    for profile_id, raw in con.execute(
        "SELECT profile_id,sibling_disambiguators_json FROM leaf_custom_profile"
    ):
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        cleaned, removed = _prune_json(value)
        if removed:
            con.execute(
                "UPDATE leaf_custom_profile SET sibling_disambiguators_json=? WHERE profile_id=?",
                (json.dumps(cleaned, ensure_ascii=False), profile_id),
            )
            changed += 1
    return changed


def _evidence_references(con: sqlite3.Connection) -> set[str]:
    refs: set[str] = set()
    tables = [
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    for table in tables:
        if table == "evidence":
            continue
        columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        if "evidence_id" in columns:
            refs.update(
                str(row[0])
                for row in con.execute(
                    f"SELECT evidence_id FROM {table} WHERE evidence_id IS NOT NULL"
                )
            )
    return refs


def _clean_evidence_records(con: sqlite3.Connection) -> dict[str, int]:
    refs = _evidence_references(con)
    old_markers = tuple(RETIRED)
    rows = con.execute("SELECT evidence_id,file_id,record_json FROM evidence").fetchall()
    cleaned = deleted = 0
    title_prefix = "EVIDENCE:TITLE_ENRICHMENT:TITLE:"
    for evidence_id, file_id, record_json in rows:
        if not any(marker in str(record_json) for marker in old_markers):
            continue
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
                    "source_artifact": "generic_leaf_retirement",
                }
                con.execute(
                    "UPDATE evidence SET record_json=? WHERE evidence_id=?",
                    (json.dumps(replacement, ensure_ascii=False), evidence_id),
                )
                cleaned += 1
                continue
        if evidence_id not in refs:
            con.execute("DELETE FROM evidence WHERE evidence_id=?", (evidence_id,))
            deleted += 1
            continue
        try:
            value = json.loads(record_json)
        except (TypeError, json.JSONDecodeError):
            continue
        value, removed = _prune_json(value)
        if removed:
            con.execute(
                "UPDATE evidence SET record_json=? WHERE evidence_id=?",
                (json.dumps(value, ensure_ascii=False), evidence_id),
            )
            cleaned += 1
    return {"cleaned_evidence_records": cleaned, "deleted_unreferenced_evidence_records": deleted}


def _parent_path(con: sqlite3.Connection, old_leaf: str) -> tuple[str, str]:
    row = con.execute(
        """SELECT p.family_id,p.parent_id FROM leaf l JOIN parent p ON p.parent_id=l.parent_id
           WHERE l.leaf_id=?""",
        (old_leaf,),
    ).fetchone()
    if row is None:
        return "UNKNOWN", "UNKNOWN"
    return str(row[0]), str(row[1])


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
        existing = {
            str(row[0]) for row in con.execute("SELECT leaf_id FROM leaf WHERE leaf_id IN (%s)" % ",".join("?" * len(RETIRED)), tuple(RETIRED))
        }
        valid_leaves = {str(row[0]) for row in con.execute("SELECT leaf_id FROM leaf")}
        stats: dict[str, dict[str, int]] = {}
        with con:
            for old_leaf in sorted(existing):
                family_id, parent_id = _parent_path(con, old_leaf)
                title_rows = [
                    dict(row)
                    for row in con.execute(
                        """SELECT tc.title_id,i.title,tc.leaf_id,tc.review_status
                           FROM title_classification tc JOIN input_title i USING(title_id)
                           WHERE tc.leaf_id=? ORDER BY i.original_row_number""",
                        (old_leaf,),
                    )
                ]
                alternative_title_ids = {
                    str(row[0])
                    for row in con.execute(
                        "SELECT title_id FROM leaf_title_evidence WHERE leaf_id=?", (old_leaf,)
                    )
                }
                all_title_ids = {str(row["title_id"]) for row in title_rows} | alternative_title_ids
                remapped = parent_only = alternatives = 0
                for title_id in sorted(all_title_ids):
                    title_row = con.execute(
                        "SELECT title FROM input_title WHERE title_id=?", (title_id,)
                    ).fetchone()
                    if title_row is None:
                        continue
                    title = str(title_row[0])
                    primary = con.execute(
                        """SELECT family_id,parent_id,leaf_id,review_status
                           FROM title_classification WHERE title_id=?""",
                        (title_id,),
                    ).fetchone()
                    targets = [
                        leaf for leaf in replacement_leaf_ids(old_leaf, title)
                        if leaf in valid_leaves and leaf not in RETIRED
                    ]
                    con.execute(
                        "DELETE FROM leaf_title_evidence WHERE title_id=? AND leaf_id=?",
                        (title_id, old_leaf),
                    )
                    if primary is not None and str(primary[2] or "") == old_leaf:
                        if targets:
                            new_family, new_parent = _path(con, targets[0])
                            con.execute(
                                """UPDATE title_classification SET family_id=?,parent_id=?,leaf_id=?,
                                   method=?,rule_id=?,review_status=? WHERE title_id=?""",
                                (new_family, new_parent, targets[0], METHOD, RULE, "manual_complete", title_id),
                            )
                            con.execute(
                                """UPDATE input_title SET provided_it_label=?,resolution_status=?,scope='core'
                                   WHERE title_id=?""",
                                (f"{new_family}/{new_parent}/{targets[0]}", "source_supported_proposal", title_id),
                            )
                            remapped += 1
                        else:
                            con.execute(
                                """UPDATE title_classification SET family_id=?,parent_id=?,leaf_id=NULL,
                                   method=?,rule_id=?,review_status=? WHERE title_id=?""",
                                (family_id, parent_id, METHOD, RULE, "parent_only_reviewed", title_id),
                            )
                            con.execute(
                                """UPDATE input_title SET provided_it_label=?,resolution_status=?
                                   WHERE title_id=?""",
                                (f"{family_id}/{parent_id}/", "parent_only_proposal", title_id),
                            )
                            parent_only += 1
                    if targets:
                        _insert_title_evidence(con, title_id=title_id, title=title, targets=targets)
                        alternatives += max(0, len(targets) - 1)

                # Source occupations remain useful parent context but cannot
                # keep a deleted leaf alive.
                con.execute(
                    """UPDATE occupation_classification SET family_id=?,parent_id=?,leaf_id=NULL,
                       mapping_relation='parent_only',method=?,review_status='proposed',rule_id=?
                       WHERE leaf_id=?""",
                    (family_id, parent_id, METHOD, RULE, old_leaf),
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
                    con.execute(f"DELETE FROM {table} WHERE leaf_id=?", (old_leaf,))
                con.execute(
                    "DELETE FROM leaf_confusion_pair WHERE leaf_id=? OR sibling_leaf_id=?",
                    (old_leaf, old_leaf),
                )
                con.execute(
                    "DELETE FROM taxonomy_v2_crosswalk WHERE (old_level='leaf' AND old_id=?) OR (new_level='leaf' AND new_id=?)",
                    (old_leaf, old_leaf),
                )
                con.execute("DELETE FROM leaf WHERE leaf_id=?", (old_leaf,))
                stats[old_leaf] = {
                    "titles_remapped": remapped,
                    "titles_parent_only": parent_only,
                    "alternative_paths": alternatives,
                    "titles_affected": len(all_title_ids),
                }

            cleaned_profiles = _clean_custom_profile_references(con)
            evidence_stats = _clean_evidence_records(con)
            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                ("taxonomy_version", VERSION),
            )
            con.execute("PRAGMA user_version=119")

        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")

        report = {
            "status": "applied" if existing else "already_applied",
            "taxonomy_version": VERSION,
            "applied_at": now,
            "removed_leaves": sorted(RETIRED),
            "not_found_before_migration": sorted(RETIRED - existing),
            "replacement_policy": "specific platform/security titles use functional leaves; generic titles remain parent-only; valid alternatives are retained",
            "per_leaf": stats,
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
            "cleaned_custom_profiles": cleaned_profiles,
            **evidence_stats,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
