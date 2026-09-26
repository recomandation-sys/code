/**
 * Post-validation job preference survey validation.
 */
import { z } from "zod";

const CONTRACT_TYPES = ["CDI", "CDD", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "OTHER"] as const;
const WORK_MODES = ["REMOTE", "HYBRID", "ONSITE"] as const;
const MOBILITY_PREFERENCES = ["LOCAL", "FOREIGN", "REMOTE"] as const;

export const candidatePreferenceSurveySchema = z
  .object({
    profileId: z.string().uuid(),
    contractTypes: z.array(z.enum(CONTRACT_TYPES)).min(1, "Select at least one contract type"),
    workModes: z.array(z.enum(WORK_MODES)).default([]),
    mobilityPreferences: z.array(z.enum(MOBILITY_PREFERENCES)).min(1, "Select at least one mobility option"),
    preferredCountries: z.array(z.string().trim().min(1).max(80)).default([]),
    goals: z.array(z.enum(["FIND_JOB", "OPTIMIZE_PROFILE"])).default([]),
  })
  .transform((input) => ({
    ...input,
    preferredCountries: dedupeCaseInsensitive(input.preferredCountries),
    goals: [...new Set(input.goals)],
  }));

function dedupeCaseInsensitive(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    const key = value.trim().toLowerCase();
    if (key.length === 0 || seen.has(key)) continue;
    seen.add(key);
    result.push(value.trim());
  }
  return result;
}

export type CandidatePreferenceSurveyValidated = z.infer<typeof candidatePreferenceSurveySchema>;
