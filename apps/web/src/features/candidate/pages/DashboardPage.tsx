import { Link } from "react-router-dom";

const doors = [
  {
    to: "/jobs",
    title: "Job recommendations",
    body: "Roles matched to your CV skills and preferences.",
    accent: "from-brand-500 to-brand-700",
    chip: "bg-brand-50 text-brand-700",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M4 7h16v12H4V7zm3-3h10v3H7V4z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    to: "/positions",
    title: "Suitable positions",
    body: "Job titles that fit your experience — with clear match reasons.",
    accent: "from-accent-500 to-accent-600",
    chip: "bg-accent-50 text-accent-600",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.6" />
        <path d="M12 8v4l3 2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: "/skills-gap",
    title: "Skills gap",
    body: "What to learn next based on roles you want.",
    accent: "from-warn-500 to-[#f97316]",
    chip: "bg-warn-50 text-warn-500",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M4 19V5m0 14h16M8 15l3-4 3 2 4-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
] as const;

const nextSteps = [
  {
    to: "/onboarding/upload-cv",
    title: "Upload your CV",
    body: "Parse skills and experience into your JOBLIK profile.",
  },
  {
    to: "/settings",
    title: "Complete preferences",
    body: "Work mode, contracts, and goals — so matches stay relevant.",
  },
  {
    to: "/feedback",
    title: "Share feedback",
    body: "Tell us what to improve as you use the product.",
  },
] as const;

export function DashboardPage() {
  return (
    <div className="space-y-8">
      <section className="jl-fade-up relative overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-600 via-brand-600 to-brand-900 px-6 py-8 text-white shadow-lg shadow-brand-600/20 sm:px-8 sm:py-10 jl-hero-glow">
        <div
          className="pointer-events-none absolute -right-16 -top-16 size-56 rounded-full bg-white/10 blur-2xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-20 left-1/3 size-48 rounded-full bg-accent-500/20 blur-3xl"
          aria-hidden="true"
        />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-xl">
            <p className="text-sm font-semibold tracking-wide text-brand-100">JOBLIK AI</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Welcome back</h1>
            <p className="mt-2 text-sm leading-relaxed text-brand-100 sm:text-base">
              Your hub for CV-powered matching — recommendations, positions, and skills to close the gap.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/onboarding/upload-cv"
                className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-brand-700 shadow-sm transition-transform duration-200 hover:-translate-y-0.5"
              >
                Upload CV
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </Link>
              <Link
                to="/jobs"
                className="inline-flex items-center rounded-xl border border-white/40 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/10"
              >
                Browse jobs
              </Link>
            </div>
          </div>
          <img
            src="/cv-upload-hero.png"
            alt=""
            className="jl-float relative mx-auto hidden h-auto w-40 object-contain drop-shadow-xl sm:w-48 lg:mx-0 lg:block lg:w-52"
          />
        </div>
      </section>

      <section className="jl-fade-up jl-delay-1">
        <h2 className="text-lg font-bold tracking-tight text-slate-900">Explore</h2>
        <p className="mt-1 text-sm text-slate-500">Three paths into your matches.</p>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {doors.map((d) => (
            <Link
              key={d.to}
              to={d.to}
              className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-lg hover:shadow-brand-600/10"
            >
              <div
                className={`mb-4 inline-flex size-11 items-center justify-center rounded-xl bg-gradient-to-br ${d.accent} text-white shadow-md`}
              >
                {d.icon}
              </div>
              <span className={`inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold ${d.chip}`}>Open</span>
              <h3 className="mt-3 text-lg font-semibold text-slate-900 transition-colors group-hover:text-brand-600">
                {d.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{d.body}</p>
              <span className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-brand-600">
                Go
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 16 16"
                  fill="none"
                  aria-hidden="true"
                  className="transition-transform duration-300 group-hover:translate-x-1"
                >
                  <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="jl-fade-up jl-delay-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Next steps</h2>
        <p className="mt-1 text-sm text-slate-500">Build your profile from your CV — no placeholder activity.</p>
        <ul className="mt-5 grid gap-3 sm:grid-cols-3">
          {nextSteps.map((step) => (
            <li key={step.to}>
              <Link
                to={step.to}
                className="flex h-full flex-col rounded-xl border border-slate-100 bg-slate-50/80 p-4 transition-all duration-200 hover:border-brand-200 hover:bg-brand-50/50"
              >
                <span className="font-semibold text-slate-900">{step.title}</span>
                <span className="mt-1 text-sm leading-relaxed text-slate-500">{step.body}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
