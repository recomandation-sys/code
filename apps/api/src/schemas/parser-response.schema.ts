/**
 * Zod mirror of `cv_parser/schemas/parser_response.py` (`ParserDraftResponse`).
 * This is the ONLY place in the Node codebase allowed to know the raw Python
 * parser shape (section 13 / section 65) — everything downstream consumes
 * `RawParserResponse` and the adapter converts it into `CandidateDraftDTO`.
 *
 * `.passthrough()` is used on nested objects so new optional parser fields
 * (future metadata) don't break the web app (section 13), while every
 * business-critical field still gets an explicit, typed schema.
 */
import { z } from "zod";

const confidenceSchema = z.enum(["HIGH", "MEDIUM", "LOW"]);
const contractTypeSchema = z.enum(["CDI", "CDD", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "OTHER"]);
const workModeSchema = z.enum(["REMOTE", "HYBRID", "ONSITE"]);
const experienceTypeSchema = z.enum(["PROFESSIONAL", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "UNKNOWN"]);
const desiredPositionSourceTypeSchema = z.enum(["EXPLICIT_TARGET", "CV_HEADLINE", "PROFILE_STATEMENT"]);
const skillEvidenceSourceTypeSchema = z.enum([
  "SKILLS_SECTION",
  "PROFESSIONAL_EXPERIENCE",
  "INTERNSHIP",
  "ALTERNANCE",
  "PROJECT",
  "CERTIFICATION",
  "EDUCATION",
  "PROFILE",
]);
const cefrLevelSchema = z.enum([
  "A1",
  "A2",
  "B1",
  "B2",
  "C1",
  "C2",
  "NATIVE",
  "FLUENT",
  "ADVANCED",
  "INTERMEDIATE",
  "BASIC",
  "UNKNOWN",
]);
const parseQualityStatusSchema = z.enum(["GOOD", "FAIR", "POOR"]);

const confidentValueSchema = z
  .object({
    value: z.string().nullable().default(null),
    confidence: confidenceSchema.default("LOW"),
    method: z.string().nullable().default(null),
    reason_codes: z.array(z.string()).default([]),
  })
  .passthrough();

const identitySectionSchema = z
  .object({
    full_name: confidentValueSchema.nullable().default(null),
    email: confidentValueSchema.nullable().default(null),
    phone: confidentValueSchema.nullable().default(null),
    country: confidentValueSchema.nullable().default(null),
  })
  .passthrough();

const desiredPositionSchema = z
  .object({
    raw: z.string(),
    normalized: z.string().nullable().default(null),
    source_type: desiredPositionSourceTypeSchema,
    confidence: confidenceSchema,
  })
  .passthrough();

const targetSectionSchema = z
  .object({
    desired_positions: z.array(desiredPositionSchema).default([]),
    desired_contract_types: z.array(contractTypeSchema).default([]),
    desired_work_modes: z.array(workModeSchema).default([]),
  })
  .passthrough();

const partialDateSchema = z
  .object({
    year: z.number().int().nullable().default(null),
    month: z.number().int().nullable().default(null),
    day: z.number().int().nullable().default(null),
    precision: z.enum(["YEAR", "MONTH", "DAY"]).nullable().default(null),
  })
  .passthrough();

const experienceRecordSchema = z
  .object({
    id: z.string(),
    type: experienceTypeSchema,
    title: z.string().nullable().default(null),
    start_date: partialDateSchema.nullable().default(null),
    end_date: partialDateSchema.nullable().default(null),
    is_current: z.boolean().default(false),
    raw_text: z.string().nullable().default(null),
    technologies: z.array(z.string()).default([]),
    confidence: confidenceSchema.default("LOW"),
  })
  .passthrough();

const experienceSectionSchema = z
  .object({
    professional_months: z.number().int().default(0),
    internship_months: z.number().int().default(0),
    alternance_months: z.number().int().default(0),
    freelance_months: z.number().int().default(0),
    records: z.array(experienceRecordSchema).default([]),
  })
  .passthrough();

const skillEvidenceSchema = z
  .object({
    source_type: skillEvidenceSourceTypeSchema,
    source_id: z.string().nullable().default(null),
    raw_text: z.string().nullable().default(null),
  })
  .passthrough();

const knownSkillSchema = z
  .object({
    canonical_name: z.string(),
    category: z.string().nullable().default(null),
    raw_mentions: z.array(z.string()).default([]),
    evidence: z.array(skillEvidenceSchema).default([]),
  })
  .passthrough();

const unmappedTechnologySchema = z
  .object({
    raw_name: z.string(),
    known: z.boolean().default(false),
    source_type: skillEvidenceSourceTypeSchema.nullable().default(null),
    evidence: z.array(skillEvidenceSchema).default([]),
  })
  .passthrough();

const skillsSectionSchema = z
  .object({
    known: z.array(knownSkillSchema).default([]),
    unmapped_technology_candidates: z.array(unmappedTechnologySchema).default([]),
  })
  .passthrough();

const languageEntrySchema = z
  .object({
    language: z.string(),
    raw_level: z.string().nullable().default(null),
    normalized_level: cefrLevelSchema.nullable().default(null),
    confidence: confidenceSchema.default("LOW"),
  })
  .passthrough();

const certificationEntrySchema = z
  .object({
    id: z.string(),
    name: z.string(),
    issuer: z.string().nullable().default(null),
    date: partialDateSchema.nullable().default(null),
    technology_evidence: z.array(z.string()).default([]),
  })
  .passthrough();

const parseQualitySchema = z
  .object({
    status: parseQualityStatusSchema.default("GOOD"),
    section_coverage: z.number().nullable().default(null),
    orphan_ratio: z.number().nullable().default(null),
    record_coherence: z.number().nullable().default(null),
    warnings: z.array(z.string()).default([]),
  })
  .passthrough();

const reviewItemSchema = z
  .object({
    field: z.string(),
    reason: z.string(),
    confidence: confidenceSchema.nullable().default(null),
  })
  .passthrough();

const parseMetaSchema = z
  .object({
    parser_version: z.string(),
    page_count: z.number().int(),
    used_ocr: z.boolean().default(false),
    overall_page_state: z.string().nullable().default(null),
    reading_strategy: z.string().nullable().default(null),
    parse_duration_ms: z.number().nullable().default(null),
    word_count: z.number().int().default(0),
    line_count: z.number().int().default(0),
    block_count: z.number().int().default(0),
    sections_found: z.number().int().default(0),
    unknown_section_count: z.number().int().default(0),
  })
  .passthrough();

export const rawParserResponseSchema = z
  .object({
    identity: identitySectionSchema.default({}),
    target: targetSectionSchema.default({}),
    experience: experienceSectionSchema.default({}),
    skills: skillsSectionSchema.default({}),
    languages: z.array(languageEntrySchema).default([]),
    certifications: z.array(certificationEntrySchema).default([]),
    parse_quality: parseQualitySchema.default({}),
    review_items: z.array(reviewItemSchema).default([]),
    meta: parseMetaSchema,
  })
  .passthrough();

export type RawParserResponse = z.infer<typeof rawParserResponseSchema>;

export const parserErrorBodySchema = z.object({
  code: z.string(),
  message: z.string(),
});
