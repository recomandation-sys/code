import { useMutation } from "@tanstack/react-query";
import type { CandidatePreferenceSurveyInput, CandidatePreferenceSurveyResponse } from "@job-recommender/contracts";

import { profileApi } from "../../../api/profile.api.js";

export function useSubmitPreferenceSurvey() {
  return useMutation<CandidatePreferenceSurveyResponse, Error, CandidatePreferenceSurveyInput>({
    mutationFn: (input) => profileApi.submitPreferenceSurvey(input),
  });
}
