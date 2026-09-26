"""Offline checks for the Rekrute English IT path. No network and no E5 load."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "jobnlpv2"))

from extractionv2.pipeline import extract, leaf_row, normalize
from ingestionv2.crawl import new_ids
from ingestionv2.parse import parse_offer
from jobnlpv2.visible import english_offer_url, visible_description
from bs4 import BeautifulSoup

PAGE = """
<html><body>
<script type="application/ld+json">
{"@type":"JobPosting","title":"Test Lead","description":"le Test Lead a pour missions principales en francais"}
</script>
<div class="contentbloc">
  <div class="col-md-12 info blc">Test Lead - Rabat</div>
  <div class="col-md-12 blc">Job : the Test Lead main missions are to organize testing and support the squad.</div>
  <div class="col-md-12 blc">Required profile : You have a degree and experience in software testing.</div>
  <div class="col-md-12 blc">Head office address : Avenue Bin Al Ouidane, Rabat</div>
</div>
<ul class="featureInfo">
  <li title="Experience required">3 to 5 years</li>
  <li title="Level of education and training">Associate degree and a Bachelor's degree</li>
  <li title="Contract type">permanent</li>
  <li title="Teleworking">Teleworking : Hybrid</li>
</ul>
</body></html>
"""

BODY = " ".join(["the candidate will organize testing and support the squad with clear written procedures"] * 16)


class Scripted:
    version = "scripted"

    def __init__(self, scores):
        self.scores = list(scores)

    def predict(self, text):
        return self.scores.pop(0)


def _record(**extra):
    row = {
        "job_id": "1",
        "url": "https://www.rekrute.com/en/offre-emploi-test-lead-rabat-1.html",
        "title": "Test Lead",
        "company": "Example",
        "company_logo": None,
        "country": "Morocco",
        "date_posted": "2026-09-17",
        "deadline": "2026-11-17",
        "education": "Associate degree and a Bachelor's degree",
        "teleworking": "Teleworking : Hybrid",
        "contract": "permanent",
        "experience": "3 to 5 years",
        "description": BODY,
    }
    row.update(extra)
    return row


def test_visible_description_ignores_jsonld():
    soup = BeautifulSoup(PAGE, "html.parser")
    text = visible_description(soup)
    assert "francais" not in (text or "")
    assert "organize testing" in (text or "")
    assert "Head office" not in (text or "")
    parsed = parse_offer("https://www.rekrute.com/offre-emploi-test-lead-rabat-1.html", PAGE)
    assert "francais" not in (parsed["description"] or "")
    assert parsed["teleworking"] == "Teleworking : Hybrid"
    assert parsed["experience"] == "3 to 5 years"
    assert english_offer_url("https://www.rekrute.com/offre-emploi-a-1.html").startswith(
        "https://www.rekrute.com/en/"
    )


def test_missing_description_refuses_before_leaf():
    def assign(*_args):
        raise AssertionError("leaf ran")

    row = normalize(_record(description="  "), Scripted([("en", 0.95)]), assign)
    assert row["decision"] == "REFUSE"
    assert row["reason"] == "MISSING_DESCRIPTION"
    assert "education" not in row
    assert "technologies" not in row


def test_english_accept_and_chunk_refuse():
    accepted = normalize(_record(), Scripted([("en", 0.95)]), lambda *_args: "IT Business Analyst")
    assert accepted["decision"] == "ACCEPT"
    assert accepted["leaf"] == "IT Business Analyst"
    refused = normalize(
        _record(),
        Scripted([("en", 0.90), ("en", 0.70), ("en", 0.70)]),
        lambda *_args: "IT Business Analyst",
    )
    assert refused["decision"] == "REFUSE"
    assert refused["reason"] == "LOW_CHUNK_ENGLISH_CONFIDENCE"
    assert "leaf" not in refused


def test_missing_leaf_refuses_without_fields():
    row = normalize(_record(), Scripted([("en", 0.95)]), lambda *_args: "OUT_OF_IT_DOMAIN")
    assert row == {
        "url": _record()["url"],
        "title": "Test Lead",
        "decision": "REFUSE",
        "reason": "NO_LEAF",
    }


def test_known_leaf_joins_family_and_maps_fields():
    catalog = leaf_row("IT Business Analyst")
    assert catalog["family_name"] == "Architecture and Systems Analysis"
    assert catalog["parent_name"] == "Business and Systems Analysis"
    row = normalize(_record(), Scripted([("en", 0.95)]), lambda *_args: "IT Business Analyst")
    assert row["family"] == catalog["family_name"]
    assert row["parent"] == catalog["parent_name"]
    assert row["leaf"] == "IT Business Analyst"
    assert row["work_mode"] == "HYBRID"
    assert row["contract_type"] == "PERMANENT"
    assert row["experience"] == "3_5_YEARS"
    assert row["education"] == ["ASSOCIATE", "BACHELOR"]
    assert row["experience_raw"] == "3 to 5 years"
    assert row["teleworking_raw"] == "Teleworking : Hybrid"
    bands = normalize(
        _record(experience="Mid Level (3 to 5 years) - Senior (5 to 10 years)"),
        Scripted([("en", 0.95)]),
        lambda *_args: "IT Business Analyst",
    )
    assert bands["experience"] == "3_5_YEARS"
    higher = normalize(
        _record(experience="Senior (5 to 10 years) - Expert (10 to 20 years)"),
        Scripted([("en", 0.95)]),
        lambda *_args: "IT Business Analyst",
    )
    assert higher["experience"] == "5_7_YEARS"


def test_second_run_does_not_duplicate_an_id(tmp_path):
    raw = tmp_path / "raw.jsonl"
    out = tmp_path / "out.jsonl"
    raw.write_text(json.dumps(_record()) + "\n", encoding="utf-8")
    extract(raw, out, predictor=Scripted([("en", 0.95)]), assign=lambda *_args: "IT Business Analyst")
    extract(raw, out, predictor=Scripted([("en", 0.95)]), assign=lambda *_args: "IT Business Analyst")
    lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1


def test_listing_stops_when_a_page_adds_no_new_ids():
    assert new_ids(["1", "2"], {"1"}) == ["2"]
    assert new_ids(["1"], {"1"}) == []


def test_technology_recovery_reads_technologies_best():
    tech_dir = ROOT / "jobnlpv2" / "technologies"
    sys.path.insert(0, str(tech_dir))
    from technology_v2 import RUNTIME_CSV, recover_full_text

    assert RUNTIME_CSV.name == "technologies_best.csv"
    hits = recover_full_text("The team uses Python every day.")
    assert any(hit.canonical == "Python" for hit in hits)
