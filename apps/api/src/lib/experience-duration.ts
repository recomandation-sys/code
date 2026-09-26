/**
 * Server-side recomputation of experience totals (section 22 / section 50).
 * The client-shown aggregate is informational only — this is the
 * authoritative calculation run during confirmation.
 *
 * For each experience type, overlapping records must not double-count
 * months, so intervals are merged before summing (same "union of intervals"
 * approach used by the Python parser).
 */
import type { ExperienceType } from "@job-recommender/contracts";

export interface ExperienceInterval {
  type: ExperienceType;
  startYear: number;
  startMonth: number | null;
  endYear: number | null;
  endMonth: number | null;
  isCurrent: boolean;
}

function toAbsoluteMonth(year: number, month: number | null, fallbackMonth: number): number {
  return year * 12 + ((month ?? fallbackMonth) - 1);
}

function nowAbsoluteMonth(): number {
  const now = new Date();
  return now.getFullYear() * 12 + now.getMonth();
}

function mergeAndSum(intervals: Array<[number, number]>): number {
  if (intervals.length === 0) return 0;
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  let totalMonths = 0;
  let [curStart, curEnd] = sorted[0]!;

  for (let i = 1; i < sorted.length; i += 1) {
    const [start, end] = sorted[i]!;
    if (start <= curEnd + 1) {
      curEnd = Math.max(curEnd, end);
    } else {
      totalMonths += curEnd - curStart + 1;
      [curStart, curEnd] = [start, end];
    }
  }
  totalMonths += curEnd - curStart + 1;
  return totalMonths;
}

export interface ExperienceTotals {
  professionalMonths: number;
  internshipMonths: number;
  alternanceMonths: number;
  freelanceMonths: number;
}

export function computeExperienceTotals(records: ExperienceInterval[]): ExperienceTotals {
  const byType = new Map<ExperienceType, Array<[number, number]>>();

  for (const record of records) {
    const startAbs = toAbsoluteMonth(record.startYear, record.startMonth, 1);
    const endAbs = record.isCurrent
      ? nowAbsoluteMonth()
      : toAbsoluteMonth(record.endYear ?? record.startYear, record.endMonth, 12);
    if (endAbs < startAbs) continue;

    const bucket = byType.get(record.type) ?? [];
    bucket.push([startAbs, endAbs]);
    byType.set(record.type, bucket);
  }

  return {
    professionalMonths: mergeAndSum(byType.get("PROFESSIONAL") ?? []),
    internshipMonths: mergeAndSum(byType.get("INTERNSHIP") ?? []),
    alternanceMonths: mergeAndSum(byType.get("ALTERNANCE") ?? []),
    freelanceMonths: mergeAndSum(byType.get("FREELANCE") ?? []),
  };
}
