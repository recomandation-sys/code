import { Link } from "react-router-dom";

import { Button } from "./Button.js";
import { useToast } from "./Toast.js";
import { WORK_MODE_LABEL, type MockJob } from "../data/mock.js";

const MODE_ICON: Record<MockJob["workMode"], string> = {
  remote: "⌂",
  hybrid: "⇄",
  onsite: "●",
};

export function JobCard({
  job,
  onDismiss,
}: {
  job: MockJob;
  onDismiss?: (id: string) => void;
}) {
  const toast = useToast();

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md hover:shadow-brand-600/10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            to={`/jobs/${job.id}`}
            className="text-lg font-semibold text-slate-900 transition-colors hover:text-brand-600"
          >
            {job.title}
          </Link>
          <p className="mt-0.5 text-sm text-slate-500">
            {job.company} · {job.location}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
            <span aria-hidden="true">{MODE_ICON[job.workMode]}</span>
            {WORK_MODE_LABEL[job.workMode]}
          </span>
          <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">{job.contract}</span>
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-slate-600">{job.summary}</p>

      <ul className="mt-3 flex flex-wrap gap-1.5">
        {job.skills.map((s) => (
          <li key={s} className="rounded-full bg-accent-50 px-2.5 py-0.5 text-xs font-medium text-accent-600">
            {s}
          </li>
        ))}
      </ul>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
        <Button type="button" variant="ghost" className="px-3" onClick={() => toast("Saved to Liked")} aria-label={`Like ${job.title}`}>
          Like
        </Button>
        <Button
          type="button"
          variant="ghost"
          className="px-3 text-danger-600 hover:bg-danger-50"
          onClick={() => {
            toast("Got it — we'll show fewer like this");
            onDismiss?.(job.id);
          }}
          aria-label={`Dislike ${job.title}`}
        >
          Dislike
        </Button>
        <Button type="button" variant="success" className="px-3" onClick={() => toast("Marked as applied")}>
          Apply
        </Button>
        <Button
          type="button"
          variant="secondary"
          className="px-3"
          onClick={async () => {
            const url = `${window.location.origin}/jobs/${job.id}`;
            try {
              await navigator.clipboard.writeText(url);
              toast("Link copied");
            } catch {
              toast(url);
            }
          }}
        >
          Share
        </Button>
      </div>
    </article>
  );
}
