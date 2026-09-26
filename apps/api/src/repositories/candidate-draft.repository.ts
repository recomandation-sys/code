import type { CvParseDraft, Prisma } from "@prisma/client";

import { prisma } from "../lib/prisma.js";

type Db = Prisma.TransactionClient | typeof prisma;

export interface CreateDraftInput {
  parserVersion: string;
  parseQuality: string;
  rawParserResult: Prisma.InputJsonValue;
  uiDraft: Prisma.InputJsonValue;
}

export const candidateDraftRepository = {
  async create(input: CreateDraftInput, db: Db = prisma): Promise<CvParseDraft> {
    return db.cvParseDraft.create({
      data: {
        parserVersion: input.parserVersion,
        parseQuality: input.parseQuality,
        rawParserResult: input.rawParserResult,
        uiDraft: input.uiDraft,
      },
    });
  },

  async findById(id: string, db: Db = prisma): Promise<CvParseDraft | null> {
    return db.cvParseDraft.findUnique({ where: { id } });
  },

  async updateUiDraft(id: string, uiDraft: Prisma.InputJsonValue, db: Db = prisma): Promise<CvParseDraft> {
    return db.cvParseDraft.update({
      where: { id },
      data: { uiDraft, status: "EDITING" },
    });
  },

  async markConfirmed(id: string, db: Db = prisma): Promise<CvParseDraft> {
    return db.cvParseDraft.update({
      where: { id },
      data: { status: "CONFIRMED", confirmedAt: new Date() },
    });
  },

  async markDiscarded(id: string, db: Db = prisma): Promise<CvParseDraft> {
    return db.cvParseDraft.update({
      where: { id },
      data: { status: "DISCARDED" },
    });
  },
};
