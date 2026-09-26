import { useMutation } from "@tanstack/react-query";

import { cvApi } from "../../../api/cv.api.js";

export function useParseCv() {
  return useMutation({
    mutationFn: (file: File) => cvApi.parse(file),
  });
}
