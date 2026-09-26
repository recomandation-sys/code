"""Frozen inputs and helpers for the 70/15/15 leaf run.

Paths point at leaf/inputs. The retired French-to-English title map is
archive/jobnlpv2/leaf/support.py and is not called.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

INPUTS = Path(__file__).resolve().parent / "inputs"
OFFERS = INPUTS / "rekrute_it_100_translated_best.jsonl"
TITLES = INPUTS / "it_titles_master_taxonomy_no_seniority_best.csv"
PROFILES = INPUTS / "leaf_profiles_compact_118_24_8_enriched_best.json"
MODEL = Path(__file__).resolve().parents[2] / "models" / "job-title-normalizer-e5-base"
REPORT = Path(__file__).resolve().parent / "reports" / "rekrute_it_100_title70_tech15"
JOB_SPAN = re.compile(r"(?is)(?:^|\n)\s*job\s*:\s*(.*?)\n\s*required profile\s*:")
TOKEN = re.compile(r"[a-z0-9+#./_-]+", re.I)

SHORT_OK = {
    "sap", "aws", "gcp", "sql", "iam", "rpa", "nlp", "c++", "c#", ".net", "ai", "bi",
    "qa", "ux", "ui", "etl", "erp", "crm", "api", "dns", "vpn", "sla", "pki", "hsm",
    "siem", "soc", "itil", "rag", "llm",
}


def name_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("-", " ")).strip().casefold()


def parts(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_registry():
    leaves = read_csv(INPUTS / "leaves_best.csv")
    definitions = {name_key(row["leaf_name"]): row for row in read_csv(INPUTS / "definitions_best.csv")}
    tasks = {name_key(row["leaf_name"]): row for row in read_csv(INPUTS / "main_tasks_best.csv")}
    by_name = {}
    for row in leaves:
        key = name_key(row["leaf_name"])
        if key in by_name:
            raise SystemExit(f"duplicate leaf name {row['leaf_name']}")
        by_name[key] = row
    missing = [row["leaf_name"] for row in leaves if name_key(row["leaf_name"]) not in definitions or name_key(row["leaf_name"]) not in tasks]
    families = {row["family_id"] for row in leaves}
    parents = {row["parent_id"] for row in leaves}
    if len(leaves) != 118 or len(families) != 8 or len(parents) != 24 or missing:
        raise SystemExit(f"registry failed: leaves={len(leaves)} families={len(families)} parents={len(parents)} missing={missing[:5]}")
    old = read_csv(INPUTS / "leafs_best.csv")
    old_l0001 = next(row["leaf"] for row in old if row["leaf_id"] == "L0001")
    new_l001 = next(row["leaf_name"] for row in leaves if row["id"] == "L001")
    if old_l0001 == new_l001:
        raise SystemExit("L0001 and L001 collapsed; refuse to join on stripped ids")
    tech_rows = read_csv(INPUTS / "technologies_best.csv")
    unmatched = []
    edges = []
    keys = {}
    for row in tech_rows:
        leaf_names = []
        for leaf_name in parts(row["related_leafs"]):
            key = name_key(leaf_name)
            if key not in by_name:
                unmatched.append(leaf_name)
                continue
            leaf_names.append(by_name[key]["leaf_name"])
        if not leaf_names:
            continue
        edges.append({
            "id": row["technology_id"],
            "name": row["technology"],
            "leaves": leaf_names,
            "leaf_count": len(leaf_names),
        })
        for alias in [row["technology"], *parts(row.get("aliases") or "")]:
            token = " ".join(TOKEN.findall(alias.casefold()))
            if not token:
                continue
            if len(token) < 3 and token not in SHORT_OK:
                continue
            keys.setdefault(token, row["technology_id"])
    by_id = {edge["id"]: edge for edge in edges}
    return leaves, by_name, definitions, tasks, by_id, keys, sorted(set(unmatched))


def sections(description: str) -> tuple[str, str, str]:
    match = JOB_SPAN.search(description or "")
    if not match:
        return "", description or "", "LOW"
    duties = match.group(1).strip()
    tail = (description or "")[match.end():]
    return duties, tail, "OK"


def windows(tokenizer, text: str) -> list[str]:
    prefix = "query: "
    budget = max(8, 64 - len(tokenizer.encode(prefix, add_special_tokens=False)) - 2)
    ids = tokenizer.encode(text, add_special_tokens=False)
    if not ids:
        return []
    stride = max(1, budget // 2)
    chunks = []
    for start in range(0, len(ids), stride):
        chunks.append(prefix + tokenizer.decode(ids[start:start + budget]))
        if start + budget >= len(ids):
            break
    return chunks

def is_out(raw: str, english: str) -> bool:
    blob = f"{raw} {english}".casefold()
    if "comptable" in blob or "accountant" in blob:
        return True
    sales = "commercial" in blob or "sédentaire" in blob or "sedentaire" in blob or "inside sales" in blob
    technical = any(word in blob for word in ("engineer", "developer", "support", "analyst", "informatique"))
    return sales and not technical


def role_override(raw: str, english: str, duties: str, winner: str) -> str | None:
    blob = f"{raw} {english}".casefold()
    duty = (duties or "").casefold()
    if ("chef de projet" in blob or "project manager" in blob) and winner in {
        "Artificial Intelligence Engineer", "Machine Learning Engineer", "NLP Engineer", "Computer Vision Engineer",
    }:
        return "IT Project Manager"
    if re.search(r"python (developer|engineer)", blob) and "machine learning" not in blob and "data scientist" not in blob:
        if winner in {"Machine Learning Engineer", "Artificial Intelligence Engineer", "DevOps Engineer", "Cloud Engineer"}:
            return "Backend Developer"
    platform = any(name in blob for name in ("salesforce", "servicenow", "workday", "oracle"))
    if platform and "cloud" in blob and winner in {"Cloud Engineer", "Cloud Architect"}:
        if not any(name in duty for name in ("aws", "azure", "gcp", "landing zone", "vpc")):
            return "IT Consultant"
    if "support" in blob and winner in {"Software Test Engineer", "Test Automation Engineer"}:
        if any(name in duty or name in blob for name in ("ticket", "sla", "incident", "applicatif", "java")):
            return "Application Support Specialist"
    return None
