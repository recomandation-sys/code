import type { Prisma } from "@prisma/client";

import { prisma } from "../lib/prisma.js";

type Db = Prisma.TransactionClient | typeof prisma;

const profileInclude = {
  positions: true,
  preferences: true,
  educations: true,
  experiences: true,
  skills: { include: { skill: true } },
  customSkills: true,
  languages: true,
  certifications: true,
} satisfies Prisma.CandidateProfileInclude;

export type CandidateProfileWithRelations = Prisma.CandidateProfileGetPayload<{ include: typeof profileInclude }>;

export interface CreateProfileInput {
  sourceDraftId: string;
  fullName: string;
  firstName: string | null;
  lastName: string | null;
  email: string;
  phone: string | null;
  phoneCode: string | null;
  country: string | null;
  governorate: string | null;
  gender: string | null;
  dateOfBirth: Date | null;
  positions: string[];
  educations: Array<{
    degree: string;
    institution: string;
    field: string;
    startYear: number;
    startMonth: number | null;
    endYear: number | null;
    endMonth: number | null;
    isCurrent: boolean;
  }>;
  experiences: Array<{
    type: string;
    title: string;
    company: string | null;
    description: string | null;
    startYear: number;
    startMonth: number | null;
    endYear: number | null;
    endMonth: number | null;
    isCurrent: boolean;
    sourceRecordId: string | null;
  }>;
  skills: Array<{
    skillId: string;
    evidence: Array<{ sourceType: string; sourceRecordId: string | null }>;
  }>;
  customSkills: string[];
  languages: Array<{ language: string; level: string; rawLevel: string | null }>;
  certifications: Array<{
    name: string;
    issuer: string | null;
    year: number | null;
    issueMonth: number | null;
    expirationYear: number | null;
    expirationMonth: number | null;
    doesNotExpire: boolean;
    credentialId: string | null;
    credentialUrl: string | null;
  }>;
}

export const candidateProfileRepository = {
  async findByDraftId(draftId: string, db: Db = prisma): Promise<CandidateProfileWithRelations | null> {
    return db.candidateProfile.findUnique({ where: { sourceDraftId: draftId }, include: profileInclude });
  },

  async findById(id: string, db: Db = prisma): Promise<CandidateProfileWithRelations | null> {
    return db.candidateProfile.findUnique({ where: { id }, include: profileInclude });
  },

  async create(input: CreateProfileInput, db: Db = prisma): Promise<CandidateProfileWithRelations> {
    return db.candidateProfile.create({
      include: profileInclude,
      data: {
        sourceDraftId: input.sourceDraftId,
        fullName: input.fullName,
        firstName: input.firstName,
        lastName: input.lastName,
        email: input.email,
        phone: input.phone,
        phoneCode: input.phoneCode,
        country: input.country,
        governorate: input.governorate,
        gender: input.gender,
        dateOfBirth: input.dateOfBirth,
        positions: {
          create: input.positions.map((rawTitle) => ({ rawTitle })),
        },
        educations: {
          create: input.educations.map((edu) => ({
            degree: edu.degree,
            institution: edu.institution,
            field: edu.field,
            startYear: edu.startYear,
            startMonth: edu.startMonth,
            endYear: edu.endYear,
            endMonth: edu.endMonth,
            isCurrent: edu.isCurrent,
          })),
        },
        experiences: {
          create: input.experiences.map((exp) => ({
            type: exp.type as Prisma.CandidateExperienceCreateInput["type"],
            title: exp.title,
            company: exp.company,
            description: exp.description,
            startYear: exp.startYear,
            startMonth: exp.startMonth,
            endYear: exp.endYear,
            endMonth: exp.endMonth,
            isCurrent: exp.isCurrent,
            sourceRecordId: exp.sourceRecordId,
          })),
        },
        skills: {
          create: input.skills.map((s) => ({ skillId: s.skillId, userConfirmed: true })),
        },
        skillEvidence: {
          create: input.skills.flatMap((s) =>
            s.evidence.map((ev) => ({
              skillId: s.skillId,
              sourceType: ev.sourceType as Prisma.CandidateSkillEvidenceCreateInput["sourceType"],
              sourceRecordId: ev.sourceRecordId,
            })),
          ),
        },
        customSkills: {
          create: input.customSkills.map((rawName) => ({ rawName })),
        },
        languages: {
          create: input.languages.map((lang) => ({
            language: lang.language,
            level: lang.level as Prisma.CandidateLanguageCreateInput["level"],
            rawLevel: lang.rawLevel,
          })),
        },
        certifications: {
          create: input.certifications.map((cert) => ({
            name: cert.name,
            issuer: cert.issuer,
            year: cert.year,
            issueMonth: cert.issueMonth,
            expirationYear: cert.expirationYear,
            expirationMonth: cert.expirationMonth,
            doesNotExpire: cert.doesNotExpire,
            credentialId: cert.credentialId,
            credentialUrl: cert.credentialUrl,
          })),
        },
      },
    });
  },

  async replacePreferences(
    profileId: string,
    preferences: Array<{
      type: "CONTRACT_TYPE" | "WORK_MODE" | "MOBILITY" | "PREFERRED_COUNTRY" | "GOAL";
      value: string;
    }>,
    db: Db = prisma,
  ): Promise<CandidateProfileWithRelations> {
    await db.candidatePreference.deleteMany({ where: { candidateProfileId: profileId } });
    await db.candidateProfile.update({
      where: { id: profileId },
      data: {
        preferencesCompletedAt: new Date(),
        preferences: {
          create: preferences.map((pref) => ({ type: pref.type, value: pref.value })),
        },
      },
    });
    return db.candidateProfile.findUniqueOrThrow({ where: { id: profileId }, include: profileInclude });
  },
};
