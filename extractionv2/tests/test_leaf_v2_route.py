"""Offline routing checks; the E5 model is not loaded."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extractionv2.pipeline import default_assign, normalize


class Scripted:
    version = "scripted"
    def predict(self, text):
        return ("en", 0.95)


def record():
    return {"job_id": "example-1", "url": "https://example.invalid/job/example-1", "title": "Test Lead", "company": "Example", "description": " ".join(["the candidate will organize software tests and support the squad"] * 16)}


def test_review_retains_ranked_leaves_without_forcing_one():
    candidates = [{"leaf": "Software Test Engineer", "score": 0.812}, {"leaf": "Test Automation Engineer", "score": 0.806}]
    row = normalize(record(), Scripted(), lambda *_: {"status": "REVIEW_AMBIGUOUS", "leaf": None, "margin": 0.006, "candidates": candidates})
    assert row["decision"] == "REVIEW"
    assert row["leaf_candidates"] == candidates
    assert "leaf" not in row


def test_v2_reuses_existing_site_span(monkeypatch):
    monkeypatch.setenv("LEAF_CLASSIFIER_V2", "on")
    seen = {}
    def scorer(title, duties, *, technology_text):
        seen.update(title=title, duties=duties, full=technology_text)
        return {"status": "NO_LEAF", "leaf": None, "candidates": [], "margin": None}
    monkeypatch.setitem(sys.modules, "evidence_classifier", types.SimpleNamespace(classify_leaf=scorer))
    body = "Job : Build and maintain test suites.\nRequired profile : Experience with Python."
    assert default_assign("Test Lead", body)["status"] == "NO_LEAF"
    assert seen["duties"] == "Build and maintain test suites."
    assert seen["full"] == body
