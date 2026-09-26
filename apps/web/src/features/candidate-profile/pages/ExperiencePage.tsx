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
  emptyExperience,
  experienceFromDraft,
  loadExperience,
  saveExperience,
  type ExperienceEntry,
} from "../utils/wizard-storage.js";

const DESC_MAX = 1000;

function RequiredMark() {
  return <span className="text-danger-500">*</span>;
}

export function ExperiencePage() {
  const navigate = useNavigate();
  const { draftId } = useParams<{ draftId: string }>();
  const { data: draft, isLoading, isError, error } = useCandidateDraft(draftId);

  const initial = useMemo(() => {
    if (!draftId) return [emptyExperience()];
    const saved = loadExperience(draftId);
    if (saved?.length) return saved;
    if (draft) return experienceFromDraft(draft);
    return [emptyExperience()];
  }, [draft, draftId]);

  const [entries, setEntries] = useState<ExperienceEntry[] | null>(null);
  const list = entries ?? initial;
  const [activeIndex, setActiveIndex] = useState(0);
  const active = list[Math.min(activeIndex, list.length - 1)] ?? list[0]!;
  const [errors, setErrors] = useState<Partial<Record<keyof ExperienceEntry, string>>>({});

  function setField<K extends keyof ExperienceEntry>(key: K, value: ExperienceEntry[K]) {
    setEntries((prev) => {
      const base = prev ?? initial;
      return base.map((e, i) => (i === activeIndex ? { ...e, [key]: value } : e));
    });
  }

  function validate(entry: ExperienceEntry): boolean {
    const next: typeof errors = {};
    if (!entry.jobTitle.trim()) next.jobTitle = "Required";
    if (!entry.company.trim()) next.company = "Required";
    if (!entry.startDate) next.startDate = "Required";
    if (!entry.isCurrent && !entry.endDate) next.endDate = "Required";
    if (!entry.description.trim()) next.description = "Required";
    if (!entry.skillsUsed.trim()) next.skillsUsed = "Required";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onContinue() {
    if (!draftId) return;
    if (!validate(active)) return;
    saveExperience(draftId, list);
    // Skills step is next in the design stepper (mock not built yet)
    navigate(`/onboarding/skills/${draftId}`);
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
          heroSrc="/experience-hero.png"
          tip="Adding your experience helps our AI match you with opportunities that fit your background and goals."
          progressPercent={60}
          completedThrough={1}
          steps={PROFILE_FLOW_STEPS}
          title="You're doing great!"
          subtitle="Complete your profile to unlock better job matches."
        />
      }
    >
      <OnboardingStepper activeIndex={2} steps={PROFILE_FLOW_STEPS} />

      <div className="mt-5 flex min-h-0 flex-1 flex-col">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
          Let&apos;s add your professional experience
        </h1>
        <p className="mt-1 text-sm text-slate-500">Share your work history so we can find the right opportunities for you.</p>

        {list.length > 1 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {list.map((e, i) => (
              <button
                key={e.id}
                type="button"
                onClick={() => setActiveIndex(i)}
                className={`cursor-pointer rounded-lg px-3 py-1 text-xs font-medium ${
                  i === activeIndex ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                }`}
              >
                Role {i + 1}
              </button>
            ))}
          </div>
        ) : null}

        <div className="mt-5 space-y-4 overflow-y-auto">
          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Job Title <RequiredMark />
            </span>
            <input
              className={fieldClass}
              placeholder="e.g. Senior Software Engineer"
              value={active.jobTitle}
              onChange={(e) => setField("jobTitle", e.target.value)}
            />
            {errors.jobTitle ? <p className="mt-1 text-xs text-danger-600">{errors.jobTitle}</p> : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Company <RequiredMark />
            </span>
            <input
              className={fieldClass}
              placeholder="e.g. Acme Inc."
              value={active.company}
              onChange={(e) => setField("company", e.target.value)}
            />
            {errors.company ? <p className="mt-1 text-xs text-danger-600">{errors.company}</p> : null}
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1.5 block font-medium text-slate-700">
                Start Date <RequiredMark />
              </span>
              <input
                type="month"
                className={fieldClass}
                value={active.startDate}
                onChange={(e) => setField("startDate", e.target.value)}
              />
              {errors.startDate ? <p className="mt-1 text-xs text-danger-600">{errors.startDate}</p> : null}
            </label>

            <div>
              <label className="block text-sm">
                <span className="mb-1.5 block font-medium text-slate-700">
                  End Date (or Present) {!active.isCurrent ? <RequiredMark /> : null}
                </span>
                <input
                  type="month"
                  className={fieldClass}
                  value={active.endDate}
                  disabled={active.isCurrent}
                  onChange={(e) => setField("endDate", e.target.value)}
                />
                {errors.endDate ? <p className="mt-1 text-xs text-danger-600">{errors.endDate}</p> : null}
              </label>
              <label className="mt-2 flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  className="size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                  checked={active.isCurrent}
                  onChange={(e) => {
                    setField("isCurrent", e.target.checked);
                    if (e.target.checked) setField("endDate", "");
                  }}
                />
                I currently work here
              </label>
            </div>
          </div>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Description <RequiredMark />
            </span>
            <textarea
              className={`${fieldClass} min-h-[120px] resize-y`}
              placeholder="Describe your key responsibilities, achievements, and impact..."
              maxLength={DESC_MAX}
              value={active.description}
              onChange={(e) => setField("description", e.target.value)}
            />
            <span className="mt-1 block text-right text-xs text-slate-400">
              {active.description.length} / {DESC_MAX}
            </span>
            {errors.description ? <p className="mt-1 text-xs text-danger-600">{errors.description}</p> : null}
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">
              Skills Used <RequiredMark />
            </span>
            <input
              className={fieldClass}
              placeholder="Add skills separated by commas"
              value={active.skillsUsed}
              onChange={(e) => setField("skillsUsed", e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-400">e.g. Python, SQL, Project Management, Agile, Data Analysis</p>
            {errors.skillsUsed ? <p className="mt-1 text-xs text-danger-600">{errors.skillsUsed}</p> : null}
          </label>
        </div>

        <button
          type="button"
          onClick={() => {
            setEntries((prev) => [...(prev ?? initial), emptyExperience()]);
            setActiveIndex(list.length);
            setErrors({});
          }}
          className="mt-4 cursor-pointer self-start text-sm font-semibold text-brand-600 hover:underline"
        >
          + Add another role
        </button>

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() => navigate(`/onboarding/education/${draftId}`)}
            onContinue={onContinue}
          />
          <OnboardingSecurityNote />
        </div>
      </div>
    </OnboardingFrame>
  );
}
