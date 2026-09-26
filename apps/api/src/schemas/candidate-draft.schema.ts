import { z } from "zod";

export const draftIdParamsSchema = z.object({
  draftId: z.string().uuid("draftId must be a valid UUID"),
});

export type DraftIdParams = z.infer<typeof draftIdParamsSchema>;
