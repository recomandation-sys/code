import { useState } from "react";

import { Button } from "../../../components/Button.js";
import { Card } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { useToast } from "../../../components/Toast.js";
import { MOCK_REPORTS } from "../../../data/mock.js";

type Status = "New" | "In Review" | "Fixed";

export function AdminReportsPage() {
  const toast = useToast();
  const [selected, setSelected] = useState(MOCK_REPORTS[0]?.id ?? null);
  const [statuses, setStatuses] = useState<Record<string, Status>>(
    Object.fromEntries(MOCK_REPORTS.map((r) => [r.id, r.status])),
  );

  const report = MOCK_REPORTS.find((r) => r.id === selected);

  function advance(id: string) {
    setStatuses((prev) => {
      const cur = prev[id];
      const next: Status = cur === "New" ? "In Review" : cur === "In Review" ? "Fixed" : "Fixed";
      toast(`Status → ${next}`);
      return { ...prev, [id]: next };
    });
  }

  return (
    <div>
      <PageHeader title="Extraction error reports" description="User-flagged mis-extractions listings." />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Job</th>
                <th className="px-4 py-3">Field</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_REPORTS.map((r) => (
                <tr
                  key={r.id}
                  className={`cursor-pointer border-b border-slate-100 transition-colors hover:bg-brand-50/50 ${
                    selected === r.id ? "bg-brand-50" : ""
                  }`}
                  onClick={() => setSelected(r.id)}
                >
                  <td className="px-4 py-3 font-medium text-slate-800">{r.job}</td>
                  <td className="px-4 py-3 text-slate-500">{r.field}</td>
                  <td className="px-4 py-3">{statuses[r.id]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {report ? (
          <Card>
            <h2 className="font-semibold text-slate-900">{report.job}</h2>
            <p className="mt-1 text-sm text-slate-500">
              Field: {report.field} · {report.date}
            </p>
            <p className="mt-4 rounded-xl border border-warn-50 bg-warn-50 p-3 text-sm text-slate-700">{report.note}</p>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Scraped text</p>
                <p className="mt-2 text-sm text-slate-600">
                  …requirements include advanced SQL and Python for warehouse analytics. Contract: CDI. Location: Paris
                  hybrid…
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Extracted fields</p>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  <li>Skills: Excel, SQL, Python</li>
                  <li>Contract: CDD</li>
                  <li>Location: Remote</li>
                </ul>
              </div>
            </div>
            <Button className="mt-6 font-semibold" onClick={() => advance(report.id)} disabled={statuses[report.id] === "Fixed"}>
              {statuses[report.id] === "Fixed" ? "Fixed" : "Advance status"}
            </Button>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
