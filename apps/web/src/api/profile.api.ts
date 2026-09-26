import type {
  CandidatePreferenceSurveyInput,
  CandidatePreferenceSurveyResponse,
  CandidateProfileInput,
  CandidateProfileResponse,
} from "@job-recommender/contracts";

import { apiRequest } from "./client.js";

export interface SkillSearchResult {
  id: string;
  name: string;
  category: string | null;
}

export const profileApi = {
  async confirm(input: CandidateProfileInput): Promise<CandidateProfileResponse> {
    const { profile } = await apiRequest<{ profile: CandidateProfileResponse }>("/candidate-profiles/confirm", {
      method: "POST",
      body: input,
    });
    return profile;
  },

  async getProfile(profileId: string): Promise<CandidateProfileResponse> {
    const { profile } = await apiRequest<{ profile: CandidateProfileResponse }>(
      `/candidate-profile?profileId=${encodeURIComponent(profileId)}`,
    );
    return profile;
  },

  async submitPreferenceSurvey(input: CandidatePreferenceSurveyInput): Promise<CandidatePreferenceSurveyResponse> {
    const { survey } = await apiRequest<{ survey: CandidatePreferenceSurveyResponse }>(
      "/candidate-profiles/preferences",
      {
        method: "POST",
        body: input,
      },
    );
    return survey;
  },

  async searchSkills(query: string): Promise<SkillSearchResult[]> {
    if (query.trim().length === 0) return [];
    return apiRequest<SkillSearchResult[]>(`/skills?query=${encodeURIComponent(query)}`);
  },
};
