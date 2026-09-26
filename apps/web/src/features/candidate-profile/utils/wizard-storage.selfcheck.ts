/**
 * ponytail: runnable check for wizard preference ↔ API mobility mapping
 * Run: npx tsx src/features/candidate-profile/utils/wizard-storage.selfcheck.ts
 * (or: node --experimental-strip-types after build)
 */
import assert from "node:assert/strict";

type Where = "LOCAL" | "FOREIGN" | "BOTH";

function toMobility(where: Where): string[] {
  if (where === "LOCAL") return ["LOCAL"];
  if (where === "FOREIGN") return ["FOREIGN"];
  return ["LOCAL", "FOREIGN"];
}

assert.deepEqual(toMobility("LOCAL"), ["LOCAL"]);
assert.deepEqual(toMobility("FOREIGN"), ["FOREIGN"]);
assert.deepEqual(toMobility("BOTH"), ["LOCAL", "FOREIGN"]);
console.log("wizard preference mobility mapping: ok");
