import { useMemo, useState } from "react";

import { Button } from "../../../components/Button.js";
import { Card } from "../../../components/Card.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { useToast } from "../../../components/Toast.js";
import { fieldClass } from "../../candidate-profile/components/OnboardingChrome.js";
import { MOCK_USERS } from "../../../data/mock.js";

export function AdminUsersPage() {
  const [q, setQ] = useState("");
  const toast = useToast();
  const users = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return MOCK_USERS;
    return MOCK_USERS.filter(
      (u) => u.name.toLowerCase().includes(needle) || u.email.toLowerCase().includes(needle),
    );
  }, [q]);

  return (
    <div>
      <PageHeader title="User management" description="Search and manage candidate accounts." />
      <input
        type="search"
        placeholder="Search name or email…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className={`${fieldClass} mb-4 max-w-md`}
      />

      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Signup</th>
              <th className="px-4 py-3">Profile %</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-slate-100 transition-colors hover:bg-brand-50/40">
                <td className="px-4 py-3 font-medium text-slate-800">{u.name}</td>
                <td className="px-4 py-3 text-slate-500">{u.email}</td>
                <td className="px-4 py-3 text-slate-500">{u.signup}</td>
                <td className="px-4 py-3">{u.completion}%</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      u.status === "Active" ? "bg-accent-50 text-accent-600" : "bg-danger-50 text-danger-600"
                    }`}
                  >
                    {u.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => toast(`View ${u.name}`)}>
                      View
                    </Button>
                    <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => toast(`Suspend ${u.name}`)}>
                      Suspend
                    </Button>
                    <Button variant="danger" className="px-2 py-1 text-xs" onClick={() => toast(`Delete ${u.name}`)}>
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
