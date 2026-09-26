import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { adaptParserResponseToDraft } from "../../src/adapters/parser-to-draft.adapter.js";
import { rawParserResponseSchema } from "../../src/schemas/parser-response.schema.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const fixturesDir = path.resolve(here, "../fixtures/parser");

function loadFixture(name: string) {
  const raw = JSON.parse(readFileSync(path.join(fixturesDir, name), "utf-8"));
  return rawParserResponseSchema.parse(raw);
}

describe("adaptParserResponseToDraft", () => {
  it("maps a GOOD-quality parser response without dropping data", () => {
    const raw = loadFixture("v3-good.json");
    const draft = adaptParserResponseToDraft(raw);

    expect(draft.identity.fullName.value).toBe("Jane Doe");
    expect(draft.identity.fullName.needsReview).toBe(false);
    expect(draft.identity.email.needsReview).toBe(false);

    expect(draft.target.positions).toHaveLength(1);
    expect(draft.target.positions[0]?.value).toBe("Backend Developer");
    expect(draft.target.contractTypes).toEqual(["CDI"]);

    expect(draft.experience.records).toHaveLength(1);
    expect(draft.experience.records[0]?.isCurrent).toBe(true);
    expect(draft.experience.records[0]?.endYear).toBeNull();

    expect(draft.skills.detected.map((s) => s.name)).toEqual(["Python", "FastAPI"]);
    expect(draft.skills.uncertain.map((s) => s.rawName)).toEqual(["Sequelize"]);

    expect(draft.languages[0]?.level).toBe("C1");
    expect(draft.certifications[0]?.year).toBe(2022);

    expect(draft.quality.status).toBe("GOOD");
    expect(draft.reviewSummary.reviewRequired).toBe(false);
    expect(draft.reviewSummary.itemCount).toBe(0);
  });

  it("marks missing identity fields as needing review instead of fabricating values", () => {
    const raw = loadFixture("v3-poor.json");
    const draft = adaptParserResponseToDraft(raw);

    expect(draft.identity.fullName.value).toBe("");
    expect(draft.identity.fullName.needsReview).toBe(true);
    expect(draft.identity.email.value).toBe("");
    expect(draft.identity.email.needsReview).toBe(true);

    expect(draft.quality.status).toBe("POOR");
    expect(draft.quality.warnings).toContain("LAYOUT_QUALITY_POOR");
    expect(draft.reviewSummary.reviewRequired).toBe(true);
    expect(draft.reviewSummary.itemCount).toBe(2);
  });

  it("keeps unmapped technologies out of the detected skills list", () => {
    const raw = loadFixture("v3-unknown-skills.json");
    const draft = adaptParserResponseToDraft(raw);

    expect(draft.skills.detected).toHaveLength(0);
    expect(draft.skills.uncertain.map((s) => s.rawName)).toEqual(["Zustand", "Drizzle ORM"]);
    expect(draft.identity.fullName.needsReview).toBe(true); // MEDIUM confidence still needs review
  });
});
