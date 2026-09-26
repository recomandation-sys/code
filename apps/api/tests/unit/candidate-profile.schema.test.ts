import { describe, expect, it } from "vitest";

import { candidateProfileInputSchema } from "../../src/schemas/candidate-profile.schema.js";

function baseInput() {
  return {
    draftId: "5f2c1e8a-6b1a-4e2a-9c3d-1a2b3c4d5e6f",
    identity: { fullName: "Jane Doe", email: "jane@example.com" },
    target: { positions: ["Backend Developer"] },
    experience: { records: [] },
    skills: [],
    customSkills: [],
    languages: [],
    certifications: [],
  };
}

describe("candidateProfileInputSchema", () => {
  it("accepts a minimal valid confirmation payload", () => {
    const result = candidateProfileInputSchema.safeParse(baseInput());
    expect(result.success).toBe(true);
  });

  it("rejects a payload with no desired positions", () => {
    const input = baseInput();
    input.target.positions = [];
    const result = candidateProfileInputSchema.safeParse(input);
    expect(result.success).toBe(false);
  });

  it("deduplicates desired positions case-insensitively", () => {
    const input = baseInput();
    input.target.positions = ["Backend Developer", "backend developer", "Frontend Developer"];
    const result = candidateProfileInputSchema.parse(input);
    expect(result.target.positions).toEqual(["Backend Developer", "Frontend Developer"]);
  });

  it("rejects an experience record whose end date precedes its start date", () => {
    const input = {
      ...baseInput(),
      experience: {
        records: [
          {
            type: "PROFESSIONAL",
            title: "Dev",
            startYear: 2023,
            startMonth: 6,
            endYear: 2022,
            endMonth: 1,
            isCurrent: false,
          },
        ],
      },
    };
    const result = candidateProfileInputSchema.safeParse(input);
    expect(result.success).toBe(false);
  });

  it("rejects a current record that also has an end date", () => {
    const input = {
      ...baseInput(),
      experience: {
        records: [
          {
            type: "PROFESSIONAL",
            title: "Dev",
            startYear: 2023,
            startMonth: 1,
            endYear: 2024,
            endMonth: 1,
            isCurrent: true,
          },
        ],
      },
    };
    const result = candidateProfileInputSchema.safeParse(input);
    expect(result.success).toBe(false);
  });

  it("deduplicates skills by skillId", () => {
    const input = { ...baseInput(), skills: [{ skillId: "python" }, { skillId: "python" }, { skillId: "react" }] };
    const result = candidateProfileInputSchema.parse(input);
    expect(result.skills).toEqual([{ skillId: "python" }, { skillId: "react" }]);
  });

  it("rejects an invalid email", () => {
    const input = baseInput();
    input.identity.email = "not-an-email";
    const result = candidateProfileInputSchema.safeParse(input);
    expect(result.success).toBe(false);
  });
});
