import type { ParseQualityStatus } from "@job-recommender/contracts";

const COPY: Record<ParseQualityStatus, { title: string; className: string }> = {
  GOOD: {
    title: "We extracted your profile. Please review it before continuing.",
    className: "bg-emerald-50 text-emerald-800 border-emerald-200",
  },
  FAIR: {
    title: "Some information may need your attention. Please review the highlighted fields.",
    className: "bg-amber-50 text-amber-800 border-amber-200",
  },
  POOR: {
    title: "We could only partially read this CV. Please review and complete the missing information.",
    className: "bg-red-50 text-red-800 border-red-200",
  },
};

interface ParseQualityBannerProps {
  status: ParseQualityStatus;
  warnings: string[];
}

/** Never blocks manual editing regardless of status (section 17). */
export function ParseQualityBanner({ status, warnings }: ParseQualityBannerProps) {
  const copy = COPY[status];
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${copy.className}`} role="status">
      <p className="font-medium">{copy.title}</p>
      {warnings.length > 0 ? (
        <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs opacity-90">
          {warnings.map((warning, i) => (
            <li key={i}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
