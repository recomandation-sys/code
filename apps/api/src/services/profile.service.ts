/**
 * Confirmation and preference survey use cases.
 */
import type { CandidatePreferenceSurveyResponse, CandidateProfileResponse } from "@job-recommender/contracts";

import { AppError } from "../errors/app-error.js";
import { computeExperienceTotals } from "../lib/experience-duration.js";
import { prisma } from "../lib/prisma.js";
import {
  type CandidateProfileWithRelations,
  candidateProfileRepository,
} from "../repositories/candidate-profile.repository.js";
import { candidateDraftRepository } from "../repositories/candidate-draft.repository.js";
import { skillRepository } from "../repositories/skill.repository.js";
import type { CandidateProfileInputValidated } from "../schemas/candidate-profile.schema.js";
import type { CandidatePreferenceSurveyValidated } from "../schemas/candidate-preferences-survey.schema.js";
import { candidateDraftService } from "./candidate-draft.service.js";

function toResponse(profile: CandidateProfileWithRelations): CandidateProfileResponse {
  const totals = computeExperienceTotals(
    profile.experiences.map((exp) => ({
      type: exp.type,
      startYear: exp.startYear,
      startMonth: exp.startMonth,
      endYear: exp.endYear,
      endMonth: exp.endMonth,
      isCurrent: exp.isCurrent,
    })),
  );

  return {
    id: profile.id,
    fullName: profile.fullName,
    firstName: profile.firstName,
    lastName: profile.lastName,
    email: profile.email,
    phone: profile.phone,
    phoneCode: profile.phoneCode,
    country: profile.country,
    governorate: profile.governorate,
    gender: profile.gender,
    dateOfBirth: profile.dateOfBirth ? profile.dateOfBirth.toISOString().slice(0, 10) : null,
    target: {
      positions: profile.positions.map((p) => p.normalizedTitle ?? p.rawTitle),
      contractTypes: profile.preferences
        .filter((p) => p.type === "CONTRACT_TYPE")
        .map((p) => p.value) as CandidateProfileResponse["target"]["contractTypes"],
      workModes: profile.preferences
        .filter((p) => p.type === "WORK_MODE")
        .map((p) => p.value) as CandidateProfileResponse["target"]["workModes"],
      mobilityPreferences: profile.preferences
        .filter((p) => p.type === "MOBILITY")
        .map((p) => p.value) as CandidateProfileResponse["target"]["mobilityPreferences"],
      preferredCountries: profile.preferences.filter((p) => p.type === "PREFERRED_COUNTRY").map((p) => p.value),
      goals: profile.preferences
        .filter((p) => p.type === "GOAL")
        .map((p) => p.value) as CandidateProfileResponse["target"]["goals"],
    },
    education: {
      records: profile.educations.map((edu) => ({
        id: edu.id,
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
    experience: {
      ...totals,
      records: profile.experiences.map((exp) => ({
        id: exp.id,
        type: exp.type,
        title: exp.title,
        company: exp.company,
        description: exp.description,
        startYear: exp.startYear,
        startMonth: exp.startMonth,
        endYear: exp.endYear,
        endMonth: exp.endMonth,
        isCurrent: exp.isCurrent,
      })),
    },
    skills: profile.skills.map((s) => ({ id: s.skill.id, name: s.skill.canonicalName, category: s.skill.category })),
    customSkills: profile.customSkills.map((s) => s.rawName),
    languages: profile.languages.map((l) => ({ id: l.id, language: l.language, level: l.level })),
    certifications: profile.certifications.map((c) => ({
      id: c.id,
      name: c.name,
      issuer: c.issuer,
      year: c.year,
      issueMonth: c.issueMonth,
      expirationYear: c.expirationYear,
      expirationMonth: c.expirationMonth,
      doesNotExpire: c.doesNotExpire,
      credentialId: c.credentialId,
      credentialUrl: c.credentialUrl,
    })),
    preferencesCompletedAt: profile.preferencesCompletedAt?.toISOString() ?? null,
    createdAt: profile.createdAt.toISOString(),
    updatedAt: profile.updatedAt.toISOString(),
  };
}

function toSurveyResponse(profile: CandidateProfileWithRelations): CandidatePreferenceSurveyResponse {
  const response = toResponse(profile);
  return {
    profileId: profile.id,
    contractTypes: response.target.contractTypes,
    workModes: response.target.workModes,
    mobilityPreferences: response.target.mobilityPreferences,
    preferredCountries: response.target.preferredCountries,
    goals: response.target.goals,
    preferencesCompletedAt: response.preferencesCompletedAt ?? new Date().toISOString(),
  };
}

export const profileService = {
  async confirm(input: CandidateProfileInputValidated): Promise<CandidateProfileResponse> {
    const draft = await candidateDraftService.getReviewableDraft(input.draftId);

    if (draft.status === "CONFIRMED") {
      const existing = await candidateProfileRepository.findByDraftId(draft.id);
      if (existing) return toResponse(existing);
      throw new AppError("PROFILE_INVALID", "This draft was confirmed but its profile could not be found.");
    }

    const requestedSkillIds = input.skills.map((s) => s.skillId);
    const foundSkills = await skillRepository.findManyByIds(requestedSkillIds);
    const foundIds = new Set(foundSkills.map((s) => s.id));
    const missingIds = requestedSkillIds.filter((id) => !foundIds.has(id));
    if (missingIds.length > 0) {
      throw new AppError("PROFILE_INVALID", "One or more selected skills are not recognized.", missingIds);
    }

    const created = await prisma.$transaction(async (tx) => {
      const profile = await candidateProfileRepository.create(
        {
          sourceDraftId: draft.id,
          fullName: input.identity.fullName,
          firstName: input.identity.firstName?.trim() || null,
          lastName: input.identity.lastName?.trim() || null,
          email: input.identity.email,
          phone: input.identity.phone?.trim() || null,
          phoneCode: input.identity.phoneCode?.trim() || null,
          country: input.identity.country?.trim() || null,
          governorate: input.identity.governorate?.trim() || null,
          gender: input.identity.gender?.trim() || null,
          dateOfBirth: input.identity.dateOfBirth ? new Date(input.identity.dateOfBirth) : null,
          positions: input.target.positions,
          educations: input.education.records.map((r) => ({
            degree: r.degree,
            institution: r.institution,
            field: r.field,
            startYear: r.startYear,
            startMonth: r.startMonth,
            endYear: r.endYear,
            endMonth: r.endMonth,
            isCurrent: r.isCurrent,
          })),
          experiences: input.experience.records.map((r) => ({
            type: r.type,
            title: r.title,
            company: r.company?.trim() || null,
            description: r.description?.trim() || null,
            startYear: r.startYear,
            startMonth: r.startMonth,
            endYear: r.endYear,
            endMonth: r.endMonth,
            isCurrent: r.isCurrent,
            sourceRecordId: r.id ?? null,
          })),
          skills: input.skills.map((s) => ({
            skillId: s.skillId,
            evidence: (s.evidence ?? []).map((ev) => ({
              sourceType: ev.source,
              sourceRecordId: ev.sourceRecordId ?? null,
            })),
          })),
          customSkills: input.customSkills.map((s) => s.rawName),
          languages: input.languages.map((l) => ({ language: l.language, level: l.level, rawLevel: null })),
          certifications: input.certifications.map((c) => ({
            name: c.name,
            issuer: c.issuer ?? null,
            year: c.year ?? null,
            issueMonth: c.issueMonth ?? null,
            expirationYear: c.expirationYear ?? null,
            expirationMonth: c.expirationMonth ?? null,
            doesNotExpire: c.doesNotExpire ?? false,
            credentialId: c.credentialId?.trim() || null,
            credentialUrl: c.credentialUrl?.trim() || null,
          })),
        },
        tx,
      );

      await candidateDraftRepository.markConfirmed(draft.id, tx);
      return profile;
    });

    return toResponse(created);
  },

  async submitPreferenceSurvey(input: CandidatePreferenceSurveyValidated): Promise<CandidatePreferenceSurveyResponse> {
    const profile = await candidateProfileRepository.findById(input.profileId);
    if (!profile) {
      throw new AppError("PROFILE_NOT_FOUND", "This candidate profile does not exist.");
    }

    const preferences = [
      ...input.contractTypes.map((value) => ({ type: "CONTRACT_TYPE" as const, value })),
      ...input.workModes.map((value) => ({ type: "WORK_MODE" as const, value })),
      ...input.mobilityPreferences.map((value) => ({ type: "MOBILITY" as const, value })),
      ...input.preferredCountries.map((value) => ({ type: "PREFERRED_COUNTRY" as const, value })),
      ...input.goals.map((value) => ({ type: "GOAL" as const, value })),
    ];

    const updated = await candidateProfileRepository.replacePreferences(input.profileId, preferences);
    return toSurveyResponse(updated);
  },

  async getById(profileId: string): Promise<CandidateProfileResponse> {
    const profile = await candidateProfileRepository.findById(profileId);
    if (!profile) {
      throw new AppError("PROFILE_NOT_FOUND", "This candidate profile does not exist.");
    }
    return toResponse(profile);
  },
};
