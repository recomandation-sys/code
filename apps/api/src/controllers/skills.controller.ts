/**
 * Skill autocomplete for profile editing only (section 63) — has nothing to
 * do with job recommendation.
 */
import type { Request, Response } from "express";

import { skillRepository } from "../repositories/skill.repository.js";

export const skillsController = {
  async search(req: Request, res: Response): Promise<void> {
    const query = typeof req.query.query === "string" ? req.query.query.trim() : "";
    const skills = query.length === 0 ? [] : await skillRepository.search(query);
    res.status(200).json({
      data: skills.map((s) => ({ id: s.id, name: s.canonicalName, category: s.category })),
    });
  },
};
