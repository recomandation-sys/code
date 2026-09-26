/**
 * Stable, user-safe error codes (section 53). Every code here maps to a
 * fixed HTTP status; handlers throw `AppError` and the central error
 * middleware (middleware/error-handler.ts) is the only place that turns it
 * into a response body. Never leak stack traces, Prisma exceptions, or
 * filesystem paths to the client.
 */
export type AppErrorCode =
  | "INVALID_FILE"
  | "FILE_TOO_LARGE"
  | "UNSUPPORTED_MEDIA_TYPE"
  | "PDF_UNREADABLE"
  | "PARSER_UNAVAILABLE"
  | "PARSER_TIMEOUT"
  | "PARSER_RESPONSE_INVALID"
  | "DRAFT_NOT_FOUND"
  | "DRAFT_EXPIRED"
  | "DRAFT_DISCARDED"
  | "PROFILE_INVALID"
  | "PROFILE_NOT_FOUND"
  | "VALIDATION_ERROR"
  | "DATABASE_ERROR"
  | "INTERNAL_ERROR"
  | "NOT_FOUND";

const STATUS_BY_CODE: Record<AppErrorCode, number> = {
  INVALID_FILE: 400,
  FILE_TOO_LARGE: 413,
  UNSUPPORTED_MEDIA_TYPE: 415,
  PDF_UNREADABLE: 422,
  PARSER_UNAVAILABLE: 502,
  PARSER_TIMEOUT: 504,
  PARSER_RESPONSE_INVALID: 502,
  DRAFT_NOT_FOUND: 404,
  DRAFT_EXPIRED: 410,
  DRAFT_DISCARDED: 410,
  PROFILE_INVALID: 422,
  PROFILE_NOT_FOUND: 404,
  VALIDATION_ERROR: 400,
  DATABASE_ERROR: 500,
  INTERNAL_ERROR: 500,
  NOT_FOUND: 404,
};

export class AppError extends Error {
  readonly code: AppErrorCode;
  readonly status: number;
  readonly details?: unknown[];

  constructor(code: AppErrorCode, message: string, details?: unknown[]) {
    super(message);
    this.name = "AppError";
    this.code = code;
    this.status = STATUS_BY_CODE[code];
    this.details = details;
  }
}
