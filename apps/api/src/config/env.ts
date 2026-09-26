/**
 * Centralized, validated environment configuration (section 75).
 * Every other module reads config from here instead of `process.env`
 * directly, so a missing/invalid variable fails fast at startup.
 */
import "dotenv/config";
import { z } from "zod";

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  PORT: z.coerce.number().int().positive().default(3000),
  WEB_ORIGIN: z.string().url().default("http://localhost:5173"),

  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),

  CV_PARSER_BASE_URL: z.string().url().default("http://localhost:8000"),
  CV_PARSER_TIMEOUT_MS: z.coerce.number().int().positive().default(15000),

  CV_MAX_FILE_SIZE_MB: z.coerce.number().int().positive().default(10),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  // eslint-disable-next-line no-console
  console.error("Invalid environment configuration:", parsed.error.flatten().fieldErrors);
  throw new Error("Invalid environment configuration. Check your .env file against .env.example.");
}

export const env = {
  ...parsed.data,
  CV_MAX_FILE_SIZE_BYTES: parsed.data.CV_MAX_FILE_SIZE_MB * 1024 * 1024,
  isProduction: parsed.data.NODE_ENV === "production",
  isTest: parsed.data.NODE_ENV === "test",
};
