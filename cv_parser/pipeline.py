"""Top-level orchestrator: PDF bytes in, parser draft JSON out.

`extract_profile` is the package's only required entry point per section
53 ("Stateless parser"): no caching, no globals depend on request history,
so it is safe to call concurrently from multiple FastAPI workers.

Phase G adds: adaptive reading-order retry that actually *compares* two
candidate parses rather than blindly overriding on one metric (section
48), plus the final `parse_quality`/`review_items` diagnostics (sections
45-47, 51). Every earlier phase's extractors are unchanged; this module
only decides which single reading-order attempt's `sections` to hand them.
"""
from __future__ import annotations

import time

from cv_parser.config import settings
from cv_parser.extractors.certifications import extract_certifications
from cv_parser.extractors.experience import extract_experience
from cv_parser.extractors.identity import extract_identity
from cv_parser.extractors.languages import extract_languages
from cv_parser.extractors.preferences import extract_preferences
from cv_parser.extractors.target import extract_desired_positions
from cv_parser.ingestion.pymupdf_extractor import load_document
from cv_parser.layout.quality import compute_layout_quality
from cv_parser.layout.reading_order import assign_reading_order
from cv_parser.quality.review import build_review_items
from cv_parser.quality.scoring import compute_parse_quality, needs_adaptive_retry, score_parse_candidate
from cv_parser.schemas.internal import Document
from cv_parser.normalization.candidate_profile import normalize_candidate_profile
from cv_parser.schemas.parser_response import ParseMeta, ParserDraftResponse, TargetSection
from cv_parser.schemas.verified_profile import CandidateKnowledgeProfile
from cv_parser.skills.extractor import extract_skills
from cv_parser.structure.section_classifier import Section, classify_sections


def _run_reading_strategy(base_document: Document, strategy: str) -> tuple[Document, list[Section], str]:
    document, _regions = assign_reading_order(base_document, strategy=strategy)
    layout_report = compute_layout_quality(document.blocks)
    sections = classify_sections(document)
    return document, sections, layout_report.status


def _choose_best_attempt(base_document: Document):
    """Adaptive retry (section 48): try the column-aware strategy first;
    only pay for a second attempt when a concrete trigger suggests the
    first one may have scrambled the document, then keep whichever of
    the two actually scores better rather than always overriding.
    """
    document_a, sections_a, layout_status_a = _run_reading_strategy(base_document, "XY_CUT")
    experience_a = extract_experience(sections_a)

    if not needs_adaptive_retry(document_a, sections_a, layout_status_a, experience_a):
        return document_a, sections_a, layout_status_a, "XY_CUT"

    document_b, sections_b, layout_status_b = _run_reading_strategy(base_document, "SIMPLE")
    score_a = score_parse_candidate(sections_a)
    score_b = score_parse_candidate(sections_b)
    if score_b > score_a:
        return document_b, sections_b, layout_status_b, "SIMPLE"
    return document_a, sections_a, layout_status_a, "XY_CUT"


def extract_profile(pdf_bytes: bytes, source_name: str = "cv.pdf") -> dict:
    t0 = time.perf_counter()
    base_document = load_document(pdf_bytes, source_name)

    document, sections, layout_status, reading_strategy = _choose_best_attempt(base_document)

    # Core field extraction (Phase D), the IT Skill Engine (Phase E), and
    # languages/certifications (Phase F).
    identity = extract_identity(document, sections)
    desired_positions = extract_desired_positions(document, sections)
    desired_contract_types, desired_work_modes = extract_preferences(document)
    experience = extract_experience(sections)
    skills = extract_skills(sections)
    languages = extract_languages(sections)
    certifications = extract_certifications(sections)

    duration_ms = (time.perf_counter() - t0) * 1000

    overall_state = document.overall_page_state
    base_warnings: list[str] = []
    if overall_state != "DIGITAL_GOOD":
        base_warnings.append(f"PAGE_STATE_{overall_state}")
    if layout_status == "POOR":
        # Reports the *chosen* candidate's own column-interleaving metric,
        # independent of whether adaptive retry actually switched strategy
        # (section 48 requires comparing, not blindly overriding) — see the
        # separate warning below for whether a switch happened.
        base_warnings.append("LAYOUT_QUALITY_POOR")
    if reading_strategy != "XY_CUT":
        base_warnings.append(f"ADAPTIVE_RETRY_SWITCHED_TO_{reading_strategy}")

    target = TargetSection(
        desired_positions=desired_positions,
        desired_contract_types=desired_contract_types,
        desired_work_modes=desired_work_modes,
    )

    parse_quality = compute_parse_quality(
        document=document,
        sections=sections,
        layout_status=layout_status,
        reading_strategy=reading_strategy,
        identity=identity,
        experience=experience,
        skills=skills,
        base_warnings=base_warnings,
    )
    review_items = build_review_items(
        identity=identity, target=target, experience=experience, skills=skills, languages=languages
    )

    unknown_sections = [s for s in sections if s.section_type == "UNKNOWN"]
    meta = ParseMeta(
        parser_version=settings.parser_version,
        page_count=document.page_count,
        used_ocr=document.used_ocr,
        overall_page_state=overall_state,
        reading_strategy=reading_strategy,
        parse_duration_ms=round(duration_ms, 2),
        word_count=len(document.words),
        line_count=len(document.lines),
        block_count=len(document.blocks),
        sections_found=len(sections),
        unknown_section_count=len(unknown_sections),
    )

    draft = ParserDraftResponse(
        identity=identity,
        target=target,
        experience=experience,
        skills=skills,
        languages=languages,
        certifications=certifications,
        parse_quality=parse_quality,
        review_items=review_items,
        meta=meta,
    )
    return draft.model_dump(mode="json")


def extract_candidate_profile(pdf_bytes: bytes, source_name: str = "cv.pdf") -> dict:
    """PDF bytes in, normalized Candidate Knowledge Profile JSON out."""
    draft_dict = extract_profile(pdf_bytes, source_name=source_name)
    draft = ParserDraftResponse.model_validate(draft_dict)
    profile: CandidateKnowledgeProfile = normalize_candidate_profile(draft)
    return profile.model_dump(mode="json")
