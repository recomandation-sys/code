import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  OnboardingFrame,
  OnboardingNav,
  OnboardingSecurityNote,
  OnboardingSidebar,
  OnboardingStepper,
  PROFILE_FLOW_STEPS,
} from "../../candidate-profile/components/OnboardingChrome.js";

const POINTS = [
  "Your data is encrypted in transit and at rest.",
  "We never share your CV without your consent.",
  "You can delete your account and data anytime.",
  "Matches stay private to your account.",
] as const;

export function PrivacyPage() {
  const navigate = useNavigate();
  const [consented, setConsented] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onContinue() {
    if (!consented) {
      setError("Please agree to continue.");
      return;
    }
    setError(null);
    navigate("/dashboard");
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    onContinue();
  }

  return (
    <OnboardingFrame
      sidebar={
        <OnboardingSidebar
          heroSrc="/cv-check-hero.png"
          tip="Consent is the last step before your dashboard — you stay in control of what JOBLIK AI uses."
          progressPercent={100}
          completedThrough={PROFILE_FLOW_STEPS.length - 1}
          steps={PROFILE_FLOW_STEPS}
          title="You're all set!"
          subtitle="One privacy check, then your matches open up."
        />
      }
    >
      <OnboardingStepper activeIndex={PROFILE_FLOW_STEPS.length - 1} steps={PROFILE_FLOW_STEPS} />

      <form className="jl-fade-up mt-5 flex min-h-0 flex-1 flex-col" onSubmit={onSubmit}>
        <div className="mx-auto flex size-14 items-center justify-center rounded-full bg-brand-50 text-brand-600">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 3l7 3v5c0 4.5-3 8.2-7 9.5C8 19.2 5 15.5 5 11V6l7-3z"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <h1 className="mt-4 text-center text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
          Your data, your control
        </h1>
        <p className="mt-1 text-center text-sm text-slate-500">
          Before you open your dashboard, a quick look at how we handle what you shared.
        </p>

        <ul className="mt-6 space-y-3 rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-sm text-slate-600">
          {POINTS.map((text) => (
            <li key={text} className="flex gap-2.5">
              <span className="mt-0.5 inline-flex size-4 shrink-0 items-center justify-center rounded-full bg-accent-500 text-[10px] font-bold text-white">
                ✓
              </span>
              {text}
            </li>
          ))}
        </ul>

        <label className="mt-6 flex cursor-pointer items-start gap-3 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={consented}
            onChange={(e) => {
              setConsented(e.target.checked);
              if (e.target.checked) setError(null);
            }}
            className="mt-1 size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
          />
          <span>
            I understand and agree to the{" "}
            <Link to="/" className="font-medium text-brand-600 underline">
              privacy policy
            </Link>
            .
          </span>
        </label>
        {error ? <p className="mt-2 text-xs text-danger-600">{error}</p> : null}

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() => navigate(-1)}
            onContinue={onContinue}
            continueDisabled={!consented}
            continueLabel="Continue to Dashboard"
            continueIcon="check"
          />
          <OnboardingSecurityNote />
        </div>
      </form>
    </OnboardingFrame>
  );
}
