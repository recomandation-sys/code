import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { ContractType, MobilityPreference, WorkMode } from "@job-recommender/contracts";

import { ApiClientError } from "../../../api/client.js";
import {
  OnboardingFrame,
  OnboardingNav,
  OnboardingSecurityNote,
  OnboardingSidebar,
  OnboardingStepper,
  PROFILE_FLOW_STEPS,
} from "../components/OnboardingChrome.js";
import { useCandidateDraft } from "../hooks/useCandidateDraft.js";
import { useSubmitPreferenceSurvey } from "../hooks/useSubmitPreferenceSurvey.js";
import {
  loadPreferences,
  preferencesFromDraft,
  savePreferences,
  type PreferencesDraft,
} from "../utils/wizard-storage.js";

type WhereToWork = PreferencesDraft["whereToWork"];
type Goal = PreferencesDraft["goals"][number];

const WHERE_OPTIONS: { value: WhereToWork; label: string; icon: "pin" | "plane" | "globe" }[] = [
  { value: "LOCAL", label: "Local opportunities", icon: "pin" },
  { value: "FOREIGN", label: "Opportunities abroad", icon: "plane" },
  { value: "BOTH", label: "Both", icon: "globe" },
];

const WORK_MODE_OPTIONS: { value: WorkMode; label: string }[] = [
  { value: "ONSITE", label: "On-site" },
  { value: "REMOTE", label: "Remote" },
  { value: "HYBRID", label: "Hybrid" },
];

const CONTRACT_OPTIONS: { value: ContractType; label: string }[] = [
  { value: "CDI", label: "CDI" },
  { value: "CDD", label: "CDD" },
  { value: "INTERNSHIP", label: "Internship" },
  { value: "FREELANCE", label: "Freelance" },
];

const GOAL_OPTIONS: { value: Goal; label: string; icon: "briefcase" | "target" }[] = [
  { value: "FIND_JOB", label: "Find a job", icon: "briefcase" },
  { value: "OPTIMIZE_PROFILE", label: "Optimize my profile", icon: "target" },
];

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function toMobility(where: WhereToWork): MobilityPreference[] {
  if (where === "LOCAL") return ["LOCAL"];
  if (where === "FOREIGN") return ["FOREIGN"];
  return ["LOCAL", "FOREIGN"];
}

function Icon({ name }: { name: "pin" | "plane" | "globe" | "briefcase" | "target" }) {
  const common = "text-brand-600";
  if (name === "pin") {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className={common} aria-hidden="true">
        <path
          d="M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11z"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <circle cx="12" cy="10" r="2.2" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    );
  }
  if (name === "plane") {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className={common} aria-hidden="true">
        <path
          d="M3 12l18-8-4 16-5-5-4 2 1.5-5L3 12z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  if (name === "globe") {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className={common} aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
        <path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    );
  }
  if (name === "briefcase") {
    return (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className={common} aria-hidden="true">
        <rect x="3" y="7" width="18" height="13" rx="2" stroke="currentColor" strokeWidth="1.6" />
        <path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 12h18" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    );
  }
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className={common} aria-hidden="true">
      <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function SelectCard({
  selected,
  onClick,
  label,
  icon,
}: {
  selected: boolean;
  onClick: () => void;
  label: string;
  icon: "pin" | "plane" | "globe" | "briefcase" | "target";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative flex cursor-pointer flex-col items-start gap-3 rounded-xl border px-4 py-4 text-left transition-colors ${
        selected ? "border-brand-600 bg-brand-50/40" : "border-slate-200 bg-white hover:border-brand-300"
      }`}
    >
      {selected ? (
        <span className="absolute right-3 top-3 inline-flex size-5 items-center justify-center rounded-full bg-brand-600 text-white">
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </span>
      ) : null}
      <Icon name={icon} />
      <span className="text-sm font-semibold text-slate-800">{label}</span>
    </button>
  );
}

function PillOption({
  selected,
  onClick,
  label,
}: {
  selected: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex cursor-pointer items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors ${
        selected
          ? "border-brand-600 bg-white text-brand-700"
          : "border-slate-200 bg-white text-slate-600 hover:border-brand-300"
      }`}
    >
      {selected ? (
        <span className="inline-flex size-4 items-center justify-center rounded-full bg-brand-600 text-white">
          <svg width="8" height="8" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </span>
      ) : null}
      {label}
    </button>
  );
}

function RequiredMark() {
  return <span className="text-danger-500">*</span>;
}

