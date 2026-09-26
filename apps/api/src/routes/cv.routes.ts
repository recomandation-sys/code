import { Router } from "express";

import { cvController } from "../controllers/cv.controller.js";
import { uploadCv } from "../middleware/upload.js";
import { draftIdParamsSchema } from "../schemas/candidate-draft.schema.js";
import { validateParams } from "../middleware/validate.js";

export const cvRouter = Router();

cvRouter.post("/cv/parse", uploadCv, cvController.parseCv);
cvRouter.post("/cv/manual-draft", cvController.createManualDraft);
cvRouter.get("/candidate-drafts/:draftId", validateParams(draftIdParamsSchema), cvController.getDraft);
cvRouter.delete("/candidate-drafts/:draftId", validateParams(draftIdParamsSchema), cvController.discardDraft);
