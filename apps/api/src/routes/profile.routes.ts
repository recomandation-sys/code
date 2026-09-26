import { Router } from "express";

import { profileController } from "../controllers/profile.controller.js";
import { candidateProfileInputSchema } from "../schemas/candidate-profile.schema.js";
import { candidatePreferenceSurveySchema } from "../schemas/candidate-preferences-survey.schema.js";
import { validateBody } from "../middleware/validate.js";

export const profileRouter = Router();

profileRouter.post(
  "/candidate-profiles/confirm",
  validateBody(candidateProfileInputSchema),
  profileController.confirm,
);
profileRouter.post(
  "/candidate-profiles/preferences",
  validateBody(candidatePreferenceSurveySchema),
  profileController.submitPreferenceSurvey,
);
profileRouter.get("/candidate-profile", profileController.getProfile);