export function PreferenceSurveyPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const profileId = searchParams.get("profileId") ?? "";
  const draftId = searchParams.get("draftId") ?? "";
  const submitSurvey = useSubmitPreferenceSurvey();
  const { data: draft } = useCandidateDraft(draftId || undefined);

  const defaults = useMemo((): PreferencesDraft => {
    if (draftId) {
      const saved = loadPreferences(draftId);
      if (saved) return saved;
      if (draft) return preferencesFromDraft(draft);
    }
    return {
      whereToWork: "BOTH",
      workModes: [],
      contractTypes: [],
      goals: [],
    };
  }, [draft, draftId]);

  const [form, setForm] = useState<PreferencesDraft | null>(null);
  const values = form ?? defaults;
  const [errors, setErrors] = useState<{
    whereToWork?: string;
    workModes?: string;
    contractTypes?: string;
    goals?: string;
  }>({});

  function setField<K extends keyof PreferencesDraft>(key: K, value: PreferencesDraft[K]) {
    setForm((prev) => ({ ...(prev ?? defaults), [key]: value }));
  }

  function validate(data: PreferencesDraft): boolean {
    const next: typeof errors = {};
    if (!data.whereToWork) next.whereToWork = "Required";
    if (data.workModes.length === 0) next.workModes = "Select at least one";
    if (data.contractTypes.length === 0) next.contractTypes = "Select at least one";
    if (data.goals.length === 0) next.goals = "Select at least one";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onComplete() {
    if (!validate(values)) return;

    if (draftId && !profileId) {
      // ponytail: goals are UI-only until preferences API accepts them
      savePreferences(draftId, values);
      navigate("/onboarding/privacy");
      return;
    }

    if (!profileId) return;

    submitSurvey.mutate(
      {
        profileId,
        contractTypes: values.contractTypes as ContractType[],
        workModes: values.workModes as WorkMode[],
        mobilityPreferences: toMobility(values.whereToWork),
        preferredCountries: [],
      },
      { onSuccess: () => navigate("/onboarding/privacy") },
    );
  }

  if (!profileId && !draftId) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-500">
        No profile to configure.{" "}
        <button type="button" className="ml-1 text-brand-600 underline" onClick={() => navigate("/onboarding/upload-cv")}>
          Upload a CV
        </button>
      </div>
    );
  }

  const errorMessage =
    submitSurvey.error instanceof ApiClientError
      ? submitSurvey.error.message
      : "We couldn't save your preferences. Please try again.";

  return (
    <OnboardingFrame
      sidebar={
        <OnboardingSidebar
          heroSrc="/experience-hero.png"
          tip="These preferences help our AI recommend better opportunities for you."
          progressPercent={90}
          completedThrough={5}
          steps={PROFILE_FLOW_STEPS}
          title="One last step!"
          subtitle="Tell us what you're looking for so we can personalize matches."
        />
      }
    >
      <OnboardingStepper activeIndex={6} steps={PROFILE_FLOW_STEPS} />

      <div className="mt-5 flex min-h-0 flex-1 flex-col">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">What are you looking for?</h1>
        <p className="mt-1 text-sm text-slate-500">Choose your preferences so we can personalize your experience.</p>

        <div className="mt-5 space-y-6 overflow-y-auto pb-2">
          <section>
            <p className="mb-3 text-sm font-semibold text-slate-800">
              Where do you want to work? <RequiredMark />
            </p>
            <div className="grid gap-3 sm:grid-cols-3">
              {WHERE_OPTIONS.map((opt) => (
                <SelectCard
                  key={opt.value}
                  selected={values.whereToWork === opt.value}
                  onClick={() => setField("whereToWork", opt.value)}
                  label={opt.label}
                  icon={opt.icon}
                />
              ))}
            </div>
            {errors.whereToWork ? <p className="mt-2 text-xs text-danger-600">{errors.whereToWork}</p> : null}
          </section>

          <section>
            <p className="mb-3 text-sm font-semibold text-slate-800">
              Preferred work mode <RequiredMark />
            </p>
            <div className="flex flex-wrap gap-2">
              {WORK_MODE_OPTIONS.map((opt) => (
                <PillOption
                  key={opt.value}
                  selected={values.workModes.includes(opt.value)}
                  onClick={() => setField("workModes", toggle(values.workModes, opt.value))}
                  label={opt.label}
                />
              ))}
            </div>
            {errors.workModes ? <p className="mt-2 text-xs text-danger-600">{errors.workModes}</p> : null}
          </section>

          <section>
            <p className="mb-3 text-sm font-semibold text-slate-800">
              Contract type <RequiredMark />
            </p>
            <div className="flex flex-wrap gap-2">
              {CONTRACT_OPTIONS.map((opt) => (
                <PillOption
                  key={opt.value}
                  selected={values.contractTypes.includes(opt.value)}
                  onClick={() => setField("contractTypes", toggle(values.contractTypes, opt.value))}
                  label={opt.label}
                />
              ))}
            </div>
            {errors.contractTypes ? <p className="mt-2 text-xs text-danger-600">{errors.contractTypes}</p> : null}
          </section>

          <section>
            <p className="mb-3 text-sm font-semibold text-slate-800">
              What is your goal? <RequiredMark />
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {GOAL_OPTIONS.map((opt) => (
                <SelectCard
                  key={opt.value}
                  selected={values.goals.includes(opt.value)}
                  onClick={() => setField("goals", toggle(values.goals, opt.value))}
                  label={opt.label}
                  icon={opt.icon}
                />
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-400">You can select more than one option.</p>
            {errors.goals ? <p className="mt-2 text-xs text-danger-600">{errors.goals}</p> : null}
          </section>
        </div>

        {submitSurvey.isError ? <p className="mt-3 text-sm text-danger-600">{errorMessage}</p> : null}

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() =>
              draftId
                ? navigate(`/onboarding/languages/${draftId}`)
                : navigate(-1)
            }
            onContinue={onComplete}
            continueDisabled={submitSurvey.isPending}
            continueLabel={submitSurvey.isPending ? "Saving…" : "Complete profile"}
            continueIcon="check"
          />
          <OnboardingSecurityNote />
        </div>
      </div>
    </OnboardingFrame>
  );
}
