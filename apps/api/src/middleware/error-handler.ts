/**
 * Central Express error middleware (section 53). This is the single place
 * that turns any thrown error into the API error envelope (section 36) —
 * routes/controllers/services only ever `throw`.
 */
import type { NextFunction, Request, Response } from "express";
import { MulterError } from "multer";
import { ZodError } from "zod";

import { AppError } from "../errors/app-error.js";
import { logger } from "../lib/logger.js";

function zodToAppError(err: ZodError): AppError {
  return new AppError("VALIDATION_ERROR", "The request contains invalid data.", err.issues);
}

function multerToAppError(err: MulterError): AppError {
  if (err.code === "LIMIT_FILE_SIZE") {
    return new AppError("FILE_TOO_LARGE", "The uploaded file exceeds the maximum allowed size.");
  }
  return new AppError("INVALID_FILE", "The uploaded file could not be processed.");
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function errorHandler(err: unknown, req: Request, res: Response, _next: NextFunction): void {
  let appError: AppError;

  if (err instanceof AppError) {
    appError = err;
  } else if (err instanceof ZodError) {
    appError = zodToAppError(err);
  } else if (err instanceof MulterError) {
    appError = multerToAppError(err);
  } else {
    appError = new AppError("INTERNAL_ERROR", "Something went wrong. Please try again.");
  }

  const logPayload = {
    requestId: req.requestId,
    route: req.originalUrl,
    httpStatus: appError.status,
    code: appError.code,
  };

  if (appError.status >= 500) {
    logger.error({ ...logPayload, err: err instanceof Error ? err.message : err }, "request failed");
  } else {
    logger.warn(logPayload, "request rejected");
  }

  res.status(appError.status).json({
    error: {
      code: appError.code,
      message: appError.message,
      details: appError.details ?? [],
    },
    requestId: req.requestId,
  });
}

export function notFoundHandler(req: Request, res: Response): void {
  res.status(404).json({
    error: { code: "NOT_FOUND", message: "The requested resource does not exist.", details: [] },
    requestId: req.requestId,
  });
}
