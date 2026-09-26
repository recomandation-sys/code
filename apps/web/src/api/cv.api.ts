import type { CandidateDraft } from "@job-recommender/contracts";

import { apiRequest } from "./client.js";

export const cvApi = {
  async parse(file: File): Promise<CandidateDraft> {
    const form = new FormData();
    form.append("cv", file);
    const { draft } = await apiRequest<{ draft: CandidateDraft }>("/cv/parse", {
      method: "POST",
      formData: form,
    });
    return draft;
  },

  async createManualDraft(): Promise<CandidateDraft> {
    const { draft } = await apiRequest<{ draft: CandidateDraft }>("/cv/manual-draft", { method: "POST" });
    return draft;
  },

  async getDraft(draftId: string): Promise<CandidateDraft> {
    const { draft } = await apiRequest<{ draft: CandidateDraft }>(`/candidate-drafts/${draftId}`);
    return draft;
  },

  async discardDraft(draftId: string): Promise<void> {
    await apiRequest<void>(`/candidate-drafts/${draftId}`, { method: "DELETE" });
  },
};
