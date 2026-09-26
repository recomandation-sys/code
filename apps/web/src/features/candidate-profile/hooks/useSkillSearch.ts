import { useQuery } from "@tanstack/react-query";

import { profileApi } from "../../../api/profile.api.js";

export function useSkillSearch(query: string) {
  return useQuery({
    queryKey: ["skill-search", query],
    queryFn: () => profileApi.searchSkills(query),
    enabled: query.trim().length > 1,
    staleTime: 30_000,
  });
}
