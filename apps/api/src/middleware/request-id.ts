/**
 * One request ID per public request (section 54), echoed back as
 * `X-Request-Id` and forwarded to the Python parser so both services can be
 * correlated in logs without ever logging CV content.
 */
import type { NextFunction, Request, Response } from "express";
import { v4 as uuidv4 } from "uuid";

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      requestId: string;
    }
  }
}

export function requestId(req: Request, res: Response, next: NextFunction): void {
  const incoming = req.header("X-Request-Id");
  const id = incoming && incoming.trim().length > 0 ? incoming : uuidv4();
  req.requestId = id;
  res.setHeader("X-Request-Id", id);
  next();
}
