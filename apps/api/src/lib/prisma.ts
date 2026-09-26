import { PrismaClient } from "@prisma/client";

import { env } from "../config/env.js";

// Standard "one PrismaClient per process, reused across tsx watch reloads"
// pattern to avoid exhausting Postgres connections in development.
const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: env.isProduction ? ["error", "warn"] : ["error", "warn"],
  });

if (!env.isProduction) {
  globalForPrisma.prisma = prisma;
}
