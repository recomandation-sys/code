import { useMutation } from "@tanstack/react-query";
import type { CandidateProfileInput } from "@job-recommender/contracts";

import { profileApi } from "../../../api/profile.api.js";

export function useConfirmProfile() {
  return useMutation({
    mutationFn: (input: CandidateProfileInput) => profileApi.confirm(input),
  });
}
