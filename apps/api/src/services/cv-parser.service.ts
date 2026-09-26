/**
 * Use-case orchestration for "parse a CV" (section 31):
 * call parser -> validate response (done inside the client) -> adapt draft
 * -> resolve canonical skill ids -> persist draft -> return draft.
 */
import type { Prisma } from "@prisma/client";

import { composeDraftDTO } from "../adapters/compose-draft-dto.js";
import { type AdaptedCandidateDraft, adaptParserResponseToDraft } from "../adapters/parser-to-draft.adapter.js";
import { type UploadedPdf, cvParserClient } from "../clients/cv-parser.client.js";
import { buildEmptyParserResponse } from "../lib/empty-parser-response.js";
import { candidateDraftRepository } from "../repositories/candidate-draft.repository.js";
import { skillRepository } from "../repositories/skill.repository.js";
import type { RawParserResponse } from "../schemas/parser-response.schema.js";
import type { CandidateDraft } from "@job-recommender/contracts";

/**
 * The parser vouches for its `known` skills (they only ever come from the
 * curated IT lexicon), so this resolves each one to a stable, real
 * `Skill.id` before the draft is ever shown to the user — that id is what
 * the frontend echoes back verbatim in the confirmation payload
 * (section 35, section 69).
 */
async function resolveKnownSkillIds(draft: AdaptedCandidateDraft): Promise<AdaptedCandidateDraft> {
  const resolved = await Promise.all(
    draft.skills.detected.map(async (skill) => {
      const row = await skillRepository.findOrCreateByCanonicalName(skill.name, skill.category);
      return { ...skill, id: row.id };
    }),
  );
  return { ...draft, skills: { ...draft.skills, detected: resolved } };
}

export const cvParserService = {
  async parseCv(file: UploadedPdf, requestId: string): Promise<CandidateDraft> {
    const raw: RawParserResponse = await cvParserClient.parsePdf(file, requestId);
    const adapted = await resolveKnownSkillIds(adaptParserResponseToDraft(raw));

    const draftRow = await candidateDraftRepository.create({
      parserVersion: raw.meta.parser_version,
      parseQuality: raw.parse_quality.status,
      rawParserResult: raw as unknown as Prisma.InputJsonValue,
      uiDraft: adapted as unknown as Prisma.InputJsonValue,
    });

    return composeDraftDTO(draftRow);
  },

  /** Manual-entry fallback (section 28): same pipeline, no PDF, no parser call. */
  async createManualDraft(): Promise<CandidateDraft> {
    const raw = buildEmptyParserResponse();
    const adapted = adaptParserResponseToDraft(raw);

    const draftRow = await candidateDraftRepository.create({
      parserVersion: raw.meta.parser_version,
      parseQuality: raw.parse_quality.status,
      rawParserResult: raw as unknown as Prisma.InputJsonValue,
      uiDraft: adapted as unknown as Prisma.InputJsonValue,
    });

    return composeDraftDTO(draftRow);
  },
};
