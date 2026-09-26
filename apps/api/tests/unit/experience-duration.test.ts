import { describe, expect, it } from "vitest";

import { computeExperienceTotals } from "../../src/lib/experience-duration.js";

describe("computeExperienceTotals", () => {
  it("sums non-overlapping records of the same type", () => {
    const totals = computeExperienceTotals([
      { type: "PROFESSIONAL", startYear: 2020, startMonth: 1, endYear: 2020, endMonth: 6, isCurrent: false },
      { type: "PROFESSIONAL", startYear: 2021, startMonth: 1, endYear: 2021, endMonth: 3, isCurrent: false },
    ]);

    expect(totals.professionalMonths).toBe(6 + 3);
  });

  it("merges overlapping records instead of double-counting", () => {
    const totals = computeExperienceTotals([
      { type: "PROFESSIONAL", startYear: 2020, startMonth: 1, endYear: 2020, endMonth: 12, isCurrent: false },
      { type: "PROFESSIONAL", startYear: 2020, startMonth: 6, endYear: 2021, endMonth: 3, isCurrent: false },
    ]);

    // Union of Jan 2020 -> Mar 2021 = 15 months, not 12 + 10.
    expect(totals.professionalMonths).toBe(15);
  });

  it("treats a current record as running through today", () => {
    const now = new Date();
    const totals = computeExperienceTotals([
      { type: "FREELANCE", startYear: now.getFullYear(), startMonth: 1, endYear: null, endMonth: null, isCurrent: true },
    ]);

    expect(totals.freelanceMonths).toBe(now.getMonth() + 1);
  });

  it("keeps totals for different experience types independent", () => {
    const totals = computeExperienceTotals([
      { type: "PROFESSIONAL", startYear: 2020, startMonth: 1, endYear: 2020, endMonth: 12, isCurrent: false },
      { type: "INTERNSHIP", startYear: 2019, startMonth: 6, endYear: 2019, endMonth: 8, isCurrent: false },
    ]);

    expect(totals.professionalMonths).toBe(12);
    expect(totals.internshipMonths).toBe(3);
    expect(totals.alternanceMonths).toBe(0);
  });
});
