"""Stage analyst-curated evidence for a reviewed leaf-profile batch.

Custom profiles are deliberately separate from official source occupations and
remain outside the semantic vector cache until an independent review changes
their vector gate to ``APPROVED``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
DB = ROOT / "it_knowledge.sqlite"
DEFAULT_BATCH = ROOT / "custom_sources" / "leaf_profiles" / "batch_01_core_unprofiled.json"
REPORT_DIR = REPO_ROOT / "job_nlp" / "artifacts" / "reports" / "leaf_evidence"
USER_VERSION = 118


DDL = """
CREATE TABLE IF NOT EXISTS leaf_custom_profile (
    profile_id TEXT PRIMARY KEY,
    leaf_id TEXT NOT NULL REFERENCES leaf,
    source_id TEXT NOT NULL REFERENCES source,
    evidence_id TEXT NOT NULL REFERENCES evidence,
    batch_id TEXT NOT NULL,
    description TEXT NOT NULL,
    primary_outcome TEXT NOT NULL,
    in_scope_json TEXT NOT NULL CHECK(json_valid(in_scope_json)),
    out_of_scope_json TEXT NOT NULL CHECK(json_valid(out_of_scope_json)),
    tasks_json TEXT NOT NULL CHECK(json_valid(tasks_json)),
    professional_skills_json TEXT NOT NULL CHECK(json_valid(professional_skills_json)),
    technologies_json TEXT NOT NULL CHECK(json_valid(technologies_json)),
    sibling_disambiguators_json TEXT NOT NULL CHECK(json_valid(sibling_disambiguators_json)),
    review_status TEXT NOT NULL CHECK(review_status IN ('DRAFT','REVIEW_REQUIRED','APPROVED')),
    vector_status TEXT NOT NULL CHECK(vector_status IN ('NOT_INCLUDED_UNTIL_APPROVED','APPROVED')),
    reviewer TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(leaf_id,batch_id)
);
"""


def stage(batch_path: Path = DEFAULT_BATCH) -> dict[str, object]:
    batch_path = Path(batch_path).resolve()
    payload = json.loads(batch_path.read_text(encoding="utf-8"))
    source = payload["source"]
    batch_id = str(payload["batch_id"])
    profiles = payload["profiles"]
    if not profiles:
        raise ValueError("Custom profile batch is empty")
    if len({profile["leaf_id"] for profile in profiles}) != len(profiles):
        raise ValueError("Custom profile batch contains duplicate leaves")
    if payload["review_policy"]["review_status"] != "REVIEW_REQUIRED":
        raise ValueError("Only REVIEW_REQUIRED custom batches may be staged automatically")

    source_file_id = f"FILE:CUSTOM_LEAF_PROFILE:{batch_id}"
    relative_path = str(batch_path.relative_to(REPO_ROOT)).replace("\\", "/")
    raw = batch_path.read_bytes()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    source_bytes = len(raw)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    backup = DB.with_name(f"it_knowledge.sqlite.pre_custom_leaf_profile_{batch_id}.bak")
    if not backup.exists():
        shutil.copy2(DB, backup)

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    created = 0
    try:
        with con:
            con.executescript(DDL)
            valid_leaves = {row[0] for row in con.execute("SELECT leaf_id FROM leaf")}
            unknown = sorted(set(profile["leaf_id"] for profile in profiles) - valid_leaves)
            if unknown:
                raise ValueError(f"Unknown canonical leaves: {', '.join(unknown)}")

            con.execute(
                """INSERT INTO source(source_id,name,version,language,url,attribution)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(source_id) DO UPDATE SET name=excluded.name,
                       version=excluded.version,attribution=excluded.attribution""",
                (
                    source["source_id"],
                    source["name"],
                    source["version"],
                    source["language"],
                    None,
                    source["description"],
                ),
            )
            con.execute(
                """INSERT INTO source_file(file_id,source_id,relative_path,sha256,byte_size,processing_note)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(file_id) DO UPDATE SET sha256=excluded.sha256,
                       byte_size=excluded.byte_size,processing_note=excluded.processing_note""",
                (
                    source_file_id,
                    source["source_id"],
                    relative_path,
                    source_sha256,
                    source_bytes,
                    "Analyst-curated leaf evidence; not official occupation provenance.",
                ),
            )

            for profile in profiles:
                leaf_id = profile["leaf_id"]
                evidence_id = f"EVIDENCE:CUSTOM_LEAF_PROFILE:{batch_id}:{leaf_id}"
                profile_id = f"CUSTOM_PROFILE:{batch_id}:{leaf_id}"
                record = {
                    "batch_id": batch_id,
                    "leaf_id": leaf_id,
                    "profile": profile,
                    "review_policy": payload["review_policy"],
                    "source": source,
                }
                con.execute(
                    """INSERT INTO evidence(evidence_id,file_id,locator,record_json)
                       VALUES(?,?,?,?)
                       ON CONFLICT(evidence_id) DO UPDATE SET file_id=excluded.file_id,
                           locator=excluded.locator,record_json=excluded.record_json""",
                    (evidence_id, source_file_id, f"profile:{leaf_id}", json.dumps(record, ensure_ascii=False, sort_keys=True)),
                )
                con.execute(
                    """INSERT INTO leaf_custom_profile(
                         profile_id,leaf_id,source_id,evidence_id,batch_id,description,
                         primary_outcome,in_scope_json,out_of_scope_json,tasks_json,
                         professional_skills_json,technologies_json,sibling_disambiguators_json,
                         review_status,vector_status,reviewer,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(profile_id) DO UPDATE SET evidence_id=excluded.evidence_id,
                         description=excluded.description,primary_outcome=excluded.primary_outcome,
                         in_scope_json=excluded.in_scope_json,out_of_scope_json=excluded.out_of_scope_json,
                         tasks_json=excluded.tasks_json,professional_skills_json=excluded.professional_skills_json,
                         technologies_json=excluded.technologies_json,
                         sibling_disambiguators_json=excluded.sibling_disambiguators_json,
                         review_status=excluded.review_status,vector_status=excluded.vector_status,
                         reviewer=excluded.reviewer,created_at=excluded.created_at""",
                    (
                        profile_id,
                        leaf_id,
                        source["source_id"],
                        evidence_id,
                        batch_id,
                        profile["description"],
                        profile["primary_outcome"],
                        json.dumps(profile["in_scope"], ensure_ascii=False),
                        json.dumps(profile["out_of_scope"], ensure_ascii=False),
                        json.dumps(profile["tasks"], ensure_ascii=False),
                        json.dumps(profile["professional_skills"], ensure_ascii=False),
                        json.dumps(profile["technologies"], ensure_ascii=False),
                        json.dumps(profile["sibling_disambiguators"], ensure_ascii=False),
                        payload["review_policy"]["review_status"],
                        payload["review_policy"]["vector_status"],
                        "",
                        now,
                    ),
                )
                created += 1

            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (f"custom_leaf_profile_{batch_id}_source", relative_path),
            )
            con.execute(
                """INSERT INTO metadata(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (f"custom_leaf_profile_{batch_id}_status", "REVIEW_REQUIRED_NOT_IN_VECTOR_INDEX"),
            )
            con.execute(f"PRAGMA user_version={USER_VERSION}")

        if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite foreign-key check failed")
        report = {
            "batch_id": batch_id,
            "source_file": relative_path,
            "source_sha256": source_sha256,
            "profiles_staged": created,
            "review_status": payload["review_policy"]["review_status"],
            "vector_status": payload["review_policy"]["vector_status"],
            "official_sources_modified": False,
            "backup": str(backup),
            "staged_at": now,
        }
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"{batch_id}_staging_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["report"] = str(report_path)
        return report
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(stage(), ensure_ascii=False, indent=2))
