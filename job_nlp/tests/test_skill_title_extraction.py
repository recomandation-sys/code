"""NESTA fragment filter, curated titles, and the skill-title score gate."""
from __future__ import annotations

from job_nlp.pipeline.job_extraction_pipeline import JobNLPService
from job_nlp.skills.en_skill_stack import _contained_by_longer, _offset_inside
from job_nlp.taxonomy.title_vector_resolver import choose_skill_title


def test_shorter_span_inside_a_longer_phrase_is_dropped():
    phrases = ["SQL Server", "SQL", "excellent communication"]
    assert _contained_by_longer("SQL", phrases)
    assert not _contained_by_longer("excel", ["excellent communication"])
    assert not _contained_by_longer("SQL Server", phrases)
    assert _offset_inside(10, 13, 10, 20)
    assert not _offset_inside(10, 20, 10, 20)


def test_production_engineer_resolves_without_the_title_model():
    calls: list[str] = []

    class Recorder:
        def __init__(self, label: str) -> None:
            self.label = label
            self.warning = ""
            self.last_decision: dict = {}

        def resolve(self, *args, **kwargs):
            calls.append(self.label)

        def resolve_from_skills(self, *args, **kwargs):
            calls.append(self.label)

        def resolve_responsibilities(self, *args, **kwargs):
            calls.append(self.label)

    service = JobNLPService(
        load_en_skills=False,
        load_semantic=False,
        preload_semantic=False,
        load_tfidf=False,
    )
    service.semantic_resolver = Recorder("semantic")
    service.title_vector_resolver = Recorder("title")

    class Structured:
        occupation_method = ""
        occupation_family = None
        occupation_uri = None

    decision = service._resolve_family(
        "Production Engineer",
        "Supports production applications.",
        "Production Engineer",
        "Supports production applications.",
        [],
        Structured(),
        [],
        [],
    )
    assert decision.job_family == "SUPPORT"
    assert decision.job_parent == "USER_APPLICATION_SUPPORT"
    assert decision.job_leaf == "APPLICATION_SUPPORT"
    assert calls == []


def test_leafless_title_is_not_accepted():
    leafless = {"title": "Application Manager", "family_id": "SOFTWARE", "parent_id": "SOFTWARE_DEVELOPMENT", "leaf_id": ""}
    kept = {
        "title": "Application Coordinator",
        "family_id": "SUPPORT",
        "parent_id": "USER_APPLICATION_SUPPORT",
        "leaf_id": "APPLICATION_SUPPORT",
    }
    chosen = choose_skill_title([(leafless, 0.90), (kept, 0.70)], threshold=0.55, margin=0.015)
    assert chosen is not None
    assert chosen[0]["leaf_id"] == "APPLICATION_SUPPORT"
    assert choose_skill_title([(leafless, 0.90)], threshold=0.55, margin=0.015) is None


def test_margin_below_gate_abstains():
    first = {"title": "Application Lifecycle Manager", "family_id": "PLATFORM_INFRASTRUCTURE", "parent_id": "SYSTEMS_OPERATIONS", "leaf_id": "SYSTEM_CONFIG"}
    second = {"title": "Application Coordinator", "family_id": "SUPPORT", "parent_id": "USER_APPLICATION_SUPPORT", "leaf_id": "APPLICATION_SUPPORT"}
    assert choose_skill_title([(first, 0.720), (second, 0.710)], threshold=0.55, margin=0.015) is None
