import type { CandidateDraft } from "@job-recommender/contracts";
import type { CvParseDraft } from "@prisma/client";

import type { AdaptedCandidateDraft } from "./parser-to-draft.adapter.js";

/**
 * `id` and `status` live as real columns on `CvParseDraft`, not inside the
 * stored `ui_draft` JSON blob, so this stitches them back together for the
 * client (section 15).
 */
export function composeDraftDTO(row: CvParseDraft): CandidateDraft {
  const body = row.uiDraft as unknown as AdaptedCandidateDraft;
  const status = row.status === "PARSED" || row.status === "EDITING" ? row.status : "EDITING";

  return {
    id: row.id,
    status,
    parserVersion: row.parserVersion,
    ...body,
  };
}
