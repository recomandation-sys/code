"""Preprocessing gate. Language scores are scripted; no fastText file required."""
from __future__ import annotations

import json
import logging

import pytest

from job_nlp.ingestion.preprocess.adapters import from_scraped_record
from job_nlp.ingestion.preprocess.config import GateConfig, load_config
from job_nlp.ingestion.preprocess.gate import (
    ACCEPT,
    CHUNK_LANGUAGE_MISMATCH,
    DECISIONS,
    DESCRIPTION_SELECTOR_NOT_FOUND,
    DESCRIPTION_TOO_LARGE,
    DESCRIPTION_TOO_SHORT,
    ENGLISH_CONFIRMED_BY_TWO_CHUNKS,
    HIGH_CONFIDENCE_ENGLISH,
    INSUFFICIENT_TEXT_FOR_CHUNK_CONFIRMATION,
    LOW_CHUNK_ENGLISH_CONFIDENCE,
    MISSING_DESCRIPTION,
    NON_ENGLISH_DESCRIPTION,
    REFUSE,
    REFUSE_REASONS,
    LANGUAGE_MODEL_UNAVAILABLE,
    run_gate,
)
from job_nlp.ingestion.preprocess.integrate import preprocess_and_extract
from job_nlp.ingestion.preprocess.language import UnavailablePredictor, open_predictor
from job_nlp.ingestion.preprocess.text import (
    DESCRIPTION_HTML,
    FULL_PAGE_HTML,
    PLAIN_TEXT,
    clean_description,
    confirmation_chunks,
)

SENSITIVE = (
    "Contact me at jane@example.com or visit https://jobs.example.com/apply "
    "or call +216 98 123 456. We need 3+ years and 6 months of experience "
    "on a 12-month contract. Salary is EUR 45000. Use Python 3.12, C++ and .NET. "
    "Posted on 2023-09-01. Bonus is 15%. Expérience و خبرة."
)


class Scripted:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.version = "scripted-v1"

    def predict(self, text):
        self.calls.append(text)
        if not self._responses:
            raise AssertionError("unexpected predict")
        return self._responses.pop(0)


class Extractor:
    def __init__(self):
        self.calls = []

    def resolve_job_family(self, title, description):
        return type("Family", (), {"job_family": "SOFTWARE"})()

    def extract(self, title, description, country="", *, job_id="", source="", source_id=None, source_fields=None, **_kwargs):
        self.calls.append({
            "title": title,
            "description": description,
            "country": country,
            "job_id": job_id,
            "source": source,
            "source_id": source_id,
            "source_fields": source_fields,
        })
        return {"extracted": True}


