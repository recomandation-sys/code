import type { IncomingMessage } from "node:http";

import cors from "cors";
import express, { type Express, type Request } from "express";
import { pinoHttp } from "pino-http";

import { env } from "./config/env.js";
import { logger } from "./lib/logger.js";
import { errorHandler, notFoundHandler } from "./middleware/error-handler.js";
import { requestId } from "./middleware/request-id.js";
import { cvRouter } from "./routes/cv.routes.js";
import { profileRouter } from "./routes/profile.routes.js";
import { skillsRouter } from "./routes/skills.routes.js";

export function createApp(): Express {
  const app = express();

  app.disable("x-powered-by");
  app.use(requestId);
  app.use(
    cors({
      origin: env.WEB_ORIGIN,
      methods: ["GET", "POST", "DELETE"],
    }),
  );
  app.use(express.json({ limit: "1mb" }));
  app.use(
    pinoHttp({
      logger,
      genReqId: (req: IncomingMessage) => (req as Request).requestId,
      // Section 55: never log full request/response bodies (CV text, parser JSON).
      serializers: {
        req: (req: { method: string; url: string }) => ({ method: req.method, url: req.url }),
        res: (res: { statusCode: number }) => ({ statusCode: res.statusCode }),
      },
    }),
  );

  app.get("/health", (_req, res) => {
    res.status(200).json({ status: "ok" });
  });

  const v1 = express.Router();
  v1.use(cvRouter);
  v1.use(profileRouter);
  v1.use(skillsRouter);
  app.use("/api/v1", v1);

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
