import { Link } from "react-router-dom";

import { Card } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { MOCK_ADMIN_KPIS } from "../../../data/mock.js";

const links = [
  { to: "/admin/scraping", label: "Scraping analytics" },
  { to: "/admin/feedback", label: "Feedback inbox" },
  { to: "/admin/reports", label: "Extraction reports" },
  { to: "/admin/users", label: "User management" },
  { to: "/admin/analytics", label: "Platform analytics" },
];

export function AdminOverviewPage() {
  const kpis = [
    { label: "Jobs scraped this week", value: MOCK_ADMIN_KPIS.jobsScrapedWeek },
    { label: "Active users", value: MOCK_ADMIN_KPIS.activeUsers },
    { label: "Pending reports", value: MOCK_ADMIN_KPIS.pendingReports },
    { label: "New comments", value: MOCK_ADMIN_KPIS.newComments },
  ];

  return (
    <div>
      <PageHeader title="Overview" description="Platform health at a glance." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <Card
            key={k.label}
            className="p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md hover:shadow-brand-600/10"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{k.label}</p>
            <p className="mt-2 text-3xl font-bold text-slate-900">{k.value.toLocaleString()}</p>
          </Card>
        ))}
      </div>

      <Card className="mt-8">
        <h2 className="text-sm font-semibold text-slate-900">Trend (demo)</h2>
        <div className="mt-4 flex h-32 items-end gap-2">
          {[40, 55, 48, 70, 62, 80, 75].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t-md bg-brand-500/90 transition-opacity hover:opacity-100"
              style={{ height: `${h}%` }}
              title={`Day ${i + 1}`}
            />
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">Jobs scraped · last 7 days</p>
      </Card>

      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm font-semibold text-slate-800 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-brand-200 hover:text-brand-700 hover:shadow-md hover:shadow-brand-600/10"
          >
            {l.label} →
          </Link>
        ))}
      </div>
    </div>
  );
}
