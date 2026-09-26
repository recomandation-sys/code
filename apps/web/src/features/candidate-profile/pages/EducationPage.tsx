import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  OnboardingFrame,
  OnboardingNav,
  OnboardingSecurityNote,
  OnboardingSidebar,
  OnboardingStepper,
  PROFILE_FLOW_STEPS,
  fieldClass,
} from "../components/OnboardingChrome.js";
import {
  emptyEducation,
  loadEducation,
  saveEducation,
  type EducationEntry,
} from "../utils/wizard-storage.js";

function RequiredMark() {
  return <span className="text-danger-500">*</span>;
}

export function EducationPage() {
  const navigate = useNavigate();
  const { draftId } = useParams<{ draftId: string }>();

  const initial = useMemo(() => {
    if (!draftId) return [emptyEducation()];
    return loadEducation(draftId) ?? [emptyEducation()];
  }, [draftId]);

  const [entries, setEntries] = useState<EducationEntry[]>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});

  function update(id: string, patch: Partial<EducationEntry>) {
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    for (const e of entries) {
      if (!e.degree.trim()) next[`${e.id}.degree`] = "Required";
      if (!e.institution.trim()) next[`${e.id}.institution`] = "Required";
      if (!e.field.trim()) next[`${e.id}.field`] = "Required";
      if (!e.startDate) next[`${e.id}.startDate`] = "Required";
      if (!e.isCurrent && !e.endDate) next[`${e.id}.endDate`] = "Required";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onContinue() {
    if (!draftId) return;
    if (!validate()) return;
    saveEducation(draftId, entries);
    navigate(`/onboarding/experience/${draftId}`);
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

  return (
    <OnboardingFrame
      sidebar={
        <OnboardingSidebar
          heroSrc="/education-hero.png"
          tip="Your education history helps match roles to your level and field of study."
          progressPercent={40}
          completedThrough={0}
          steps={PROFILE_FLOW_STEPS}
          title="You're off to a great start!"
          subtitle="Complete your profile to unlock better job matches."
        />
      }
    >
      <OnboardingStepper activeIndex={1} steps={PROFILE_FLOW_STEPS} />

      <div className="mt-5 flex min-h-0 flex-1 flex-col">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">Add your education</h1>
        <p className="mt-1 text-sm text-slate-500">Degrees, schools, and fields of study — you can add more than one.</p>

        <div className="mt-5 space-y-5 overflow-y-auto">
          {entries.map((entry, index) => (
            <div key={entry.id} className="rounded-xl border border-slate-200 p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-800">Education {index + 1}</p>
                {entries.length > 1 ? (
                  <button
                    type="button"
                    className="cursor-pointer text-xs font-medium text-danger-600 hover:underline"
                    onClick={() => setEntries((prev) => prev.filter((e) => e.id !== entry.id))}
                  >
                    Remove
                  </button>
                ) : null}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm sm:col-span-2">
                  <span className="mb-1.5 block font-medium text-slate-700">
                    Degree / diploma <RequiredMark />
                  </span>
                  <input
                    className={fieldClass}
                    placeholder="e.g. Bachelor's in Computer Science"
                    value={entry.degree}
                    onChange={(e) => update(entry.id, { degree: e.target.value })}
                  />
                  {errors[`${entry.id}.degree`] ? (
                    <p className="mt-1 text-xs text-danger-600">{errors[`${entry.id}.degree`]}</p>
                  ) : null}
                </label>
                <label className="block text-sm">
                  <span className="mb-1.5 block font-medium text-slate-700">
                    Institution <RequiredMark />
                  </span>
                  <input
                    className={fieldClass}
                    placeholder="e.g. University of Tunis"
                    value={entry.institution}
                    onChange={(e) => update(entry.id, { institution: e.target.value })}
                  />
                  {errors[`${entry.id}.institution`] ? (
                    <p className="mt-1 text-xs text-danger-600">{errors[`${entry.id}.institution`]}</p>
                  ) : null}
                </label>
                <label className="block text-sm">
                  <span className="mb-1.5 block font-medium text-slate-700">
                    Field of study <RequiredMark />
                  </span>
                  <input
                    className={fieldClass}
                    placeholder="e.g. Software Engineering"
                    value={entry.field}
                    onChange={(e) => update(entry.id, { field: e.target.value })}
                  />
                  {errors[`${entry.id}.field`] ? (
                    <p className="mt-1 text-xs text-danger-600">{errors[`${entry.id}.field`]}</p>
                  ) : null}
                </label>
                <label className="block text-sm">
                  <span className="mb-1.5 block font-medium text-slate-700">
                    Start date <RequiredMark />
                  </span>
                  <input
                    type="month"
                    className={fieldClass}
                    value={entry.startDate}
                    onChange={(e) => update(entry.id, { startDate: e.target.value })}
                  />
                  {errors[`${entry.id}.startDate`] ? (
                    <p className="mt-1 text-xs text-danger-600">{errors[`${entry.id}.startDate`]}</p>
                  ) : null}
                </label>
                <label className="block text-sm">
                  <span className="mb-1.5 block font-medium text-slate-700">
                    End date {!entry.isCurrent ? <RequiredMark /> : null}
                  </span>
                  <input
                    type="month"
                    className={fieldClass}
                    value={entry.endDate}
                    disabled={entry.isCurrent}
                    onChange={(e) => update(entry.id, { endDate: e.target.value })}
                  />
                  {errors[`${entry.id}.endDate`] ? (
                    <p className="mt-1 text-xs text-danger-600">{errors[`${entry.id}.endDate`]}</p>
                  ) : null}
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                    checked={entry.isCurrent}
                    onChange={(e) =>
                      update(entry.id, {
                        isCurrent: e.target.checked,
                        endDate: e.target.checked ? "" : entry.endDate,
                      })
                    }
                  />
                  I currently study here
                </label>
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setEntries((prev) => [...prev, emptyEducation()])}
          className="mt-4 cursor-pointer self-start text-sm font-semibold text-brand-600 hover:underline"
        >
          + Add education
        </button>

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() => navigate(`/onboarding/personal-info/${draftId}`)}
            onContinue={onContinue}
          />
          <OnboardingSecurityNote />
        </div>
      </div>
    </OnboardingFrame>
  );
}
