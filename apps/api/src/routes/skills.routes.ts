import { Router } from "express";

import { skillsController } from "../controllers/skills.controller.js";

export const skillsRouter = Router();

skillsRouter.get("/skills", skillsController.search);
