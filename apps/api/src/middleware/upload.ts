/**
 * Multer upload middleware (section 51). Uses in-memory storage — the PDF
 * buffer is forwarded straight to the Python parser and discarded, so there
 * is never a file on disk, never a user-controlled filesystem path, and
 * nothing to clean up in a `finally`.
 */
import multer, { type FileFilterCallback } from "multer";
import type { Request } from "express";

import { env } from "../config/env.js";
import { AppError } from "../errors/app-error.js";

function pdfFileFilter(_req: Request, file: Express.Multer.File, callback: FileFilterCallback): void {
  const isPdfMime = file.mimetype === "application/pdf";
  const hasPdfExtension = file.originalname.toLowerCase().endsWith(".pdf");

  if (!isPdfMime || !hasPdfExtension) {
    callback(new AppError("UNSUPPORTED_MEDIA_TYPE", "Only PDF files are accepted."));
    return;
  }
  callback(null, true);
}

export const uploadCv = multer({
  storage: multer.memoryStorage(),
  limits: {
    files: 1,
    fileSize: env.CV_MAX_FILE_SIZE_BYTES,
  },
  fileFilter: pdfFileFilter,
}).single("cv");
