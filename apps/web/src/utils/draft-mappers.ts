import type { CandidateDraft, CandidateProfileInput } from "@job-recommender/contracts";

import type { ReviewFormValues } from "../schemas/review-form.schema.js";

export function draftToFormValues(draft: CandidateDraft): ReviewFormValues {
  return {
    identity: {
      fullName: draft.identity.fullName.value,
      email: draft.identity.email.value,
      phone: draft.identity.phone.value,
      country: draft.identity.country.value,
    },
    positions: draft.target.positions.map((p) => p.value),
    experience: draft.experience.records.map((r) => ({
      id: r.id,
      type: r.type,
      title: r.title,
      // The parser may not have found a start year at all; the form always
      // needs a concrete value to edit, so an unresolved date defaults to
      // the current year rather than being silently dropped.
      startYear: r.startYear ?? new Date().getFullYear(),
      startMonth: r.startMonth,
      endYear: r.endYear,
      endMonth: r.endMonth,
      isCurrent: r.isCurrent,
      technologies: r.technologies,
    })),
    skills: draft.skills.detected.map((s) => ({ id: s.id, name: s.name })),
    customSkills: [],
    uncertainSkills: draft.skills.uncertain.map((s) => ({ id: s.id, rawName: s.rawName })),
    languages: draft.languages,
    certifications: draft.certifications,
  };
}

export function formValuesToProfileInput(
  values: ReviewFormValues,
  draftId: string,
  draft: CandidateDraft,
): CandidateProfileInput {
  const evidenceBySkillId = new Map(
    draft.skills.detected.map((skill) => [
      skill.id,
      skill.evidence.map((ev) => ({
        source: ev.source,
        label: ev.label,
        sourceRecordId: ev.sourceRecordId,
      })),
    ]),
  );

  return {
    draftId,
    identity: values.identity,
    target: {
      positions: values.positions,
    },
    experience: {
      records: values.experience.map((e) => ({
        type: e.type,
        title: e.title,
        startYear: e.startYear,
        startMonth: e.startMonth,
        endYear: e.isCurrent ? null : e.endYear,
        endMonth: e.isCurrent ? null : e.endMonth,
        isCurrent: e.isCurrent,
      })),
    },
    skills: values.skills.map((s) => ({
      skillId: s.id,
      evidence: evidenceBySkillId.get(s.id) ?? [],
    })),
    customSkills: values.customSkills.map((rawName) => ({ rawName })),
    languages: values.languages.map((l) => ({ language: l.language, level: l.level })),
    certifications: values.certifications.map((c) => ({ name: c.name, issuer: c.issuer, year: c.year })),
  };
}
