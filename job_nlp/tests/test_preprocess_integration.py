"""HTTP and batch ingestion go through the gate before extraction."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import job_nlp.api.main as api
from job_nlp.pipeline.job_extraction_pipeline import LANGUAGE_TRUST, JobNLPService
from job_nlp.scripts.filter_english_datasets import classify_language
from job_nlp.scripts.run_full_dataset import extract_ingested_record

ENGLISH = " ".join(
    [
        "The ward nurse provides daily patient care, writes treatment notes, and supports the care team during each shift."
    ]
    * 8
)
FRENCH = " ".join(
    [
        "Nous recherchons une infirmiere pour accueillir les patients, rediger les dossiers medicaux et travailler avec l equipe du service chaque jour."
    ]
    * 8
)


class CountingExtractor:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.trusted: list[object | None] = []
        self.families: list[object] = []
        self.family = type("Family", (), {"job_family": "SOFTWARE"})()

    def resolve_job_family(self, title, description):
        self.calls.append("resolve_job_family")
        return self.family

    def extract(self, title, description, country="", *, job_id="", source="", source_id=None, source_fields=None, _language_trusted=None, _family=None):
        self.calls.append("extract")
        self.trusted.append(_language_trusted)
        self.families.append(getattr(_family, "job_family", None))

        class Offer:
            def model_dump(self, mode="json"):
                return {"quality": {"status": "ok", "language": "en"}, "title": title}

        return Offer()

    def extract_skills_only(self, title, description, *, _language_trusted=None):
        self.calls.append("skills_only")
        self.trusted.append(_language_trusted)
        return {"professional_skills": [{"name": "care"}], "technologies": []}

    def extract_v1(self, title, description, country="", *, _language_trusted=None, _family=None):
        self.calls.append("legacy_v1")
        self.trusted.append(_language_trusted)

        class Profile:
            def model_dump(self, mode="json"):
                return {"job_family_parent": "UNKNOWN"}

        return Profile()


def _client(extractor: CountingExtractor) -> TestClient:
    api._service = extractor
    return TestClient(api.app)


def test_http_english_reaches_extraction_once():
    extractor = CountingExtractor()
    response = _client(extractor).post(
        "/api/v1/jobs/extract",
        json={"title": "Ward nurse", "description": ENGLISH, "source": "himalayas", "job_id": "n1"},
    )
    assert response.status_code == 200
    assert response.json()["quality"]["status"] == "ok"
    assert extractor.calls == ["resolve_job_family", "extract"]
    assert extractor.trusted == [LANGUAGE_TRUST]
    assert extractor.families == [None]


def test_http_french_never_reaches_extraction():
    extractor = CountingExtractor()
    response = _client(extractor).post(
        "/api/v1/jobs/extract",
        json={
            "title": "Infirmiere",
            "description": FRENCH,
            "source": "keejob",
            "job_id": "f1",
            "language_verified": True,
        },
    )
    body = response.json()
    assert extractor.calls == []
    assert body["quality"]["status"] == "unsupported_language"
    assert body["quality"]["warnings"] == ["preprocess_gate_refused:NON_ENGLISH_DESCRIPTION"]
    assert "language_verified" not in body
    assert "language_verified" not in api.JobExtractRequest.model_fields


def test_http_skills_only_accepts_once_and_refuse_skips_skills():
    extractor = CountingExtractor()
    client = _client(extractor)
    accepted = client.post(
        "/api/v1/jobs/extract",
        json={"title": "Ward nurse", "description": ENGLISH, "skills_only": True, "job_id": "s1"},
    )
    assert accepted.json()["professional_skills"] == [{"name": "care"}]
    assert extractor.calls == ["resolve_job_family", "skills_only"]
    refused = client.post(
        "/api/v1/jobs/extract",
        json={"title": "Infirmiere", "description": FRENCH, "skills_only": True, "job_id": "s2"},
    )
    assert refused.json() == {"professional_skills": [], "technologies": []}
    assert extractor.calls == ["resolve_job_family", "skills_only"]


def test_unknown_family_rejects_before_extraction():
    extractor = CountingExtractor()
    extractor.family = type("Family", (), {"job_family": "UNKNOWN"})()
    response = _client(extractor).post(
        "/api/v1/jobs/extract",
        json={"title": "Ward nurse", "description": ENGLISH, "source": "himalayas", "job_id": "n2"},
    )
    body = response.json()
    assert extractor.calls == ["resolve_job_family"]
    assert body["quality"]["status"] == "rejected"
    assert body["quality"]["warnings"] == ["preprocess_gate_refused:JOB_FAMILY_UNKNOWN"]
    assert body["identity"]["job_family"] in (None, "", "UNKNOWN")


def test_batch_english_extracts_once_and_french_does_not():
    extractor = CountingExtractor()
    english = extract_ingested_record(
        extractor,
        api._predictor,
        {
            "_source": "himalayas",
            "_source_id": "batch-en",
            "_title": "Ward nurse",
            "_description": ENGLISH,
            "job_id": "batch-en",
            "_source_fields": {"country": "Tunisia"},
        },
    )
    assert english["quality"]["status"] == "ok"
    assert extractor.calls == ["resolve_job_family", "extract"]
    french = extract_ingested_record(
        extractor,
        api._predictor,
        {
            "_source": "keejob",
            "_source_id": "batch-fr",
            "_title": "Infirmiere",
            "_description": FRENCH,
            "job_id": "batch-fr",
            "_source_fields": {},
        },
    )
    assert french["quality"]["status"] == "unsupported_language"
    assert extractor.calls == ["resolve_job_family", "extract"]


def test_family_check_does_not_resolve_parent_or_leaf(monkeypatch):
    seen: list[bool] = []

    def family_only(self, *args, **kwargs):
        seen.append(kwargs.get("family_only"))
        return type("Family", (), {"job_family": "SOFTWARE", "job_parent": "UNKNOWN", "job_leaf": None})()

    monkeypatch.setattr(JobNLPService, "_resolve_family", family_only)
    service = JobNLPService(
        load_en_skills=False,
        load_knowledge_base=False,
        load_semantic=False,
        preload_semantic=False,
        load_tfidf=False,
    )
    decision = service.resolve_job_family("Backend engineer", ENGLISH)
    assert seen == [True]
    assert decision.job_family == "SOFTWARE"
    assert decision.job_parent == "UNKNOWN"
    assert decision.job_leaf is None


def test_direct_extract_keeps_stopword_check(monkeypatch):
    service = JobNLPService(
        load_en_skills=False,
        load_knowledge_base=False,
        load_semantic=False,
        preload_semantic=False,
        load_tfidf=False,
    )
    seen: list[str] = []

    def past_gate(title, description):
        seen.append(description)
        raise RuntimeError("past-language-gate")

    monkeypatch.setattr("job_nlp.pipeline.job_extraction_pipeline.to_model_text", past_gate)
    assert classify_language(f"Infirmiere\n{FRENCH}") != "en"
    blocked = service.extract("Infirmiere", FRENCH, _language_trusted=True)
    assert blocked.quality.status == "unsupported_language"
    assert seen == []
    with pytest.raises(RuntimeError, match="past-language-gate"):
        service.extract("Infirmiere", FRENCH, _language_trusted=LANGUAGE_TRUST)
    assert seen == [FRENCH]
