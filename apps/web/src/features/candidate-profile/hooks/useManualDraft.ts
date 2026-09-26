import { useMutation } from "@tanstack/react-query";

import { cvApi } from "../../../api/cv.api.js";

export function useManualDraft() {
  return useMutation({
    mutationFn: () => cvApi.createManualDraft(),
  });
}
