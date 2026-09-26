/**
 * Canonical skill taxonomy access (section 43, section 69). This is the
 * ONLY place allowed to write to the global `Skill` table, and it only ever
 * does so for names the parser itself already vouches for as canonical
 * (its `known` list, sourced from the same curated IT lexicon this table is
 * seeded from) — never for `unmapped_technology_candidates` (section 45).
 */
import type { Prisma, Skill } from "@prisma/client";

import { prisma } from "../lib/prisma.js";
import { slugify } from "../lib/slugify.js";

type Db = Prisma.TransactionClient | typeof prisma;

export const skillRepository = {
  async findByCanonicalName(canonicalName: string, db: Db = prisma): Promise<Skill | null> {
    return db.skill.findFirst({
      where: { canonicalName: { equals: canonicalName, mode: "insensitive" } },
    });
  },

  async findManyByIds(ids: string[], db: Db = prisma): Promise<Skill[]> {
    if (ids.length === 0) return [];
    return db.skill.findMany({ where: { id: { in: ids } } });
  },

  async search(query: string, limit = 20, db: Db = prisma): Promise<Skill[]> {
    return db.skill.findMany({
      where: { canonicalName: { contains: query, mode: "insensitive" } },
      orderBy: { canonicalName: "asc" },
      take: limit,
    });
  },

  /** Find a skill by canonical name, or create it from parser-vouched data. */
  async findOrCreateByCanonicalName(
    canonicalName: string,
    category: string | null,
    db: Db = prisma,
  ): Promise<Skill> {
    const existing = await this.findByCanonicalName(canonicalName, db);
    if (existing) return existing;

    const id = slugify(canonicalName) || slugify(`skill-${canonicalName}`);
    return db.skill.upsert({
      where: { id },
      update: {},
      create: { id, canonicalName, category },
    });
  },
};
