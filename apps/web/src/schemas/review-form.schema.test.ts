import { describe, expect, it } from "vitest";

import { reviewFormSchema } from "./review-form.schema.js";

function baseValues() {
  return {
    identity: { fullName: "Jane Doe", email: "jane@example.com", phone: "", country: "" },
    positions: ["Backend Developer"],
    experience: [] as never[],
    skills: [] as never[],
    customSkills: [] as never[],
    uncertainSkills: [] as never[],
    languages: [] as never[],
    certifications: [] as never[],
  };
}

describe("reviewFormSchema", () => {
  it("accepts a minimal valid form", () => {
    expect(reviewFormSchema.safeParse(baseValues()).success).toBe(true);
  });

  it("requires at least one target position", () => {
    const values = { ...baseValues(), positions: [] };
    expect(reviewFormSchema.safeParse(values).success).toBe(false);
  });

  it("requires a valid email", () => {
    const values = { ...baseValues(), identity: { fullName: "Jane Doe", email: "not-an-email" } };
    expect(reviewFormSchema.safeParse(values).success).toBe(false);
  });

  it("rejects an experience record ending before it starts", () => {
    const values = {
      ...baseValues(),
      experience: [
        {
          id: "e1",
          type: "PROFESSIONAL",
          title: "Dev",
          startYear: 2023,
          startMonth: 6,
          endYear: 2022,
          endMonth: 1,
          isCurrent: false,
          technologies: [],
        },
      ],
    };
    expect(reviewFormSchema.safeParse(values).success).toBe(false);
  });
});
