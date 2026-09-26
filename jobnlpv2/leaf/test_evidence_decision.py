"""Offline tests for evidence helpers; no encoder, scraper, or network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from classifier_config import LeafClassifierConfig
from evidence_decision import aggregate_chunks, decide_leaf, grounded_technology_scores


def test_chunk_aggregation_reduces_one_accidental_match():
    assert aggregate_chunks([0.9, 0.1, 0.2], "top_n_mean", 2) == pytest.approx(0.55)
    assert aggregate_chunks([], "top_n_mean", 2) == 0.0

def test_direct_tech_edge_and_shared_edge():
    relations = {"t1": {"leaves": ["A"]}, "t2": {"leaves": ["A", "B"]}}
    scores = grounded_technology_scores(["t1", "t1", "t2"], relations, ["A", "B"])
    assert scores["A"] > scores["B"]
    assert scores["A"] == 1.0

def test_close_leaves_preserve_two_candidates():
    cfg = LeafClassifierConfig(ambiguity_margin=0.02)
    result = decide_leaf({"A": {"title": 0.812}, "B": {"title": 0.806}}, cfg)
    assert result["status"] == "REVIEW_AMBIGUOUS"
    assert result["leaf"] is None
    assert [item["leaf"] for item in result["candidates"]] == ["A", "B"]

def test_optional_ood_gate():
    cfg = LeafClassifierConfig(ood_score_threshold=0.5, min_evidence_score=0.2)
    result = decide_leaf({"A": {"title": 0.2}, "B": {"title": 0.1}}, cfg)
    assert result["status"] == "NO_LEAF"
