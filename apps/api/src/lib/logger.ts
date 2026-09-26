/**
 * Structured logger (section 55). Only operational fields are ever logged —
 * raw CV text, full parser JSON, and skill evidence sentences must never be
 * passed to `logger.info`/`logger.error` (section 55 / section 10 rule 10).
 */
import pino from "pino";

import { env } from "../config/env.js";

export const logger = pino({
  level: env.isProduction ? "info" : "debug",
  transport: env.isProduction
    ? undefined
    : {
        target: "pino-pretty",
        options: { colorize: true, translateTime: "HH:MM:ss", ignore: "pid,hostname" },
      },
});
