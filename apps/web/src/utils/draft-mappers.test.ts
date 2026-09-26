import { describe, expect, it } from "vitest";
import type { CandidateDraft } from "@job-recommender/contracts";

import { draftToFormValues, formValuesToProfileInput } from "./draft-mappers.js";

function buildDraft(): CandidateDraft {
  return {
    id: "draft-1",
    status: "PARSED",
    parserVersion: "3.0.0",
    identity: {
      fullName: { value: "Jane Doe", confidence: "HIGH", needsReview: false, parserValue: "Jane Doe" },
      email: { value: "jane@example.com", confidence: "HIGH", needsReview: false, parserValue: "jane@example.com" },
      phone: { value: "+216 27102499", confidence: "HIGH", needsReview: false, parserValue: "+216 27102499" },
      country: { value: "Tunisia", confidence: "HIGH", needsReview: false, parserValue: "Tunisia" },
    },
    target: {
      positions: [{ id: "p1", value: "Backend Developer", confidence: "HIGH" }],
      contractTypes: ["CDI"],
      workModes: ["REMOTE"],
    },
    experience: {
      professionalMonths: 12,
      internshipMonths: 0,
      alternanceMonths: 0,
      freelanceMonths: 0,
      records: [
        {
          id: "e1",
          type: "PROFESSIONAL",
          title: "Backend Developer",
          startYear: 2023,
          startMonth: 1,
          endYear: null,
          endMonth: null,
          isCurrent: true,
          technologies: ["Python"],
          confidence: "HIGH",
        },
      ],
    },
    skills: {
      detected: [{ id: "python", name: "Python", category: "PROGRAMMING_LANGUAGE", evidence: [] }],
      uncertain: [{ id: "u1", rawName: "Sequelize", evidence: [] }],
    },
    languages: [{ id: "l1", language: "English", level: "C1", rawLevel: "C1", confidence: "HIGH" }],
    certifications: [{ id: "c1", name: "AWS Certified Developer", issuer: "AWS", year: 2022 }],
    quality: { status: "GOOD", warnings: [] },
    reviewSummary: { reviewRequired: false, itemCount: 0 },
    parser: { version: "3.0.0" },
  };
}

describe("draftToFormValues", () => {
  it("maps a full draft into editable form values", () => {
    const values = draftToFormValues(buildDraft());
    expect(values.identity.fullName).toBe("Jane Doe");
    expect(values.positions).toEqual(["Backend Developer"]);
    expect(values.experience[0]?.startYear).toBe(2023);
    expect(values.skills).toEqual([{ id: "python", name: "Python" }]);
    expect(values.uncertainSkills).toEqual([{ id: "u1", rawName: "Sequelize" }]);
  });

  it("defaults a missing start year to the current year instead of leaving it null", () => {
    const draft = buildDraft();
    draft.experience.records[0]!.startYear = null;
    const values = draftToFormValues(draft);
    expect(values.experience[0]?.startYear).toBe(new Date().getFullYear());
  });
});

describe("formValuesToProfileInput", () => {
  it("round-trips form values into a confirmation payload", () => {
    const values = draftToFormValues(buildDraft());
    values.customSkills = ["Zustand"];
    const input = formValuesToProfileInput(values, "draft-1", buildDraft());

    expect(input.draftId).toBe("draft-1");
    expect(input.skills).toEqual([{ skillId: "python", evidence: [] }]);
    expect(input.customSkills).toEqual([{ rawName: "Zustand" }]);
    expect(input.target.positions).toEqual(["Backend Developer"]);
  });

  it("clears end date fields for a record marked as current", () => {
    const values = draftToFormValues(buildDraft());
    values.experience[0]!.isCurrent = true;
    values.experience[0]!.endYear = 2024;
    const input = formValuesToProfileInput(values, "draft-1", buildDraft());

    expect(input.experience.records[0]?.endYear).toBeNull();
    expect(input.experience.records[0]?.endMonth).toBeNull();
  });
});
