/**
 * RawParserResponse -> CandidateDraftDTO (section 14).
 *
 * Responsibilities carried out here, and nowhere else:
 * - remove parser-only fields (raw section ids, reading strategy, etc.)
 * - stabilize naming (snake_case -> camelCase)
 * - normalize null/empty values
 * - convert parser confidence into a `needsReview` UI flag
 * - create stable ids for list items that need a React key / edit target
 * - preserve useful skill evidence (coarse source categories only)
 *
 * This function must never invent candidate facts — every value it produces
 * is either copied from the parser response or a deterministic derivation of
 * it (e.g. `needsReview` from `confidence`).
 */
import { randomUUID } from "node:crypto";

import type {
  Confidence,
  ContractType,
  DraftCertification,
  DraftExperience,
  DraftLanguage,
  DraftPosition,
  DraftSkill,
  DraftSkillEvidence,
  DraftUncertainSkill,
  EditableField,
  LanguageLevel,
  WorkMode,
} from "@job-recommender/contracts";

import type { RawParserResponse } from "../schemas/parser-response.schema.js";

export interface AdaptedCandidateDraft {
  identity: {
    fullName: EditableField<string>;
    email: EditableField<string>;
    phone: EditableField<string>;
    country: EditableField<string>;
  };
  target: {
    positions: DraftPosition[];
    contractTypes: ContractType[];
    workModes: WorkMode[];
  };
  experience: {
    professionalMonths: number;
    internshipMonths: number;
    alternanceMonths: number;
    freelanceMonths: number;
    records: DraftExperience[];
  };
  skills: {
    detected: DraftSkill[];
    uncertain: DraftUncertainSkill[];
  };
  languages: DraftLanguage[];
  certifications: DraftCertification[];
  quality: {
    status: "GOOD" | "FAIR" | "POOR";
    warnings: string[];
  };
  reviewSummary: {
    reviewRequired: boolean;
    itemCount: number;
  };
  parser: {
    version: string;
  };
}

function needsReview(confidence: Confidence, hasValue: boolean): boolean {
  if (!hasValue) return true;
  return confidence !== "HIGH";
}

function toEditableField(
  raw: { value: string | null; confidence: "HIGH" | "MEDIUM" | "LOW" } | null | undefined,
): EditableField<string> {
  const value = raw?.value ?? "";
  const confidence: Confidence = raw?.confidence ?? "UNKNOWN";
  return {
    value,
    confidence,
    needsReview: needsReview(confidence, value.trim().length > 0),
    parserValue: value,
  };
}

function mapEvidence(evidence: RawParserResponse["skills"]["known"][number]["evidence"]): DraftSkillEvidence[] {
  return evidence.map((item) => ({
    source: item.source_type,
    label: typeof item.source_label === "string" ? item.source_label : null,
    sourceRecordId: item.source_id ?? null,
  }));
}

function mapPosition(position: RawParserResponse["target"]["desired_positions"][number]): DraftPosition {
  return {
    id: randomUUID(),
    value: position.normalized ?? position.raw,
    confidence: position.confidence,
  };
}

function mapExperience(record: RawParserResponse["experience"]["records"][number]): DraftExperience {
  return {
    id: record.id,
    type: record.type,
    title: record.title ?? "",
    startYear: record.start_date?.year ?? null,
    startMonth: record.start_date?.month ?? null,
    endYear: record.end_date?.year ?? null,
    endMonth: record.end_date?.month ?? null,
    isCurrent: record.is_current,
    technologies: record.technologies,
    confidence: record.confidence,
  };
}

function mapKnownSkill(skill: RawParserResponse["skills"]["known"][number]): DraftSkill {
  return {
    id: randomUUID(),
    name: skill.canonical_name,
    category: skill.category,
    evidence: mapEvidence(skill.evidence),
  };
}

function mapUncertainSkill(candidate: RawParserResponse["skills"]["unmapped_technology_candidates"][number]): DraftUncertainSkill {
  return {
    id: randomUUID(),
    rawName: candidate.raw_name,
    evidence: mapEvidence(candidate.evidence),
  };
}

function mapLanguage(entry: RawParserResponse["languages"][number]): DraftLanguage {
  const level: LanguageLevel = entry.normalized_level ?? "UNKNOWN";
  return {
    id: randomUUID(),
    language: entry.language,
    level,
    rawLevel: entry.raw_level,
    confidence: entry.confidence,
  };
}

function mapCertification(entry: RawParserResponse["certifications"][number]): DraftCertification {
  return {
    id: entry.id,
    name: entry.name,
    issuer: entry.issuer,
    year: entry.date?.year ?? null,
  };
}

export function adaptParserResponseToDraft(raw: RawParserResponse): AdaptedCandidateDraft {
  return {
    identity: {
      fullName: toEditableField(raw.identity.full_name),
      email: toEditableField(raw.identity.email),
      phone: toEditableField(raw.identity.phone),
      country: toEditableField(raw.identity.country),
    },
    target: {
      positions: raw.target.desired_positions.map(mapPosition),
      contractTypes: raw.target.desired_contract_types,
      workModes: raw.target.desired_work_modes,
    },
    experience: {
      professionalMonths: raw.experience.professional_months,
      internshipMonths: raw.experience.internship_months,
      alternanceMonths: raw.experience.alternance_months,
      freelanceMonths: raw.experience.freelance_months,
      records: raw.experience.records.map(mapExperience),
    },
    skills: {
      detected: raw.skills.known.map(mapKnownSkill),
      uncertain: raw.skills.unmapped_technology_candidates.map(mapUncertainSkill),
    },
    languages: raw.languages.map(mapLanguage),
    certifications: raw.certifications.map(mapCertification),
    quality: {
      status: raw.parse_quality.status,
      warnings: raw.parse_quality.warnings,
    },
    reviewSummary: {
      reviewRequired: raw.review_items.length > 0 || raw.parse_quality.status !== "GOOD",
      itemCount: raw.review_items.length,
    },
    parser: {
      version: raw.meta.parser_version,
    },
  };
}
