import { Card } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";

const FUNNEL = [
  { label: "Signups", value: 2400 },
  { label: "CV upload", value: 1910 },
  { label: "Profile complete", value: 1520 },
  { label: "Active (7d)", value: 980 },
] as const;

const FUNNEL_BASE = FUNNEL[0].value;

export function AdminAnalyticsPage() {
  return (
    <div>
      <PageHeader title="Platform analytics" description="Growth and engagement over time." />

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Active jobs available", value: "8,420" },
          { label: "Likes / week", value: "6,110" },
          { label: "Applies / week", value: "1,840" },
        ].map((k) => (
          <Card
            key={k.label}
            className="p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md hover:shadow-brand-600/10"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{k.label}</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{k.value}</p>
          </Card>
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">User growth</h2>
          <div className="mt-4 flex h-40 items-end gap-2">
            {[30, 35, 42, 50, 58, 70, 85].map((h, i) => (
              <div key={i} className="flex-1 rounded-t-md bg-brand-600" style={{ height: `${h}%` }} />
            ))}
          </div>
        </Card>
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Signup → active funnel</h2>
          <ul className="mt-4 space-y-3">
            {FUNNEL.map((step, i) => (
              <li key={step.label}>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">
                    {i + 1}. {step.label}
                  </span>
                  <span className="font-medium">{step.value.toLocaleString()}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-accent-500"
                    style={{ width: `${(step.value / FUNNEL_BASE) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Top in-demand skills</h2>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-600">
            {["SQL", "Python", "React", "AWS", "dbt"].map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </Card>
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Top locations</h2>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-600">
            {["Paris", "Remote EU", "Lyon", "Casablanca", "Berlin"].map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}
