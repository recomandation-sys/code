/**
 * Draft lifecycle rules (section 37 / section 60). Loading a draft for
 * review or confirmation always goes through here so expiry/discard rules
 * are enforced in exactly one place.
 */
import type { CvParseDraft } from "@prisma/client";

import { AppError } from "../errors/app-error.js";
import { candidateDraftRepository } from "../repositories/candidate-draft.repository.js";

function isExpired(draft: CvParseDraft): boolean {
  return draft.expiresAt !== null && draft.expiresAt.getTime() < Date.now();
}

export const candidateDraftService = {
  async getReviewableDraft(draftId: string): Promise<CvParseDraft> {
    const draft = await candidateDraftRepository.findById(draftId);
    if (!draft) {
      throw new AppError("DRAFT_NOT_FOUND", "This draft no longer exists.");
    }
    if (draft.status === "DISCARDED") {
      throw new AppError("DRAFT_DISCARDED", "This draft has been discarded.");
    }
    if (draft.status === "EXPIRED" || isExpired(draft)) {
      throw new AppError("DRAFT_EXPIRED", "This draft has expired. Please upload your CV again.");
    }
    return draft;
  },
};
