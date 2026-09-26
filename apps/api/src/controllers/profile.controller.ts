import type { Request, Response } from "express";

import { AppError } from "../errors/app-error.js";
import { profileService } from "../services/profile.service.js";
import type { CandidateProfileInputValidated } from "../schemas/candidate-profile.schema.js";
import type { CandidatePreferenceSurveyValidated } from "../schemas/candidate-preferences-survey.schema.js";

export const profileController = {
  async confirm(req: Request<unknown, unknown, CandidateProfileInputValidated>, res: Response): Promise<void> {
    const profile = await profileService.confirm(req.body);
    res.status(200).json({ data: { profile } });
  },

  async submitPreferenceSurvey(
    req: Request<unknown, unknown, CandidatePreferenceSurveyValidated>,
    res: Response,
  ): Promise<void> {
    const survey = await profileService.submitPreferenceSurvey(req.body);
    res.status(200).json({ data: { survey } });
  },

  async getProfile(req: Request, res: Response): Promise<void> {
    // No authentication in this first module (section 73): the frontend
    // keeps the profileId it received from the confirm response and passes
    // it back here. This bridges section 32's id-less route until real
    // per-user sessions exist.
    const profileId = typeof req.query.profileId === "string" ? req.query.profileId : undefined;
    if (!profileId) {
      throw new AppError("VALIDATION_ERROR", "A profileId query parameter is required.");
    }
    const profile = await profileService.getById(profileId);
    res.status(200).json({ data: { profile } });
  },
};
