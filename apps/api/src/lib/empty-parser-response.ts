/**
 * A synthetic, all-empty `RawParserResponse` used for the manual-entry
 * fallback (section 28): "Manual profile creation uses the same review form
 * with an empty draft." Routing it through the real adapter/persistence
 * pipeline (instead of a parallel code path) guarantees the manual flow can
 * never drift from the parsed flow.
 */
import type { RawParserResponse } from "../schemas/parser-response.schema.js";

export function buildEmptyParserResponse(): RawParserResponse {
  return {
    identity: { full_name: null, email: null, phone: null, country: null },
    target: { desired_positions: [], desired_contract_types: [], desired_work_modes: [] },
    experience: {
      professional_months: 0,
      internship_months: 0,
      alternance_months: 0,
      freelance_months: 0,
      records: [],
    },
    skills: { known: [], unmapped_technology_candidates: [] },
    languages: [],
    certifications: [],
    parse_quality: { status: "POOR", section_coverage: null, orphan_ratio: null, record_coherence: null, warnings: [] },
    review_items: [],
    meta: {
      parser_version: "manual-entry",
      page_count: 0,
      used_ocr: false,
      overall_page_state: null,
      reading_strategy: null,
      parse_duration_ms: null,
      word_count: 0,
      line_count: 0,
      block_count: 0,
      sections_found: 0,
      unknown_section_count: 0,
    },
  };
}
