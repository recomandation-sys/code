/**
 * These integration tests only exercise request paths that fail validation
 * before ever touching PostgreSQL, so they can run without a live test
 * database (section 80's DB-touching cases are covered by the manual
 * end-to-end smoke test until a dedicated test database is wired up).
 */
import request from "supertest";
import { describe, expect, it } from "vitest";

import { createApp } from "../../src/app.js";

const app = createApp();

describe("POST /api/v1/cv/parse", () => {
  it("rejects a request with no file", async () => {
    const res = await request(app).post("/api/v1/cv/parse");
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("INVALID_FILE");
  });

  it("rejects a non-PDF file", async () => {
    const res = await request(app)
      .post("/api/v1/cv/parse")
      .attach("cv", Buffer.from("not a pdf"), { filename: "resume.txt", contentType: "text/plain" });
    expect(res.status).toBe(415);
    expect(res.body.error.code).toBe("UNSUPPORTED_MEDIA_TYPE");
  });

  it("rejects a file larger than the configured limit", async () => {
    const big = Buffer.alloc(11 * 1024 * 1024, 1);
    const res = await request(app)
      .post("/api/v1/cv/parse")
      .attach("cv", big, { filename: "resume.pdf", contentType: "application/pdf" });
    expect(res.status).toBe(413);
    expect(res.body.error.code).toBe("FILE_TOO_LARGE");
  });
});

describe("GET /api/v1/candidate-drafts/:draftId", () => {
  it("rejects a non-UUID draftId before touching the database", async () => {
    const res = await request(app).get("/api/v1/candidate-drafts/not-a-uuid");
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("VALIDATION_ERROR");
  });
});

describe("unknown routes", () => {
  it("returns a stable 404 envelope", async () => {
    const res = await request(app).get("/api/v1/does-not-exist");
    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe("NOT_FOUND");
    expect(res.body.requestId).toBeDefined();
  });
});

describe("response headers", () => {
  it("always echoes a request id", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.headers["x-request-id"]).toBeDefined();
  });
});
