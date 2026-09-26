/**
 * Thin HTTP transport to the Python FastAPI parser (section 12). Owns
 * multipart transport, timeout, and status mapping only — no UI
 * transformation logic belongs here (that's the adapter's job).
 */
import { env } from "../config/env.js";
import { AppError } from "../errors/app-error.js";
import { logger } from "../lib/logger.js";
import { type RawParserResponse, parserErrorBodySchema, rawParserResponseSchema } from "../schemas/parser-response.schema.js";

export interface UploadedPdf {
  buffer: Buffer;
  originalName: string;
}

export interface CvParserClient {
  parsePdf(file: UploadedPdf, requestId: string): Promise<RawParserResponse>;
}

class HttpCvParserClient implements CvParserClient {
  async parsePdf(file: UploadedPdf, requestId: string): Promise<RawParserResponse> {
    const form = new FormData();
    // Field name "file" matches app/api/routes.py's `file: UploadFile = File(...)`.
    form.append("file", new Blob([file.buffer], { type: "application/pdf" }), file.originalName);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), env.CV_PARSER_TIMEOUT_MS);

    let response: Response;
    try {
      response = await fetch(new URL("/api/cv/parse", env.CV_PARSER_BASE_URL), {
        method: "POST",
        body: form,
        signal: controller.signal,
        headers: { "X-Request-Id": requestId },
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        throw new AppError("PARSER_TIMEOUT", "The CV analysis service took too long to respond.");
      }
      logger.error({ requestId, err: err instanceof Error ? err.message : err }, "cv-parser unreachable");
      throw new AppError("PARSER_UNAVAILABLE", "We couldn't analyze your CV right now.");
    } finally {
      clearTimeout(timeout);
    }

    if (response.status === 400 || response.status === 422) {
      const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
      const parsedBody = parserErrorBodySchema.safeParse(body?.detail ?? body);
      const message = parsedBody.success ? parsedBody.data.message : "This PDF could not be read.";
      throw new AppError("PDF_UNREADABLE", message);
    }

    if (!response.ok) {
      logger.error({ requestId, status: response.status }, "cv-parser returned an unexpected status");
      throw new AppError("PARSER_UNAVAILABLE", "We couldn't analyze your CV right now.");
    }

    const json = await response.json();
    const result = rawParserResponseSchema.safeParse(json);
    if (!result.success) {
      logger.error({ requestId, issues: result.error.issues }, "cv-parser response failed schema validation");
      throw new AppError("PARSER_RESPONSE_INVALID", "We couldn't process the CV analysis result.");
    }

    return result.data;
  }
}

export const cvParserClient: CvParserClient = new HttpCvParserClient();
