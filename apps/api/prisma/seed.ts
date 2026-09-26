/**
 * Seeds the local canonical `Skill` table (section 43) from the same
 * offline IT-skill lexicon the Python parser matches against
 * (cv_parser/resources/skills/it_lexicon.json), so:
 * - the skill autocomplete endpoint (section 63) has real data on day one
 * - parser-known skills always resolve to a stable Skill.id at draft time
 *
 * Run with: npm run prisma:seed --workspace apps/api
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

interface LexiconEntry {
  id: string;
  canonical_name: string;
  category: string;
}

async function main(): Promise<void> {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const lexiconPath = path.resolve(here, "../../../cv_parser/resources/skills/it_lexicon.json");
  const raw = readFileSync(lexiconPath, "utf-8");
  const entries: LexiconEntry[] = JSON.parse(raw);

  // eslint-disable-next-line no-console
  console.log(`Seeding ${entries.length} canonical skills from ${lexiconPath}`);

  for (const entry of entries) {
    await prisma.skill.upsert({
      where: { id: entry.id },
      update: { canonicalName: entry.canonical_name, category: entry.category },
      create: { id: entry.id, canonicalName: entry.canonical_name, category: entry.category },
    });
  }

  // eslint-disable-next-line no-console
  console.log("Skill taxonomy seed complete.");
}

main()
  .catch((err) => {
    // eslint-disable-next-line no-console
    console.error(err);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
