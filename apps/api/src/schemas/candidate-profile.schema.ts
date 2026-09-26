/**
 * Confirmation input validation (sections 35, 50). This is the authoritative
 * application-level validation — client-side Zod is UX only (section 49).
 */
import { z } from "zod";

const CONTRACT_TYPES = ["CDI", "CDD", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "OTHER"] as const;
const WORK_MODES = ["REMOTE", "HYBRID", "ONSITE"] as const;
const EXPERIENCE_TYPES = ["PROFESSIONAL", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "UNKNOWN"] as const;
const LANGUAGE_LEVELS = [
  "A1",
  "A2",
  "B1",
  "B2",
  "C1",
  "C2",
  "NATIVE",
  "FLUENT",
  "ADVANCED",
  "INTERMEDIATE",
  "BASIC",
  "UNKNOWN",
] as const;

const MIN_YEAR = 1950;
const MAX_YEAR = new Date().getFullYear() + 1;

const datedRangeRefine = <T extends {
  startYear: number;
  startMonth: number | null;
  endYear: number | null;
  endMonth: number | null;
  isCurrent: boolean;
}>(
  record: T,
  ctx: z.RefinementCtx,
  currentMessage: string,
) => {
  if (record.isCurrent && (record.endYear !== null || record.endMonth !== null)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: currentMessage,
      path: ["endYear"],
    });
  }
  if (!record.isCurrent && record.endYear === null) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "End year is required unless the record is marked as current.",
      path: ["endYear"],
    });
  }
  if (record.endYear !== null) {
    const startIndex = record.startYear * 12 + (record.startMonth ?? 1);
    const endIndex = record.endYear * 12 + (record.endMonth ?? 12);
    if (endIndex < startIndex) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "End date cannot precede start date.",
        path: ["endYear"],
      });
    }
  }
};

const experienceInputSchema = z
  .object({
    id: z.string().uuid().optional(),
    type: z.enum(EXPERIENCE_TYPES),
    title: z.string().trim().min(1, "Title is required").max(200),
    company: z.string().trim().max(200).nullable().optional(),
    description: z.string().trim().max(2000).nullable().optional(),
    startYear: z.number().int().min(MIN_YEAR).max(MAX_YEAR),
    startMonth: z.number().int().min(1).max(12).nullable(),
    endYear: z.number().int().min(MIN_YEAR).max(MAX_YEAR).nullable(),
    endMonth: z.number().int().min(1).max(12).nullable(),
    isCurrent: z.boolean(),
  })
  .superRefine((record, ctx) =>
    datedRangeRefine(record, ctx, "A current experience record cannot have an end date."),
  );

const educationInputSchema = z
  .object({
    id: z.string().uuid().optional(),
    degree: z.string().trim().min(1, "Degree is required").max(200),
    institution: z.string().trim().min(1, "Institution is required").max(200),
    field: z.string().trim().min(1, "Field is required").max(200),
    startYear: z.number().int().min(MIN_YEAR).max(MAX_YEAR),
    startMonth: z.number().int().min(1).max(12).nullable(),
    endYear: z.number().int().min(MIN_YEAR).max(MAX_YEAR).nullable(),
    endMonth: z.number().int().min(1).max(12).nullable(),
    isCurrent: z.boolean(),
  })
  .superRefine((record, ctx) =>
    datedRangeRefine(record, ctx, "A current education record cannot have an end date."),
  );

const skillInputSchema = z.object({
  skillId: z.string().trim().min(1),
  evidence: z
    .array(
      z.object({
        source: z.string().trim().min(1),
        label: z.string().trim().max(200).nullable().optional(),
        sourceRecordId: z.string().trim().max(120).nullable().optional(),
      }),
    )
    .optional(),
});
const customSkillInputSchema = z.object({ rawName: z.string().trim().min(1).max(120) });
const languageInputSchema = z.object({
  language: z.string().trim().min(1).max(80),
  level: z.enum(LANGUAGE_LEVELS),
});
const certificationInputSchema = z.object({
  id: z.string().uuid().optional(),
  name: z.string().trim().min(1, "Certification name is required").max(200),
  issuer: z.string().trim().max(200).nullable().optional(),
  year: z.number().int().min(MIN_YEAR).max(MAX_YEAR).nullable().optional(),
  issueMonth: z.number().int().min(1).max(12).nullable().optional(),
  expirationYear: z.number().int().min(MIN_YEAR).max(MAX_YEAR + 30).nullable().optional(),
  expirationMonth: z.number().int().min(1).max(12).nullable().optional(),
  doesNotExpire: z.boolean().optional(),
  credentialId: z.string().trim().max(120).nullable().optional(),
  credentialUrl: z.string().trim().max(500).nullable().optional(),
});

export const candidateProfileInputSchema = z
  .object({
    draftId: z.string().uuid(),

    identity: z.object({
      fullName: z.string().trim().min(1, "Full name is required").max(200),
      firstName: z.string().trim().max(100).optional(),
      lastName: z.string().trim().max(100).optional(),
      email: z.string().trim().toLowerCase().email("Invalid email address"),
      phone: z.string().trim().max(40).optional(),
      phoneCode: z.string().trim().max(8).optional(),
      country: z.string().trim().max(120).optional(),
      governorate: z.string().trim().max(120).optional(),
      gender: z.string().trim().max(40).optional(),
      dateOfBirth: z
        .string()
        .trim()
        .regex(/^\d{4}-\d{2}-\d{2}$/, "dateOfBirth must be YYYY-MM-DD")
        .nullable()
        .optional(),
    }),

    target: z.object({
      positions: z
        .array(z.string().trim().min(1).max(150))
        .min(1, "At least one desired position is required"),
    }),

    education: z
      .object({
        records: z.array(educationInputSchema).default([]),
      })
      .optional(),

    experience: z.object({
      records: z.array(experienceInputSchema).default([]),
    }),

    skills: z.array(skillInputSchema).default([]),
    customSkills: z.array(customSkillInputSchema).default([]),
    languages: z.array(languageInputSchema).default([]),
    certifications: z.array(certificationInputSchema).default([]),
  })
  .transform((input) => ({
    ...input,
    education: { records: input.education?.records ?? [] },
    target: {
      ...input.target,
      positions: dedupeCaseInsensitive(input.target.positions),
    },
    skills: dedupeBy(input.skills, (s) => s.skillId),
    languages: dedupeBy(input.languages, (l) => l.language.trim().toLowerCase()),
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

function dedupeBy<T>(values: T[], keyFn: (value: T) => string): T[] {
  const seen = new Set<string>();
  const result: T[] = [];
  for (const value of values) {
    const key = keyFn(value);
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(value);
  }
  return result;
}

export type CandidateProfileInputValidated = z.infer<typeof candidateProfileInputSchema>;
