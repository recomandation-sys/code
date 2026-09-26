import { useQuery } from "@tanstack/react-query";

import { profileApi } from "../../../api/profile.api.js";

export function useCandidateProfile(profileId: string | undefined) {
  return useQuery({
    queryKey: ["candidate-profile", profileId],
    queryFn: () => profileApi.getProfile(profileId as string),
    enabled: Boolean(profileId),
  });
}
