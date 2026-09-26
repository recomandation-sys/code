import { Card } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { MOCK_SCRAPE_SOURCES } from "../../../data/mock.js";

export function AdminScrapingPage() {
  return (
    <div>
      <PageHeader title="Scraping analytics" description="Pipeline coverage and source health." />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Jobs per week</h2>
          <div className="mt-4 flex h-40 items-end gap-3">
            {[1200, 1400, 1100, 1600, 1842].map((v, i) => (
              <div key={i} className="flex flex-1 flex-col items-center gap-2">
                <div className="w-full rounded-t-md bg-accent-500" style={{ height: `${(v / 2000) * 100}%` }} />
                <span className="text-xs text-slate-400">W{i + 1}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Source breakdown</h2>
          <ul className="mt-4 space-y-3">
            {MOCK_SCRAPE_SOURCES.map((s) => (
              <li key={s.source}>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-700">{s.source}</span>
                  <span className="font-medium text-slate-900">{s.jobsAdded}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-brand-600" style={{ width: `${(s.jobsAdded / 700) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="mt-6 overflow-x-auto p-0">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Last run</th>
              <th className="px-4 py-3">Jobs added</th>
              <th className="px-4 py-3">Errors</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_SCRAPE_SOURCES.map((s) => (
              <tr key={s.source} className="border-b border-slate-100 transition-colors hover:bg-brand-50/40">
                <td className="px-4 py-3 font-medium text-slate-800">{s.source}</td>
                <td className="px-4 py-3 text-slate-500">{s.lastRun}</td>
                <td className="px-4 py-3">{s.jobsAdded}</td>
                <td className={`px-4 py-3 ${s.errors ? "text-danger-600" : "text-accent-600"}`}>{s.errors}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
