"""Central configuration for the deterministic CV extraction pipeline.

Every threshold lives here so no stage hard-codes a magic number, and every
value is overridable via environment variables (prefix ``CVPARSER_``) or a
``.env`` file. Per the architecture contract (README_CV_EXTRACTION_ARCHITECTURE.md
section 61), thresholds must be documented, test-covered, and never tuned
against a single CV.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CVPARSER_", env_file=".env", extra="ignore")

    parser_version: str = "3.0.0"

    # ---- file validation (section 7) ----
    max_pdf_size_mb: float = 20.0
    max_pdf_pages: int = 15

    # ---- native-text quality gate (section 10) ----
    # Below this many characters on a page, native extraction is treated as
    # too thin to trust and OCR becomes a candidate.
    native_text_min_chars_per_page: int = 40
    # "SUSPECT" band: enough text to not be POOR, but thin enough to flag.
    native_text_suspect_chars_per_page: int = 120
    # Fraction of unicode replacement characters (U+FFFD) tolerated before
    # the page text is considered corrupted.
    native_text_max_bad_char_ratio: float = 0.02
    # Fraction of extracted "words" that are a single character before we
    # suspect the text layer is fragmented glyph-by-glyph (a common broken
    # -PDF-producer symptom that looks nothing like real prose in any
    # language).
    native_text_max_single_char_word_ratio: float = 0.5
    native_text_suspect_single_char_word_ratio: float = 0.2
    # Above this fraction of page area covered by raster images while text
    # is thin, the page is more likely a scan than a broken digital page.
    native_text_scan_image_coverage_ratio: float = 0.3

    # ---- geometric deduplication (section 13) ----
    dedup_position_tolerance_pt: float = 1.0

    # ---- line/block reconstruction (section 14, refined in Phase B) ----
    # Vertical gap between consecutive lines (as a multiple of the local
    # font height) above which a new block starts.
    block_gap_font_multiple: float = 0.9

    # ---- layout: region/column detection + XY-Cut (Phase B, sections 15-16) ----
    # Minimum horizontal whitespace gap, as a fraction of page width,
    # before two side-by-side content bands are treated as separate
    # columns rather than natural word/line spacing.
    layout_column_gap_ratio: float = 0.03
    # Minimum vertical whitespace gap, as a fraction of page height,
    # before two vertically-stacked bands are treated as separate regions
    # (e.g. a full-width header vs. the multi-column body below it).
    layout_band_gap_ratio: float = 0.01

    # ---- structure discovery: heading detection (Phase C, section 17) ----
    heading_score_strong: float = 2.5
    heading_score_candidate_min: float = 1.0
    heading_relative_font_large: float = 1.15
    heading_relative_font_medium: float = 1.05
    heading_bold_ratio_threshold: float = 0.6

    # ---- structure discovery: heading vs. content-line disambiguation
    # (Phase C, hardened after Phase G corpus testing) ----
    # A short, bold "Label : filled-in value" line (e.g. "Nationality :
    # Indian", "Marital Status : Single") is data, not a section heading,
    # no matter how heading-shaped its style looks — real section
    # headings are bare labels, never already-answered fields. Both sides
    # of the colon must stay this short for the line to be treated as
    # such a data row (a long value, e.g. an inline "Skills: Python,
    # Java, ..." list, is deliberately left alone).
    personal_detail_line_max_label_words: int = 3
    personal_detail_line_max_value_words: int = 4

    # ---- structure discovery: section classification (Phase C, section 18) ----
    heading_fuzzy_cutoff: int = 90
    # A real section title is always short (our longest known alias is 4
    # words). Anything longer is never even attempted against the alias
    # list — RapidFuzz's substring-friendly scorers can otherwise inflate
    # a long sentence that merely *starts with* an alias-like word (e.g.
    # "Technologies: Llama, MERN stack, ...") into a false "SKILLS" match.
    heading_classification_max_words: int = 6
    supported_section_alias_packs: tuple[str, ...] = ("en", "fr", "ar")

    # ---- record segmentation (Phase C, section 20) ----
    record_anchor_max_words: int = 12
    record_anchor_relative_font: float = 1.05
    record_anchor_bold_ratio: float = 0.5

    # ---- IT Skill Engine (Phase E, sections 27-40) ----
    # nesta_tech_v2 = same EnSkillStack as jobs (Nesta + Tech Taxonomy V2)
    # lexicon = legacy Aho-Corasick only
    # hybrid = Nesta+V2 primary, lexicon exact matches merged for tech coverage
    skill_engine: str = "nesta_tech_v2"
    skill_fuzzy_cutoff: int = 92
    ambiguous_skill_context_window_chars: int = 80
    # RapidFuzz is only ever tried on an already-isolated technology-list
    # segment (never on narrative prose) that is at least this long —
    # short ambiguous fragments must go through exact/context rules only
    # (section 36).
    skill_min_fuzzy_term_chars: int = 4

    # ---- layout quality / adaptive retry (Phase B / G, sections 16, 48) ----
    # Fraction of consecutive reading-order transitions that may switch
    # column before a multi-column layout is considered incoherently
    # interleaved (section 48).
    layout_retry_column_switch_threshold: float = 0.35
    # "Many visible dates but no experience records" retry trigger
    # (section 48): year-like tokens found in the document text at or
    # above this count, combined with zero extracted experience records,
    # is treated as a sign that reading order scrambled the experience
    # section rather than the CV genuinely having no work history.
    adaptive_retry_min_year_tokens: int = 3

    # ---- record-level confidence (Phase G, section 46) ----
    # A record needs a real (multi-word) title to count as "has a title"
    # signal for confidence purposes; a single-word anchor is too weak.
    record_meaningful_title_min_words: int = 2
    # A record needs more than just its anchor/title line to count as
    # having a "body" signal.
    record_meaningful_body_min_lines: int = 2

    # ---- whole-parse quality (Phase G, section 47) ----
    quality_min_section_coverage_good: float = 0.5
    quality_max_unknown_ratio_good: float = 0.34
    # A single CV realistically demonstrates at most a few dozen distinct
    # technologies; far more than this in one parse is more likely an
    # over-eager match than genuine breadth, and is surfaced as a
    # diagnostic warning (never silently dropped — section 4.4).
    quality_suspicious_skill_count: int = 60

    # ---- OCR fallback (Phase H) ----
    ocr_dpi: int = 300
    tesseract_cmd: str | None = None
    tesseract_langs: str = "eng+fra+ara"


settings = Settings()

for _dir in (DATA_DIR,):
    _dir.mkdir(parents=True, exist_ok=True)
