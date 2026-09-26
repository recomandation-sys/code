/**
 * Client-side validation only (section 49) — mirrors, but does not replace,
 * the authoritative rules enforced by the Express API (section 50).
 */
import { z } from "zod";
import { EXPERIENCE_TYPES, LANGUAGE_LEVELS } from "@job-recommender/contracts";

const currentYear = new Date().getFullYear();

const experienceFieldSchema = z
  .object({
    id: z.string(),
    type: z.enum(EXPERIENCE_TYPES),
    title: z.string().trim().min(1, "Title is required"),
    startYear: z.number().int().min(1950).max(currentYear + 1),
    startMonth: z.number().int().min(1).max(12).nullable(),
    endYear: z.number().int().min(1950).max(currentYear + 1).nullable(),
    endMonth: z.number().int().min(1).max(12).nullable(),
    isCurrent: z.boolean(),
    technologies: z.array(z.string()),
  })
  .superRefine((record, ctx) => {
    if (!record.isCurrent && record.endYear === null) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "End year is required", path: ["endYear"] });
    }
    if (record.endYear !== null) {
      const start = record.startYear * 12 + (record.startMonth ?? 1);
      const end = record.endYear * 12 + (record.endMonth ?? 12);
      if (end < start) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message: "End date is before start date", path: ["endYear"] });
      }
    }
  });

export const reviewFormSchema = z.object({
  identity: z.object({
    fullName: z.string().trim().min(1, "Full name is required"),
    email: z.string().trim().email("Enter a valid email address"),
    phone: z.string().trim().max(40).optional(),
    country: z.string().trim().max(120).optional(),
  }),
  positions: z.array(z.string().trim().min(1)).min(1, "Add at least one target position"),
  experience: z.array(experienceFieldSchema),
  skills: z.array(z.object({ id: z.string(), name: z.string() })),
  customSkills: z.array(z.string().trim().min(1)),
  uncertainSkills: z.array(z.object({ id: z.string(), rawName: z.string() })),
  languages: z.array(
    z.object({
      id: z.string(),
      language: z.string().trim().min(1),
      level: z.enum(LANGUAGE_LEVELS),
    }),
  ),
  certifications: z.array(
    z.object({
      id: z.string(),
      name: z.string().trim().min(1, "Certification name is required"),
      issuer: z.string().nullable(),
      year: z.number().int().nullable(),
    }),
  ),
});

export type ReviewFormValues = z.infer<typeof reviewFormSchema>;
