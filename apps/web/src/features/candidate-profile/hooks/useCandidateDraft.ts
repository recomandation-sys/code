import { useQuery } from "@tanstack/react-query";

import { cvApi } from "../../../api/cv.api.js";

export function useCandidateDraft(draftId: string | undefined) {
  return useQuery({
    queryKey: ["candidate-draft", draftId],
    queryFn: () => cvApi.getDraft(draftId as string),
    enabled: Boolean(draftId),
    staleTime: Infinity,
    retry: false,
  });
}
