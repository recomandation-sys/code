function matchTone(pct: number) {
  if (pct >= 80) return { stroke: "#16c79a", text: "text-accent-600" };
  if (pct >= 50) return { stroke: "#f59e0b", text: "text-warn-500" };
  return { stroke: "#ef4444", text: "text-danger-500" };
}

export function MatchRing({ percent, size = 64 }: { percent: number; size?: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(percent)));
  const tone = matchTone(pct);
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;

  return (
    <div className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={tone.stroke}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-500"
        />
      </svg>
      <span className={`absolute text-sm font-semibold ${tone.text}`}>{pct}%</span>
      <span className="sr-only">Match score {pct} percent</span>
    </div>
  );
}
