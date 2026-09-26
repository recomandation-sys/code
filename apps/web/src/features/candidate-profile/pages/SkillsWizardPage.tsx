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
import { loadSkills, saveSkills, skillsFromDraft } from "../utils/wizard-storage.js";

export function SkillsWizardPage() {
  const navigate = useNavigate();
  const { draftId } = useParams<{ draftId: string }>();
  const { data: draft, isLoading, isError, error } = useCandidateDraft(draftId);

  const initialSkills = useMemo(() => {
    if (!draftId) return [] as string[];
    const saved = loadSkills(draftId);
    if (saved?.skills.length) return saved.skills;
    if (draft) return skillsFromDraft(draft).skills;
    return [];
  }, [draft, draftId]);

  const [skills, setSkills] = useState<string[] | null>(null);
  const list = skills ?? initialSkills;
  const [draftSkill, setDraftSkill] = useState("");

  function addSkill() {
    const value = draftSkill.trim();
    if (!value) return;
    setSkills((prev) => {
      const base = prev ?? initialSkills;
      if (base.some((s) => s.toLowerCase() === value.toLowerCase())) return base;
      return [...base, value];
    });
    setDraftSkill("");
  }

  function onContinue() {
    if (!draftId) return;
    saveSkills(draftId, { skills: list });
    navigate(`/onboarding/certifications/${draftId}`);
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
          tip="Skills power job matching, suitable positions, and your skills-gap list."
          progressPercent={70}
          completedThrough={2}
          steps={PROFILE_FLOW_STEPS}
          title="You're doing great!"
          subtitle="Complete your profile to unlock better job matches."
        />
      }
    >
      <OnboardingStepper activeIndex={3} steps={PROFILE_FLOW_STEPS} />

      <div className="mt-5 flex min-h-0 flex-1 flex-col">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">Your skills</h1>
        <p className="mt-1 text-sm text-slate-500">
          We pre-filled skills from your CV. Add or remove anything before continuing.
        </p>

        <ul className="mt-5 flex flex-wrap gap-2">
          {list.map((skill) => (
            <li
              key={skill}
              className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700"
            >
              {skill}
              <button
                type="button"
                aria-label={`Remove ${skill}`}
                className="cursor-pointer text-brand-500 hover:text-brand-800"
                onClick={() => setSkills((prev) => (prev ?? initialSkills).filter((s) => s !== skill))}
              >
                ×
              </button>
            </li>
          ))}
          {list.length === 0 ? <li className="text-sm text-slate-400">No skills yet — add one below.</li> : null}
        </ul>

        <div className="mt-4 flex gap-2">
          <input
            className={fieldClass}
            placeholder="Add a skill"
            value={draftSkill}
            onChange={(e) => setDraftSkill(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addSkill();
              }
            }}
          />
          <button
            type="button"
            onClick={addSkill}
            className="cursor-pointer rounded-lg border border-slate-300 px-4 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Add
          </button>
        </div>

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() => navigate(`/onboarding/experience/${draftId}`)}
            onContinue={onContinue}
          />
          <OnboardingSecurityNote />
        </div>
      </div>
    </OnboardingFrame>
  );
}
