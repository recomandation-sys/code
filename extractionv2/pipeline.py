"""English gate, then the frozen leaf, then the existing enum mappers."""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOBNLP = ROOT / "jobnlpv2"
LEAVES = JOBNLP / "leaf" / "inputs" / "leaves_best.csv"
RAW_PATH = ROOT / "ingestionv2" / "output" / "rekrute_raw.jsonl"
OUT_PATH = Path(__file__).resolve().parent / "output" / "rekrute_it.jsonl"

if str(JOBNLP) not in sys.path:
    sys.path.insert(0, str(JOBNLP))

from gate import ACCEPT, GateInput, PLAIN_TEXT, open_predictor, run_gate  # noqa: E402


def _module(folder: str, filename: str, name: str):
    folder_path = JOBNLP / folder
    if str(folder_path) not in sys.path:
        sys.path.insert(0, str(folder_path))
    path = folder_path / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _leaf_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("-", " ")).strip().casefold()


def leaf_row(name: str | None) -> dict | None:
    if not name:
        return None
    key = _leaf_key(name)
    with LEAVES.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if _leaf_key(row["leaf_name"]) == key:
                return row
    return None


def stored_ids(path: Path = OUT_PATH) -> set[str]:
    if not path.is_file():
        return set()
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        offer_id = row.get("job_id")
        if not offer_id and row.get("url"):
            from jobnlpv2.visible import job_id_from_url

            offer_id = job_id_from_url(row["url"])
        if offer_id:
            found.add(str(offer_id))
    return found


def _refuse(record: dict, reason: str) -> dict:
    return {
        "url": record.get("url"),
        "title": record.get("title"),
        "decision": "REFUSE",
        "reason": reason,
    }


def _experience(line: str | None) -> str:
    """Bracket the lowest figure on the page experience line."""
    module = _module("experience", "seniority_experience_extractor.py", "jobnlpv2_experience")
    months = []
    for match in module._TENURE.finditer(line or ""):
        low = module._number(match.group("low"))
        unit = match.group("unit").casefold()
        months.append(low * (12.0 if unit.startswith(("year", "yr")) else 1.0))
    if not months:
        return "UNKNOWN"
    return module.to_bracket(min(months))


def _fields(record: dict, description: str) -> dict:
    from education.extractor import EducationExtractor

    contract = _module("contract", "contract_type_extractor.py", "jobnlpv2_contract")
    work = _module("work_mode", "work_mode_extractor.py", "jobnlpv2_work_mode")
    technology = _module("technologies", "technology_v2.py", "jobnlpv2_technology")
    levels = EducationExtractor().extract(
        record.get("title") or "", record.get("education") or "",
    ).to_dict()["required_education_levels"]
    kinds = contract.ContractTypeExtractor().extract(
        record.get("title") or "", record.get("contract") or "",
    ).to_dict()["contract_types"]
    modes = work.WorkModeExtractor().extract(
        record.get("title") or "", description, workplace=record.get("teleworking"),
    ).to_dict()["work_modes"]
    names: list[str] = []
    seen: set[str] = set()
    for hit in technology.recover_full_text(description):
        if hit.canonical in seen:
            continue
        seen.add(hit.canonical)
        names.append(hit.canonical)
    return {
        "education": levels,
        "education_raw": record.get("education"),
        "contract_type": kinds[0] if kinds else "UNKNOWN",
        "contract_raw": record.get("contract"),
        "work_mode": modes[0] if modes else None,
        "teleworking_raw": record.get("teleworking"),
        "experience": _experience(record.get("experience")),
        "experience_raw": record.get("experience"),
        "technologies": names,
    }


def normalize(record: dict, predictor, assign) -> dict:
    offer_id = str(record.get("job_id") or "")
    gated = run_gate(
        GateInput(
            source="rekrute",
            description=record.get("description"),
            description_mode=PLAIN_TEXT,
            source_job_id=offer_id or None,
            canonical_url=record.get("url"),
            title=record.get("title") or "",
            company=record.get("company"),
        ),
        predictor,
    )
    if gated.decision != ACCEPT:
        return _refuse(record, gated.reason)
    name = assign(record.get("title") or "", gated.clean_description or "")
    row = leaf_row(name)
    if row is None:
        return _refuse(record, "NO_LEAF")
    accepted = {
        "job_id": offer_id,
        "url": record.get("url"),
        "title": record.get("title"),
        "company": record.get("company"),
        "company_logo": record.get("company_logo"),
        "country": record.get("country"),
        "date_posted": record.get("date_posted"),
        "deadline": record.get("deadline"),
        "description": gated.clean_description,
        "family": row["family_name"],
        "parent": row["parent_name"],
        "leaf": row["leaf_name"],
        "decision": ACCEPT,
    }
    accepted.update(_fields(record, gated.clean_description or ""))
    return accepted


def default_assign(title: str, description: str) -> str:
    leaf = JOBNLP / "leaf"
    if str(leaf) not in sys.path:
        sys.path.insert(0, str(leaf))
    from it_leaf_pipeline_tech15 import assign_leaf

    return assign_leaf(title, description)


def extract(raw_path: Path = RAW_PATH, out_path: Path = OUT_PATH, predictor=None, assign=None) -> int:
    if not raw_path.is_file():
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = stored_ids(out_path)
    scorer = assign or default_assign
    language = predictor if predictor is not None else open_predictor()
    added = 0
    for line in raw_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        offer_id = str(record.get("job_id") or "")
        if offer_id and offer_id in done:
            continue
        row = normalize(record, language, scorer)
        with out_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        if offer_id:
            done.add(offer_id)
        added += 1
    return added


def run() -> int:
    from ingestionv2.crawl import crawl

    crawl()
    return extract()
