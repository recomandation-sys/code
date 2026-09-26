/**
 * Controllers only read the validated request, call a service, and send a
 * response — no business logic lives here (section 31).
 * Express 5 forwards rejected promises to the error middleware automatically,
 * so these handlers don't need a manual try/catch or async wrapper.
 */
import type { Request, Response } from "express";

import { AppError } from "../errors/app-error.js";
import { composeDraftDTO } from "../adapters/compose-draft-dto.js";
import { candidateDraftService } from "../services/candidate-draft.service.js";
import { candidateDraftRepository } from "../repositories/candidate-draft.repository.js";
import { cvParserService } from "../services/cv-parser.service.js";
import type { DraftIdParams } from "../schemas/candidate-draft.schema.js";

export const cvController = {
  async parseCv(req: Request, res: Response): Promise<void> {
    if (!req.file) {
      throw new AppError("INVALID_FILE", "Please select a PDF file to upload.");
    }

    const draft = await cvParserService.parseCv(
      { buffer: req.file.buffer, originalName: req.file.originalname },
      req.requestId,
    );

    res.status(201).json({ data: { draft } });
  },

  /** Manual-entry fallback (section 28) — no file, an empty draft to fill in by hand. */
  async createManualDraft(_req: Request, res: Response): Promise<void> {
    const draft = await cvParserService.createManualDraft();
    res.status(201).json({ data: { draft } });
  },

  async getDraft(req: Request<DraftIdParams>, res: Response): Promise<void> {
    const draft = await candidateDraftService.getReviewableDraft(req.params.draftId);
    res.status(200).json({ data: { draft: composeDraftDTO(draft) } });
  },

  async discardDraft(req: Request<DraftIdParams>, res: Response): Promise<void> {
    await candidateDraftService.getReviewableDraft(req.params.draftId);
    await candidateDraftRepository.markDiscarded(req.params.draftId);
    res.status(204).send();
  },
};
