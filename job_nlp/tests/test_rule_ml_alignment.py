from __future__ import annotations

from job_nlp.contracts.adapters import adapt_ml_fields, extract_rule_fields, resolve_hybrid_fields
from job_nlp.contracts.business_policy import to_bracket, unknown_field_result, validate_field_result
from job_nlp.contracts.ontology import FIELD_LABELS, FIELD_NAMES


def test_locked_ontology_order_and_values() -> None:
    assert FIELD_NAMES == (
        "education_level",
        "work_mode",
        "contract_type",
        "minimum_experience_bracket",
        "seniority_level",
    )
    assert FIELD_LABELS["education_level"] == ("UNKNOWN", "ASSOCIATE", "BACHELOR", "MASTER_OR_HIGHER")
    assert FIELD_LABELS["work_mode"] == ("REMOTE", "HYBRID", "ONSITE", "UNKNOWN")
    assert FIELD_LABELS["contract_type"] == ("UNKNOWN", "PERMANENT", "FIXED_TERM", "FREELANCE", "INTERNSHIP")
    assert FIELD_LABELS["minimum_experience_bracket"] == ("0_YEARS", "1_2_YEARS", "3_5_YEARS", "5_7_YEARS", "8_PLUS_YEARS", "UNKNOWN")
    assert FIELD_LABELS["seniority_level"] == ("INTERN_ENTRY", "JUNIOR", "MID", "SENIOR", "LEAD_PRINCIPAL", "UNKNOWN")


def test_unknown_object_is_identical_for_rule_and_ml() -> None:
    rule = extract_rule_fields("Software Engineer", "No structured fields are stated.")
    ml = adapt_ml_fields({})
    for field in FIELD_NAMES:
        assert rule[field] == unknown_field_result(field)
        assert ml[field] == unknown_field_result(field)


def test_rule_results_round_trip_evidence() -> None:
    title = "Senior Software Engineer"
    description = "At least 5 years of professional experience required. This is a fully remote role."
    results = extract_rule_fields(title, description)
    assert results["minimum_experience_bracket"]["value"] == "5_7_YEARS"
    assert results["seniority_level"]["value"] == "SENIOR"
    assert results["work_mode"]["value"] == "REMOTE"
    for field, result in results.items():
        assert validate_field_result(field, result, title=title, description=description)


def test_experience_policy_cases() -> None:
    assert to_bracket(0) == "0_YEARS"
    assert to_bracket(11) == "0_YEARS"
    assert to_bracket(12) == "1_2_YEARS"
    assert to_bracket(35) == "1_2_YEARS"
    assert to_bracket(36) == "3_5_YEARS"
    assert to_bracket(59) == "3_5_YEARS"
    assert to_bracket(60) == "5_7_YEARS"
    assert to_bracket(95) == "5_7_YEARS"
    assert to_bracket(96) == "8_PLUS_YEARS"
    assert to_bracket(60, "GT") == "5_7_YEARS"
    cases = {
        "3 years of Python experience required": "3_5_YEARS",
        "minimum 2 years of AWS experience": "1_2_YEARS",
        "5+ years working with Java": "5_7_YEARS",
        "at least 4 years of SAP experience": "3_5_YEARS",
        "3 years preferred": "3_5_YEARS",
        "ideally 5 years of experience": "5_7_YEARS",
        "2+ years is a plus": "1_2_YEARS",
        "experience required": "1_2_YEARS",
        "no experience required": "0_YEARS",
    }
    for description, expected in cases.items():
        result = extract_rule_fields("Software Engineer", description)["minimum_experience_bracket"]
        assert result["value"] == expected
        assert validate_field_result("minimum_experience_bracket", result, title="Software Engineer", description=description)
    warning = extract_rule_fields("Software Engineer", "experience required")["minimum_experience_bracket"]["warnings"]
    assert "UNQUANTIFIED_EXPERIENCE_ASSUMED_1_2_YEARS" in warning
    for description in ("Senior Data Engineer", "The company has 20 years of experience", "5 years of university education"):
        result = extract_rule_fields("Software Engineer", description)["minimum_experience_bracket"]
        assert result["value"] == "UNKNOWN"


def test_hybrid_rule_precedence_and_ml_contract() -> None:
    title = "Backend Developer"
    description = "This is a fully remote role."
    ml = {"work_mode": {"value": "ONSITE", "confidence": 0.99, "evidence": {"text": "fully remote", "start": 10, "end": 22, "source": "DESCRIPTION"}}}
    result = resolve_hybrid_fields(title, description, ml)["work_mode"]
    assert result["value"] == "REMOTE"
    assert result["source"] == "HYBRID"
    assert "RULE_ML_CONTRADICTION" in result["warnings"]


def test_work_mode_negations_and_office_evidence() -> None:
    assert extract_rule_fields("Engineer", "This is not remote.")["work_mode"] == unknown_field_result("work_mode")
    onsite = extract_rule_fields("Engineer", "The role is office-based only.")["work_mode"]
    assert onsite["value"] == "ONSITE"
    assert validate_field_result("work_mode", onsite, title="Engineer", description="The role is office-based only.")
    assert extract_rule_fields("Engineer", "No remote work is available.")["work_mode"] == unknown_field_result("work_mode")