def prose(n, start="ALPHA", end="OMEGA"):
    unit = (
        "The ward nurse provides daily patient care writes treatment notes "
        "and supports the care team during each shift"
    ).split()
    words = (unit * ((n // len(unit)) + 1))[:n]
    words[0] = start
    words[-1] = end
    return " ".join(words)


def offer(description, **kwargs):
    data = dict(
        source="keejob",
        source_job_id="1",
        canonical_url="https://example.test/jobs/1",
        title="Ward nurse",
        description=description,
        description_mode=PLAIN_TEXT,
        metadata={"country": "Tunisia"},
    )
    data.update(kwargs)
    from job_nlp.ingestion.preprocess.gate import GateInput
    return GateInput(**data)


def test_decisions_are_only_accept_and_refuse():
    assert DECISIONS == {ACCEPT, REFUSE}
    assert "REVIEW" not in DECISIONS
    assert "REVIEW" not in REFUSE_REASONS


def test_config_defaults_match_the_unverified_thresholds():
    cfg = load_config()
    assert cfg.high_confidence_en == 0.95
    assert cfg.chunk_confidence_en == 0.80
    assert cfg.min_description_words == 60
    assert cfg.chunk_words == 80
    assert cfg.min_substantive_chunk_words == 30
    assert cfg.description_selectors == {}
    assert cfg.unwanted_selectors == {}
    assert cfg.boilerplate_lines == {}


def test_high_confidence_english_accepts_with_one_prediction(monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("chunks built")

    monkeypatch.setattr("job_nlp.ingestion.preprocess.text.confirmation_chunks", boom)
    predictor = Scripted([("en", 0.97)])
    result = run_gate(offer(prose(80, start="Nurse", end="patients")), predictor)
    assert result.decision == ACCEPT
    assert result.reason == HIGH_CONFIDENCE_ENGLISH
    assert result.predictions_count == 1
    assert len(predictor.calls) == 1
    assert "\n" not in predictor.calls[0]


def test_uncertain_english_confirmed_by_two_chunks():
    words = prose(220).split()
    words[80] = "BETA"
    text = " ".join(words)
    predictor = Scripted([("en", 0.94), ("en", 0.81), ("en", 0.96)])
    result = run_gate(offer(text), predictor)
    assert result.decision == ACCEPT
    assert result.reason == ENGLISH_CONFIRMED_BY_TWO_CHUNKS
    assert result.predictions_count == 3
    assert len(predictor.calls) == 3
    assert "ALPHA" in predictor.calls[1] and "BETA" not in predictor.calls[1]
    assert "OMEGA" not in predictor.calls[1]
    assert "BETA" in predictor.calls[2] and "ALPHA" not in predictor.calls[2]
    assert "OMEGA" not in predictor.calls[2]
    assert predictor.calls[1] != predictor.calls[2]
    assert all("\n" not in call for call in predictor.calls)


def test_uncertain_english_first_chunk_french():
    predictor = Scripted([("en", 0.90), ("fr", 0.99), ("en", 0.99)])
    result = run_gate(offer(prose(220)), predictor)
    assert result.decision == REFUSE
    assert result.reason == CHUNK_LANGUAGE_MISMATCH
    assert result.predictions_count == 3
    assert len(predictor.calls) == 3


def test_uncertain_english_second_chunk_french():
    predictor = Scripted([("en", 0.90), ("en", 0.99), ("fr", 0.99)])
    result = run_gate(offer(prose(220)), predictor)
    assert result.decision == REFUSE
    assert result.reason == CHUNK_LANGUAGE_MISMATCH
    assert result.predictions_count == 3


def test_uncertain_english_low_chunk_confidence():
    predictor = Scripted([("en", 0.90), ("en", 0.99), ("en", 0.50)])
    result = run_gate(offer(prose(220)), predictor)
    assert result.decision == REFUSE
    assert result.reason == LOW_CHUNK_ENGLISH_CONFIDENCE
    assert result.predictions_count == 3


def test_confident_french_refuses_after_one_prediction():
    predictor = Scripted([("fr", 0.99)])
    result = run_gate(offer(prose(80)), predictor)
    assert result.decision == REFUSE
    assert result.reason == NON_ENGLISH_DESCRIPTION
    assert result.predictions_count == 1
    assert result.clean_description is None


@pytest.mark.parametrize("language,score", [("ar", 0.40), ("fr", 0.40)])
def test_low_confidence_non_english_refuses_after_one_prediction(language, score):
    predictor = Scripted([(language, score)])
    result = run_gate(offer(prose(80)), predictor)
    assert result.decision == REFUSE
    assert result.reason == NON_ENGLISH_DESCRIPTION
    assert result.predictions_count == 1
    assert result.detected_language == language


def test_uncertain_english_without_two_chunks_refuses_after_one_prediction():
    tech = " ".join(
        "Python Java AWS Docker Kubernetes React SQL Linux Azure GCP Node Django "
        "Spark Hadoop Terraform Ansible Jenkins Mongo Redis Kafka GraphQL".split() * 4
    )
    assert confirmation_chunks(tech, GateConfig()) is None
    predictor = Scripted([("en", 0.90), ("en", 0.99), ("en", 0.99)])
    result = run_gate(offer(tech), predictor)
    assert result.decision == REFUSE
    assert result.reason == INSUFFICIENT_TEXT_FOR_CHUNK_CONFIRMATION
    assert result.predictions_count == 1
    assert len(predictor.calls) == 1


def test_missing_description_does_not_predict(caplog):
    caplog.set_level(logging.INFO, logger="job_nlp.ingestion.preprocess")
    predictor = Scripted([("en", 0.99)])
    for description in (None, "", "   "):
        result = run_gate(offer(description), predictor)
        assert result.decision == REFUSE
        assert result.reason == MISSING_DESCRIPTION
        assert result.predictions_count == 0
    short = run_gate(offer("mail jane@example.com"), predictor)
    assert short.reason == DESCRIPTION_TOO_SHORT
    assert short.predictions_count == 0
    assert "jane@example.com" not in json.dumps(short.public_dict())
    assert "jane@example.com" not in caplog.text
    assert predictor.calls == []


def test_missing_full_page_selector_refuses_without_prediction():
    page = "<html><body><div class='job'><p>English description</p></div></body></html>"
    predictor = Scripted([("en", 0.99)])
    missing = run_gate(offer(page, description_mode=FULL_PAGE_HTML), predictor, config=GateConfig())
    assert missing.reason == DESCRIPTION_SELECTOR_NOT_FOUND
    assert missing.predictions_count == 0
    unmatched = run_gate(
        offer(page, description_mode=FULL_PAGE_HTML),
        predictor,
        config=GateConfig(description_selectors={"keejob": "div.does-not-exist"}),
    )
    assert unmatched.reason == DESCRIPTION_SELECTOR_NOT_FOUND
    assert unmatched.predictions_count == 0
    assert predictor.calls == []


def test_full_page_uses_only_the_description_container():
    unit = (
        "Nous recherchons une infirmiere pour accueillir les patients rediger "
        "les dossiers medicaux et travailler avec lequipe du service chaque jour"
    ).split()
    french = " ".join((["FRENCHBODY"] + unit * 6)[:80])
    page = f"""
    <html><body>
      <nav>English navigation</nav>
      <article class="job">
        <p>{french}</p>
        <div class="share">SHAREWIDGET</div>
      </article>
      <footer>FOOTERENGLISH equal opportunity employer</footer>
    </body></html>
    """
    predictor = Scripted([("fr", 0.99)])
    config = GateConfig(
        description_selectors={"keejob": "article.job"},
        unwanted_selectors={"keejob": (".share",)},
    )
    result = run_gate(offer(page, description_mode=FULL_PAGE_HTML), predictor, config=config)
    assert result.decision == REFUSE
    assert result.reason == NON_ENGLISH_DESCRIPTION
    assert result.predictions_count == 1
    assert "FRENCHBODY" in predictor.calls[0]
    assert "SHAREWIDGET" not in predictor.calls[0]
    assert "FOOTERENGLISH" not in predictor.calls[0]


def test_cleaning_removes_contacts_and_keeps_job_facts():
    cleaned = clean_description(SENSITIVE, source="keejob", config=GateConfig())
    assert "jane@example.com" not in cleaned
    assert "https://jobs.example.com/apply" not in cleaned
    assert "+216" not in cleaned
    for kept in (
        "3+ years",
        "6 months",
        "12-month contract",
        "EUR 45000",
        "Python 3.12",
        "C++",
        ".NET",
        "2023-09-01",
        "15%",
        "Expérience",
        "خبرة",
    ):
        assert kept in cleaned
    boilerplate = GateConfig(boilerplate_lines={"keejob": ("Apply on our website",)})
    kept_apply = clean_description(
        "Apply on our website\nPlease apply with your CV and describe your ward experience.",
        source="keejob",
        config=boilerplate,
    )
    assert "Apply on our website" not in kept_apply.splitlines()
    assert "Please apply with your CV" in kept_apply


def test_html_entities_scripts_comments_and_lists():
    page = f"""
    <script>alert(1)</script>
    <style>body{{color:red}}</style>
    <!-- secret comment -->
    <svg><text>svgsecret</text></svg>
    <iframe>framesecret</iframe>
    <p>We need <strong>Python 3.12</strong> &amp; SQL.</p>
    <ul><li>Build APIs</li><li>Review code</li></ul>
    <p>{prose(70, start="Nurse", end="patients")}</p>
    """
    predictor = Scripted([("en", 0.99)])
    result = run_gate(offer(page, description_mode=DESCRIPTION_HTML), predictor)
    assert result.decision == ACCEPT
    text = result.clean_description
    assert "alert" not in text
    assert "secret comment" not in text
    assert "svgsecret" not in text
    assert "framesecret" not in text
    assert "Python 3.12" in text
    assert "&amp;" not in text
    assert "SQL" in text
    assert "Build APIs" in text
    assert "Review code" in text


def test_malformed_html_does_not_crash():
    predictor = Scripted([("en", 0.99)])
    for blob in ("<", "<<", "<p><div>", "<<<<html", "<article><p>unclosed"):
        result = run_gate(offer(blob, description_mode=DESCRIPTION_HTML), predictor)
        assert result.decision == REFUSE
    assert predictor.calls == []


def test_model_unavailable_refuses():
    result = run_gate(offer(prose(80)), UnavailablePredictor("missing file"))
    assert result.decision == REFUSE
    assert result.reason == LANGUAGE_MODEL_UNAVAILABLE
    assert result.predictions_count == 0
    assert run_gate(offer(prose(80)), None).reason == LANGUAGE_MODEL_UNAVAILABLE


def test_oversized_description_is_not_truncated_and_accepted():
    huge = prose(80) + (" word" * 20000)
    assert len(huge) > 50_000
    predictor = Scripted([("en", 0.99)])
    result = run_gate(offer(huge), predictor)
    assert result.decision == REFUSE
    assert result.reason == DESCRIPTION_TOO_LARGE
    assert result.predictions_count == 0
    assert result.clean_description is None
    assert result.cleaned_description is None
    blob = json.dumps(result.public_dict())
    assert "ALPHA" not in blob
    assert len(blob) < 2000
    assert predictor.calls == []


def test_refuse_does_not_call_feature_extraction():
    extractor = Extractor()
    predictor = Scripted([("fr", 0.99)])
    out = preprocess_and_extract(offer(prose(80)), extractor, predictor)
    assert out.gate.decision == REFUSE
    assert out.extraction is None
    assert extractor.calls == []


def test_accept_calls_feature_extraction_with_cleaned_text():
    extractor = Extractor()
    predictor = Scripted([("en", 0.99)])
    text = SENSITIVE + "\n" + prose(90, start="Nurse", end="ward")
    out = preprocess_and_extract(offer(text), extractor, predictor)
    assert out.gate.decision == ACCEPT
    assert out.extraction == {"extracted": True}
    sent = extractor.calls[0]
    assert "jane@example.com" not in sent["description"]
    assert "3+ years" in sent["description"]
    assert "Python 3.12" in sent["description"]
    assert sent["source"] == "keejob"
    assert sent["job_id"] == "1"
    assert sent["country"] == "Tunisia"
    assert sent["title"] == "Ward nurse"


def test_non_it_english_posting_is_not_refused():
    text = prose(80, start="Nurse", end="patients")
    assert "python" not in text.casefold()
    result = run_gate(offer(text, title="Ward nurse"), Scripted([("en", 0.99)]))
    assert result.decision == ACCEPT
    assert result.reason == HIGH_CONFIDENCE_ENGLISH


def test_scraped_record_maps_to_plain_text():
    row = {
        "source": "himalayas",
        "job_id": "abc",
        "url": "https://himalayas.app/jobs/abc",
        "title": "Nurse",
        "description": "Patient care",
        "city": "Tunis",
        "country": "Tunisia",
        "company": "Clinic",
    }
    got = from_scraped_record(row)
    assert got.description_mode == PLAIN_TEXT
    assert got.source_job_id == "abc"
    assert got.canonical_url.endswith("/abc")
    assert got.location == "Tunis, Tunisia"
    assert got.metadata["country"] == "Tunisia"


def test_real_lid_model_smoke():
    cfg = load_config()
    path = cfg.model_path()
    if not path.is_file():
        pytest.fail(f"lid.176.bin is required at {path}; a missing file is not a pass")
    predictor = open_predictor(cfg)
    assert predictor.version.startswith("fasttext-lid.176:")
    language, score = predictor.predict(
        "This is an English sentence about hospital work and patient care."
    )
    assert language == "en"
    assert score > 0.5
    assert open_predictor(cfg) is predictor
