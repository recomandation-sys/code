-- Align relational profile with the onboarding wizard fields.
-- Also catches up columns/enums that were in schema.prisma but missing from init.

-- PreferenceType: MOBILITY / PREFERRED_COUNTRY may already exist if applied manually.
ALTER TYPE "PreferenceType" ADD VALUE IF NOT EXISTS 'MOBILITY';
ALTER TYPE "PreferenceType" ADD VALUE IF NOT EXISTS 'PREFERRED_COUNTRY';
ALTER TYPE "PreferenceType" ADD VALUE IF NOT EXISTS 'GOAL';

ALTER TYPE "SkillEvidenceSource" ADD VALUE IF NOT EXISTS 'EDUCATION';

ALTER TABLE "candidate_profiles"
  ADD COLUMN IF NOT EXISTS "phone" TEXT,
  ADD COLUMN IF NOT EXISTS "phone_code" TEXT,
  ADD COLUMN IF NOT EXISTS "country" TEXT,
  ADD COLUMN IF NOT EXISTS "governorate" TEXT,
  ADD COLUMN IF NOT EXISTS "first_name" TEXT,
  ADD COLUMN IF NOT EXISTS "last_name" TEXT,
  ADD COLUMN IF NOT EXISTS "gender" TEXT,
  ADD COLUMN IF NOT EXISTS "date_of_birth" DATE,
  ADD COLUMN IF NOT EXISTS "preferences_completed_at" TIMESTAMP(3);

ALTER TABLE "candidate_experiences"
  ADD COLUMN IF NOT EXISTS "company" TEXT,
  ADD COLUMN IF NOT EXISTS "description" TEXT;

ALTER TABLE "candidate_certifications"
  ADD COLUMN IF NOT EXISTS "issue_month" INTEGER,
  ADD COLUMN IF NOT EXISTS "expiration_year" INTEGER,
  ADD COLUMN IF NOT EXISTS "expiration_month" INTEGER,
  ADD COLUMN IF NOT EXISTS "does_not_expire" BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS "credential_id" TEXT,
  ADD COLUMN IF NOT EXISTS "credential_url" TEXT;

CREATE TABLE IF NOT EXISTS "candidate_educations" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "degree" TEXT NOT NULL,
    "institution" TEXT NOT NULL,
    "field" TEXT NOT NULL,
    "start_year" INTEGER NOT NULL,
    "start_month" INTEGER,
    "end_year" INTEGER,
    "end_month" INTEGER,
    "is_current" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "candidate_educations_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "candidate_educations_candidate_profile_id_idx"
  ON "candidate_educations"("candidate_profile_id");

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'candidate_educations_candidate_profile_id_fkey'
  ) THEN
    ALTER TABLE "candidate_educations"
      ADD CONSTRAINT "candidate_educations_candidate_profile_id_fkey"
      FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id")
      ON DELETE CASCADE ON UPDATE CASCADE;
  END IF;
END $$;
