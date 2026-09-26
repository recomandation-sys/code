import type { ReactNode } from "react";

export const UPLOAD_FLOW_STEPS = [
  "Upload CV",
  "Personal Info",
  "Education",
  "Professional Experience",
  "Skills",
  "Languages",
  "Preferences",
] as const;

/** Stepper after CV upload — matches Personal Info+ design mocks. */
export const PROFILE_FLOW_STEPS = [
  "Personal Info",
  "Education",
  "Professional Experience",
  "Skills",
  "Certifications",
  "Languages",
  "Preferences",
] as const;

/** @deprecated use UPLOAD_FLOW_STEPS */
export const ONBOARDING_STEPS = UPLOAD_FLOW_STEPS;

export function OnboardingStepper({
  activeIndex,
  steps = UPLOAD_FLOW_STEPS,
}: {
  activeIndex: number;
  steps?: readonly string[];
}) {
  return (
    <ol className="flex w-full items-start justify-between gap-1 overflow-x-auto pb-1">
      {steps.map((label, index) => {
        const active = index === activeIndex;
        const done = index < activeIndex;
        return (
          <li key={label} className="relative flex min-w-0 flex-1 flex-col items-center text-center">
            {index < steps.length - 1 ? (
              <span
                className={`absolute left-[calc(50%+14px)] right-[calc(-50%+14px)] top-3.5 h-px ${
                  done ? "bg-brand-600" : "bg-slate-200"
                }`}
                aria-hidden="true"
              />
            ) : null}
            <span
              className={`relative z-10 flex size-7 items-center justify-center rounded-full text-xs font-semibold ${
                active || done
                  ? "bg-brand-600 text-white"
                  : "border border-slate-300 bg-white text-slate-400"
              }`}
            >
              {done ? (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              ) : (
                index + 1
              )}
            </span>
            <span
              className={`mt-2 hidden text-[11px] font-medium leading-tight sm:block ${
                active ? "text-brand-600" : "text-slate-400"
              }`}
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function OnboardingSidebar({
  heroSrc,
  tip,
  progressPercent = 0,
  completedThrough = 0,
  steps = UPLOAD_FLOW_STEPS,
  title = "Let's get started!",
  subtitle,
}: {
  heroSrc: string;
  tip: string;
  progressPercent?: number;
  /** Highest completed checklist index. */
  completedThrough?: number;
  steps?: readonly string[];
  title?: string;
  subtitle?: string;
}) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.max(0, Math.min(100, progressPercent)) / 100) * c;

  return (
    <aside className="flex w-full flex-col gap-3 lg:w-[300px] lg:shrink-0 xl:w-[320px]">
      <img src={heroSrc} alt="" className="mx-auto h-auto w-full max-w-[240px] object-contain lg:max-w-none" />

      <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3.5">
        <div className="flex items-start gap-3">
          <div className="relative flex size-14 shrink-0 items-center justify-center">
            <svg width="56" height="56" viewBox="0 0 64 64" className="-rotate-90" aria-hidden="true">
              <circle cx="32" cy="32" r={r} fill="none" stroke="#e2e8f0" strokeWidth="5" />
              <circle
                cx="32"
                cy="32"
                r={r}
                fill="none"
                stroke="#0070fd"
                strokeWidth="5"
                strokeLinecap="round"
                strokeDasharray={c}
                strokeDashoffset={offset}
              />
            </svg>
            <span className="absolute text-sm font-bold text-slate-800">{progressPercent}%</span>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-800">{title}</p>
            {subtitle ? <p className="mt-0.5 text-[11px] leading-snug text-slate-500">{subtitle}</p> : null}
            <ul className="mt-1.5 space-y-1 text-xs text-slate-500">
              {steps.map((step, i) => {
                const done = i <= completedThrough;
                return (
                  <li key={step} className="flex items-center gap-2">
                    {done ? (
                      <span className="inline-flex size-3.5 items-center justify-center rounded-full bg-brand-600 text-white">
                        <svg width="8" height="8" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                          <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                        </svg>
                      </span>
                    ) : (
                      <span className="size-3.5 rounded-full border border-slate-300" />
                    )}
                    <span className={done ? "font-medium text-slate-800" : ""}>{step}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-auto rounded-xl border border-brand-100 bg-brand-50 p-3.5">
        <div className="flex gap-2">
          <span className="mt-0.5 text-brand-600" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1.5l1.2 3.6H13l-3 2.2 1.2 3.7L8 9.8l-3.2 2.2 1.2-3.7-3-2.2h3.8L8 1.5z" />
            </svg>
          </span>
          <div>
            <p className="text-sm font-semibold text-slate-800">Why this matters</p>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">{tip}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

export function OnboardingFrame({
  sidebar,
  children,
}: {
  sidebar: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col px-3 py-3 sm:px-5 sm:py-4 lg:px-6">
      <div className="flex min-h-0 flex-1 flex-col gap-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 lg:flex-row lg:gap-8 lg:p-6">
        {sidebar}
        <section className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</section>
      </div>
    </div>
  );
}

export function OnboardingNav({
  onBack,
  onContinue,
  continueDisabled,
  continueLabel = "Continue",
  continueIcon = "arrow",
}: {
  onBack: () => void;
  onContinue: () => void;
  continueDisabled?: boolean;
  continueLabel?: string;
  continueIcon?: "arrow" | "check";
}) {
  return (
    <div className="mt-4 flex items-center justify-between gap-3">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-brand-600 px-5 py-2.5 text-sm font-semibold text-brand-600 hover:bg-brand-50"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        Back
      </button>
      <button
        type="button"
        onClick={onContinue}
        disabled={continueDisabled}
        className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {continueIcon === "check" ? (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3.5 8.5L6.5 11.5L12.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        ) : null}
        {continueLabel}
        {continueIcon === "arrow" ? (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        ) : null}
      </button>
    </div>
  );
}

export function OnboardingSecurityNote() {
  return (
    <p className="mt-3 flex items-center justify-center gap-1.5 text-center text-xs text-slate-400">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="text-slate-400">
        <path
          d="M12 3l7 3v5c0 4.5-3 8.2-7 9.5C8 19.2 5 15.5 5 11V6l7-3z"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      Your information is secure and will never be shared without your permission.
    </p>
  );
}

export const fieldClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";
