-- CreateEnum
CREATE TYPE "DraftStatus" AS ENUM ('PARSED', 'EDITING', 'CONFIRMED', 'EXPIRED', 'DISCARDED');

-- CreateEnum
CREATE TYPE "ExperienceType" AS ENUM ('PROFESSIONAL', 'INTERNSHIP', 'ALTERNANCE', 'FREELANCE', 'UNKNOWN');

-- CreateEnum
CREATE TYPE "ContractType" AS ENUM ('CDI', 'CDD', 'INTERNSHIP', 'ALTERNANCE', 'FREELANCE', 'OTHER');

-- CreateEnum
CREATE TYPE "WorkMode" AS ENUM ('REMOTE', 'HYBRID', 'ONSITE');

-- CreateEnum
CREATE TYPE "PreferenceType" AS ENUM ('CONTRACT_TYPE', 'WORK_MODE');

-- CreateEnum
CREATE TYPE "LanguageLevel" AS ENUM ('A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'NATIVE', 'FLUENT', 'ADVANCED', 'INTERMEDIATE', 'BASIC', 'UNKNOWN');

-- CreateEnum
CREATE TYPE "SkillEvidenceSource" AS ENUM ('SKILLS_SECTION', 'PROFESSIONAL_EXPERIENCE', 'INTERNSHIP', 'ALTERNANCE', 'PROJECT', 'CERTIFICATION', 'PROFILE');

-- CreateTable
CREATE TABLE "cv_parse_drafts" (
    "id" TEXT NOT NULL,
    "status" "DraftStatus" NOT NULL DEFAULT 'PARSED',
    "parser_version" TEXT NOT NULL,
    "parse_quality" TEXT,
    "raw_parser_result" JSONB NOT NULL,
    "ui_draft" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "confirmed_at" TIMESTAMP(3),
    "expires_at" TIMESTAMP(3),

    CONSTRAINT "cv_parse_drafts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_profiles" (
    "id" TEXT NOT NULL,
    "user_id" TEXT,
    "full_name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "source_draft_id" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "candidate_profiles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_desired_positions" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "raw_title" TEXT NOT NULL,
    "normalized_title" TEXT,

    CONSTRAINT "candidate_desired_positions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_preferences" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "type" "PreferenceType" NOT NULL,
    "value" TEXT NOT NULL,

    CONSTRAINT "candidate_preferences_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_experiences" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "type" "ExperienceType" NOT NULL,
    "title" TEXT NOT NULL,
    "start_year" INTEGER NOT NULL,
    "start_month" INTEGER,
    "end_year" INTEGER,
    "end_month" INTEGER,
    "is_current" BOOLEAN NOT NULL DEFAULT false,
    "source_record_id" TEXT,

    CONSTRAINT "candidate_experiences_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "skills" (
    "id" TEXT NOT NULL,
    "canonical_name" TEXT NOT NULL,
    "category" TEXT,
    "esco_uri" TEXT,
    "onet_id" TEXT,

    CONSTRAINT "skills_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_skills" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "skill_id" TEXT NOT NULL,
    "user_confirmed" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "candidate_skills_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_skill_evidence" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "skill_id" TEXT NOT NULL,
    "source_type" "SkillEvidenceSource" NOT NULL,
    "source_record_id" TEXT,
    "parser_draft_id" TEXT,

    CONSTRAINT "candidate_skill_evidence_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_custom_skills" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "raw_name" TEXT NOT NULL,

    CONSTRAINT "candidate_custom_skills_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_languages" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "language" TEXT NOT NULL,
    "level" "LanguageLevel" NOT NULL,
    "raw_level" TEXT,

    CONSTRAINT "candidate_languages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "candidate_certifications" (
    "id" TEXT NOT NULL,
    "candidate_profile_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "issuer" TEXT,
    "year" INTEGER,

    CONSTRAINT "candidate_certifications_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "cv_parse_drafts_status_idx" ON "cv_parse_drafts"("status");

-- CreateIndex
CREATE INDEX "cv_parse_drafts_created_at_idx" ON "cv_parse_drafts"("created_at");

-- CreateIndex
CREATE UNIQUE INDEX "candidate_profiles_source_draft_id_key" ON "candidate_profiles"("source_draft_id");

-- CreateIndex
CREATE INDEX "candidate_profiles_email_idx" ON "candidate_profiles"("email");

-- CreateIndex
CREATE INDEX "candidate_desired_positions_candidate_profile_id_idx" ON "candidate_desired_positions"("candidate_profile_id");

-- CreateIndex
CREATE INDEX "candidate_preferences_candidate_profile_id_idx" ON "candidate_preferences"("candidate_profile_id");

-- CreateIndex
CREATE UNIQUE INDEX "candidate_preferences_candidate_profile_id_type_value_key" ON "candidate_preferences"("candidate_profile_id", "type", "value");

-- CreateIndex
CREATE INDEX "candidate_experiences_candidate_profile_id_idx" ON "candidate_experiences"("candidate_profile_id");

-- CreateIndex
CREATE UNIQUE INDEX "skills_canonical_name_key" ON "skills"("canonical_name");

-- CreateIndex
CREATE INDEX "candidate_skills_candidate_profile_id_idx" ON "candidate_skills"("candidate_profile_id");

-- CreateIndex
CREATE INDEX "candidate_skills_skill_id_idx" ON "candidate_skills"("skill_id");

-- CreateIndex
CREATE UNIQUE INDEX "candidate_skills_candidate_profile_id_skill_id_key" ON "candidate_skills"("candidate_profile_id", "skill_id");

-- CreateIndex
CREATE INDEX "candidate_skill_evidence_candidate_profile_id_idx" ON "candidate_skill_evidence"("candidate_profile_id");

-- CreateIndex
CREATE INDEX "candidate_skill_evidence_skill_id_idx" ON "candidate_skill_evidence"("skill_id");

-- CreateIndex
CREATE INDEX "candidate_custom_skills_candidate_profile_id_idx" ON "candidate_custom_skills"("candidate_profile_id");

-- CreateIndex
CREATE INDEX "candidate_languages_candidate_profile_id_idx" ON "candidate_languages"("candidate_profile_id");

-- CreateIndex
CREATE UNIQUE INDEX "candidate_languages_candidate_profile_id_language_key" ON "candidate_languages"("candidate_profile_id", "language");

-- CreateIndex
CREATE INDEX "candidate_certifications_candidate_profile_id_idx" ON "candidate_certifications"("candidate_profile_id");

-- AddForeignKey
ALTER TABLE "candidate_profiles" ADD CONSTRAINT "candidate_profiles_source_draft_id_fkey" FOREIGN KEY ("source_draft_id") REFERENCES "cv_parse_drafts"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_desired_positions" ADD CONSTRAINT "candidate_desired_positions_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_preferences" ADD CONSTRAINT "candidate_preferences_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_experiences" ADD CONSTRAINT "candidate_experiences_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_skills" ADD CONSTRAINT "candidate_skills_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_skills" ADD CONSTRAINT "candidate_skills_skill_id_fkey" FOREIGN KEY ("skill_id") REFERENCES "skills"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_skill_evidence" ADD CONSTRAINT "candidate_skill_evidence_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_skill_evidence" ADD CONSTRAINT "candidate_skill_evidence_skill_id_fkey" FOREIGN KEY ("skill_id") REFERENCES "skills"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_custom_skills" ADD CONSTRAINT "candidate_custom_skills_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_languages" ADD CONSTRAINT "candidate_languages_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "candidate_certifications" ADD CONSTRAINT "candidate_certifications_candidate_profile_id_fkey" FOREIGN KEY ("candidate_profile_id") REFERENCES "candidate_profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;
