"""Integrate the reviewed real-world title enrichment into the live KB.

The enrichment artifact adds title variants only.  It does not add taxonomy
nodes and it never overwrites an existing title classification; this preserves
later production corrections such as generic IT-management parent-only paths.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
DB = ROOT / "it_knowledge.sqlite"
SOURCE_ARTIFACT = REPO_ROOT / "archive" / "job_nlp" / "taxonomy_migrations" / "application_developer_retirement" / "title_leaf_parent_family_enriched_124_24_8.json"
REPORT = REPO_ROOT / "job_nlp" / "artifacts" / "reports" / "title_hierarchy" / "enriched_title_integration.json"
BACKUP = DB.with_name("it_knowledge.sqlite.pre_enriched_title_hierarchy.bak")

VERSION = "IT_KB_3.0.0_REAL_WORLD_ENRICHED"
SOURCE_ID = "TITLE_ENRICHMENT"
SOURCE_FILE_ID = "FILE:TITLE_ENRICHMENT_124_24_8"
EXPECTED_NEW_TITLES = 457


def _title_norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or "")).casefold()
    text = text.replace("–", "-").replace("‑", "-")
    for pattern, replacement in (
        (r"\bback[ -]?end\b", "backend"),
        (r"\bfront[ -]?end\b", "frontend"),
        (r"\bfull[- ]?stack\b", "fullstack"),
        (r"\bdev[- ]?ops\b", "devops"),
    ):
        text = re.sub(pattern, replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def _records(payload: dict) -> list[dict]:
    rows: list[dict] = []
    for family in payload["families"]:
        for parent in family["parents"]:
            for leaf in parent["leaves"]:
                for title in leaf.get("titles", []):
                    rows.append(title)
    bottom = payload.get("titles_without_leaf_bottom", {})
    rows.extend(bottom.get("parent_only_titles", []))
    rows.extend(bottom.get("excluded_or_out_of_scope_titles", []))
    return rows


def _path(row: dict) -> tuple[str | None, str | None, str | None]:
    return row.get("family_id"), row.get("parent_id"), row.get("leaf_id")


def _source_hash() -> tuple[str, int, str]:
    raw = SOURCE_ARTIFACT.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw), str(SOURCE_ARTIFACT.relative_to(REPO_ROOT)).replace("\\", "/")


def integrate() -> dict[str, object]:
    if not SOURCE_ARTIFACT.exists():
        raise FileNotFoundError(SOURCE_ARTIFACT)
    payload = json.loads(SOURCE_ARTIFACT.read_text(encoding="utf-8"))
    if payload.get("counts", {}).get("enriched_titles_added") != EXPECTED_NEW_TITLES:
        raise ValueError("Unexpected enriched-title count; refusing partial or different input")

    rows = _records(payload)
    ids = [str(row["title_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Enriched hierarchy contains duplicate title IDs")
    new_rows = [row for row in rows if str(row["title_id"]).startswith("TITLE:ENRICHED_")]
    if len(new_rows) != EXPECTED_NEW_TITLES:
        raise ValueError(f"Expected {EXPECTED_NEW_TITLES} new IDs, found {len(new_rows)}")

    sha256, byte_size, relative_path = _source_hash()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if not BACKUP.exists():
        shutil.copy2(DB, BACKUP)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    added = 0
    try:
        with con:
            con.execute(
                """INSERT INTO source(source_id,name,version,language,url,attribution)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(source_id) DO UPDATE SET version=excluded.version,
                       name=excluded.name, attribution=excluded.attribution""",
                (
                    SOURCE_ID,
                    "Reviewed real-world IT title enrichment",
                    VERSION,
                    "en",
                    None,
                    "User-provided manually reviewed title hierarchy enrichment; not an official occupation source.",
                ),
            )
            con.execute(
                """INSERT INTO source_file(file_id,source_id,relative_path,sha256,byte_size,processing_note)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(file_id) DO UPDATE SET sha256=excluded.sha256,
                       byte_size=excluded.byte_size, relative_path=excluded.relative_path""",
                (
                    SOURCE_FILE_ID,
                    SOURCE_ID,
                    relative_path,
                    sha256,
                    byte_size,
                    "Canonical enriched title hierarchy used for reviewed-title retrieval and exact lookup.",
                ),
            )

            valid_paths = {
                (row["family_id"], row["parent_id"], row["leaf_id"])
                for row in con.execute(
                    """SELECT p.family_id,p.parent_id,l.leaf_id
                       FROM parent p JOIN leaf l ON l.parent_id=p.parent_id"""
                )
            }
            existing = {
                row["title_id"]: row
                for row in con.execute("SELECT title_id,title FROM input_title")
            }
            existing_new = set(existing).intersection(str(row["title_id"]) for row in new_rows)
            for row in new_rows:
                title_id = str(row["title_id"])
                family_id, parent_id, leaf_id = _path(row)
                if (family_id, parent_id, leaf_id) not in valid_paths:
                    raise ValueError(f"Invalid relational path for {title_id}: {_path(row)}")
                if title_id in existing:
                    if existing[title_id]["title"] != row["title"]:
                        raise ValueError(f"Existing title ID has different text: {title_id}")
                    continue

                evidence_id = f"EVIDENCE:TITLE_ENRICHMENT:{title_id}"
                evidence_record = {
                    "title_id": title_id,
                    "title": row["title"],
                    "family_id": family_id,
                    "parent_id": parent_id,
                    "leaf_id": leaf_id,
                    "method": row.get("method", "industry_real_world_enrichment_v1"),
                    "rule_id": row.get("rule_id", "real_world_market_expansion"),
                    "source_artifact": relative_path,
                }
                con.execute(
                    """INSERT INTO evidence(evidence_id,file_id,locator,record_json)
                       VALUES(?,?,?,?)""",
                    (evidence_id, SOURCE_FILE_ID, f"title:{title_id}", json.dumps(evidence_record, ensure_ascii=False, sort_keys=True)),
                )
                scope = row.get("scope") if row.get("scope") in {"core", "conditional", "review", "excluded"} else "core"
                resolution = row.get("resolution_status") or "source_supported_proposal"
                provided = "/".join(x or "" for x in (family_id, parent_id, leaf_id))
                con.execute(
                    """INSERT INTO input_title(
                         title_id,original_row_number,title,normalized_title,provided_it_label,
                         provided_review_status,scope,resolution_status,evidence_id)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        title_id,
                        int(row["original_row_number"]),
                        row["title"],
                        _title_norm(row["title"]),
                        provided,
                        row.get("review_status") or "manual_complete",
                        scope,
                        resolution,
                        evidence_id,
                    ),
                )
                con.execute(
                    """INSERT INTO title_classification(
                         title_id,family_id,parent_id,leaf_id,method,rule_id,review_status)
                       VALUES(?,?,?,?,?,?,?)""",
                    (
                        title_id,
                        family_id,
                        parent_id,
                        leaf_id,
                        row.get("method") or "industry_real_world_enrichment_v1",
                        row.get("rule_id") or "real_world_market_expansion",
                        row.get("review_status") or "manual_complete",
                    ),
                )
                con.execute(
                    """INSERT INTO leaf_title_evidence(
                         title_id,leaf_id,title,method,review_status,evidence_strength,
                         evidence_quote,taxonomy_version)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        title_id,
                        leaf_id,
                        row["title"],
                        row.get("method") or "industry_real_world_enrichment_v1",
                        row.get("review_status") or "manual_complete",
                        "reviewed_title_mapping",
                        row["title"],
                        VERSION,
                    ),
                )
                added += 1

            total_titles = con.execute("SELECT count(*) FROM input_title").fetchone()[0]
            leaf_titles = con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NOT NULL").fetchone()[0]
            parent_only = con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NULL").fetchone()[0]
            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                ("title_hierarchy_enrichment_version", VERSION),
            )
            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                ("title_hierarchy_enrichment_source", relative_path),
            )
            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                ("title_hierarchy_enrichment_added", str(EXPECTED_NEW_TITLES)),
            )
            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                ("title_hierarchy_enrichment_applied_at", now),
            )
            con.execute("PRAGMA user_version=117")

        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")
        report = {
            "taxonomy_version": VERSION,
            "applied_at": now,
            "source_artifact": str(SOURCE_ARTIFACT),
            "source_sha256": sha256,
            "source_bytes": byte_size,
            "expected_new_titles": EXPECTED_NEW_TITLES,
            "new_titles_added_this_run": added,
            "already_integrated_new_titles": len(existing_new),
            "total_titles": con.execute("SELECT count(*) FROM input_title").fetchone()[0],
            "leaf_assigned_titles": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NOT NULL").fetchone()[0],
            "parent_only_titles": con.execute("SELECT count(*) FROM title_classification WHERE leaf_id IS NULL").fetchone()[0],
            "excluded_titles": con.execute("SELECT count(*) FROM taxonomy_v2_excluded_title").fetchone()[0],
            "preserved_latest_management_correction": True,
            "backup": str(BACKUP),
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(integrate(), ensure_ascii=False, indent=2))
