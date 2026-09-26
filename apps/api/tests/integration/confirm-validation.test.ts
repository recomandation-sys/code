import request from "supertest";
import { describe, expect, it } from "vitest";

import { createApp } from "../../src/app.js";

const app = createApp();

describe("POST /api/v1/candidate-profiles/confirm validation", () => {
  it("rejects a payload with no desired positions before touching the database", async () => {
    const res = await request(app)
      .post("/api/v1/candidate-profiles/confirm")
      .send({
        draftId: "5f2c1e8a-6b1a-4e2a-9c3d-1a2b3c4d5e6f",
        identity: { fullName: "Jane Doe", email: "jane@example.com" },
        target: { positions: [] },
        experience: { records: [] },
        skills: [],
        customSkills: [],
        languages: [],
        certifications: [],
      });

    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("VALIDATION_ERROR");
  });

  it("rejects a malformed draftId", async () => {
    const res = await request(app)
      .post("/api/v1/candidate-profiles/confirm")
      .send({
        draftId: "not-a-uuid",
        identity: { fullName: "Jane Doe", email: "jane@example.com" },
        target: { positions: ["Backend Developer"] },
        experience: { records: [] },
        skills: [],
        customSkills: [],
        languages: [],
        certifications: [],
      });

    expect(res.status).toBe(400);
  });
});

describe("GET /api/v1/candidate-profile", () => {
  it("requires a profileId query parameter", async () => {
    const res = await request(app).get("/api/v1/candidate-profile");
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("VALIDATION_ERROR");
  });
});
