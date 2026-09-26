import { useMemo, useState } from "react";

import { Button } from "../../../components/Button.js";
import { PageHeader } from "../../../components/PageHeader.js";
import { useToast } from "../../../components/Toast.js";
import { MOCK_FEEDBACK } from "../../../data/mock.js";

type Tab = "negative" | "positive";

export function AdminFeedbackPage() {
  const [tab, setTab] = useState<Tab>("negative");
  const toast = useToast();
  const items = useMemo(() => MOCK_FEEDBACK.filter((f) => f.sentiment === tab), [tab]);

  return (
    <div>
      <PageHeader title="Feedback moderation" description="Comments pre-sorted by sentiment." />

      <div className="mb-6 flex gap-2">
        {(
          [
            ["negative", "Negative"],
            ["positive", "Positive"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`cursor-pointer rounded-xl px-4 py-2 text-sm font-medium transition-all duration-200 ${
              tab === id
                ? "bg-brand-600 text-white shadow-sm shadow-brand-600/25"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-brand-50 hover:text-brand-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <ul className="space-y-3">
        {items.map((f) => (
          <li
            key={f.id}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-300 hover:border-brand-200 hover:shadow-md hover:shadow-brand-600/10"
          >
            <p className="text-sm text-slate-800">{f.comment}</p>
            <p className="mt-2 text-xs text-slate-400">
              {f.role} · {f.date} · confidence {(f.confidence * 100).toFixed(0)}%
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {tab === "positive" ? (
                <>
                  <Button variant="success" onClick={() => toast("Published as testimonial")}>
                    Publish as testimonial
                  </Button>
                  <Button variant="ghost" onClick={() => toast("Dismissed")}>
                    Dismiss
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="secondary" onClick={() => toast("Marked resolved")}>
                    Mark resolved
                  </Button>
                  <Button variant="danger" onClick={() => toast("Escalated")}>
                    Escalate
                  </Button>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
