import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ApiClientError } from "../../../api/client.js";
import {
  OnboardingFrame,
  OnboardingNav,
  OnboardingSecurityNote,
  OnboardingSidebar,
  OnboardingStepper,
  PROFILE_FLOW_STEPS,
  fieldClass,
} from "../components/OnboardingChrome.js";
import { useCandidateDraft } from "../hooks/useCandidateDraft.js";
import {
  emptyLanguage,
  languagesFromDraft,
  loadLanguages,
  saveLanguages,
  type LanguageEntry,
} from "../utils/wizard-storage.js";

const LANGUAGES = [
  "Arabic",
  "French",
  "English",
  "Spanish",
  "German",
  "Italian",
  "Portuguese",
  "Dutch",
  "Turkish",
  "Chinese",
  "Japanese",
  "Other",
] as const;

const PROFICIENCY_OPTIONS = [
  { value: "NATIVE", label: "Native or bilingual" },
  { value: "FLUENT", label: "Full professional proficiency" },
  { value: "ADVANCED", label: "Professional working proficiency" },
  { value: "INTERMEDIATE", label: "Limited working proficiency" },
  { value: "BASIC", label: "Elementary proficiency" },
] as const;

function RequiredMark() {
  return <span className="text-danger-500">*</span>;
}

export function LanguagesWizardPage() {
  const navigate = useNavigate();
  const { draftId } = useParams<{ draftId: string }>();
  const { data: draft, isLoading, isError, error } = useCandidateDraft(draftId);

  const initial = useMemo(() => {
    if (!draftId) return [emptyLanguage()];
    const saved = loadLanguages(draftId);
    if (saved?.length) return saved;
    if (draft?.languages.length) return languagesFromDraft(draft);
    return [emptyLanguage(), emptyLanguage(), emptyLanguage()];
  }, [draft, draftId]);

  const [entries, setEntries] = useState<LanguageEntry[] | null>(null);
  const list = entries ?? initial;
  const [errors, setErrors] = useState<Record<string, string>>({});

  function update(id: string, patch: Partial<LanguageEntry>) {
    setEntries((prev) => (prev ?? initial).map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    for (const e of list) {
      if (!e.language.trim()) next[`${e.id}.language`] = "Required";
      if (!e.level) next[`${e.id}.level`] = "Required";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onContinue() {
    if (!draftId) return;
    if (!validate()) return;
    saveLanguages(draftId, list);
    navigate(`/onboarding/survey?draftId=${draftId}`);
  }

  if (!draftId) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-500">
        Missing draft.{" "}
        <button type="button" className="ml-1 text-brand-600 underline" onClick={() => navigate("/onboarding/upload-cv")}>
          Upload a CV
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-slate-500" role="status">
        Loading your draft…
      </div>
    );
  }

  if (isError) {
    const message = error instanceof ApiClientError ? error.message : "This draft could not be loaded.";
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-sm text-danger-600">{message}</p>
        <button type="button" className="text-sm text-brand-600 underline" onClick={() => navigate("/onboarding/upload-cv")}>
          Upload a CV
        </button>
      </div>
    );
  }

  return (
    <OnboardingFrame
      sidebar={
        <OnboardingSidebar
          heroSrc="/certifications-hero.png"
          tip="Language skills help us match you with the right local and international opportunities."
          progressPercent={90}
          completedThrough={5}
          steps={PROFILE_FLOW_STEPS}
          title="Great progress! Add the languages you use professionally."
        />
      }
    >
      <OnboardingStepper activeIndex={5} steps={PROFILE_FLOW_STEPS} />

      <div className="mt-5 flex min-h-0 flex-1 flex-col">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">What languages do you speak?</h1>
        <p className="mt-1 text-sm text-slate-500">Add each language and select your proficiency level.</p>

        <div className="mt-5 space-y-3 overflow-y-auto">
          {list.map((entry) => (
            <div key={entry.id} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
              <label className="block text-sm">
                <span className="mb-1.5 block font-medium text-slate-700">
                  Language <RequiredMark />
                </span>
                <select
                  className={fieldClass}
                  value={entry.language}
                  onChange={(e) => update(entry.id, { language: e.target.value })}
                >
                  <option value="">Select language</option>
                  {LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang}
                    </option>
                  ))}
                  {entry.language && !LANGUAGES.includes(entry.language as (typeof LANGUAGES)[number]) ? (
                    <option value={entry.language}>{entry.language}</option>
                  ) : null}
                </select>
                {errors[`${entry.id}.language`] ? (
                  <p className="mt-1 text-xs text-danger-600">{errors[`${entry.id}.language`]}</p>
                ) : null}
              </label>

              <label className="block text-sm">
                <span className="mb-1.5 block font-medium text-slate-700">
                  Proficiency level <RequiredMark />
                </span>
                <select
                  className={fieldClass}
                  value={entry.level}
                  onChange={(e) => update(entry.id, { level: e.target.value })}
                >
                  <option value="">Select level</option>
                  {PROFICIENCY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                {errors[`${entry.id}.level`] ? (
                  <p className="mt-1 text-xs text-danger-600">{errors[`${entry.id}.level`]}</p>
                ) : null}
              </label>

              <button
                type="button"
                aria-label="Remove language"
                disabled={list.length <= 1}
                onClick={() => setEntries((prev) => (prev ?? initial).filter((e) => e.id !== entry.id))}
                className="mb-0.5 inline-flex size-10 cursor-pointer items-center justify-center rounded-lg border border-slate-200 text-slate-400 hover:bg-slate-50 hover:text-danger-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M5 7h14M10 7V5h4v2M9 7v12h6V7"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setEntries((prev) => [...(prev ?? initial), emptyLanguage()])}
          className="mt-4 inline-flex cursor-pointer items-center gap-2 self-start rounded-xl border border-brand-600 px-4 py-2.5 text-sm font-semibold text-brand-600 hover:bg-brand-50"
        >
          <span aria-hidden="true">+</span>
          Add another language
        </button>

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() => navigate(`/onboarding/certifications/${draftId}`)}
            onContinue={onContinue}
          />
          <OnboardingSecurityNote />
        </div>
      </div>
    </OnboardingFrame>
  );
}
