import { z } from "zod";
import { CONTRACT_TYPES, MOBILITY_PREFERENCES, WORK_MODES } from "@job-recommender/contracts";

export const preferenceSurveySchema = z.object({
  contractTypes: z.array(z.enum(CONTRACT_TYPES)).min(1, "Select at least one contract type"),
  workModes: z.array(z.enum(WORK_MODES)),
  mobilityPreferences: z.array(z.enum(MOBILITY_PREFERENCES)).min(1, "Select at least one mobility option"),
  preferredCountries: z.array(z.string().trim().min(1)),
});

export type PreferenceSurveyValues = z.infer<typeof preferenceSurveySchema>;
