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
  certificationsFromDraft,
  emptyCertification,
  loadCertifications,
  saveCertifications,
  type CertificationEntry,
} from "../utils/wizard-storage.js";

function RequiredMark() {
  return <span className="text-danger-500">*</span>;
}

export function CertificationsPage() {
  const navigate = useNavigate();
  const { draftId } = useParams<{ draftId: string }>();
  const { data: draft, isLoading, isError, error } = useCandidateDraft(draftId);

  const initial = useMemo(() => {
    if (!draftId) return [emptyCertification()];
    const saved = loadCertifications(draftId);
    if (saved?.length) return saved;
    if (draft?.certifications.length) return certificationsFromDraft(draft);
    return [emptyCertification()];
  }, [draft, draftId]);

  const [entries, setEntries] = useState<CertificationEntry[] | null>(null);
  const list = entries ?? initial;
  const [activeIndex, setActiveIndex] = useState(0);
  const active = list[Math.min(activeIndex, list.length - 1)] ?? list[0]!;
  const [errors, setErrors] = useState<Partial<Record<keyof CertificationEntry, string>>>({});

  function setField<K extends keyof CertificationEntry>(key: K, value: CertificationEntry[K]) {
    setEntries((prev) => {
      const base = prev ?? initial;
      return base.map((e, i) => (i === activeIndex ? { ...e, [key]: value } : e));
    });
  }

  function validate(entry: CertificationEntry): boolean {
    const next: typeof errors = {};
    if (!entry.name.trim()) next.name = "Required";
    if (!entry.issuer.trim()) next.issuer = "Required";
    if (!entry.issueDate) next.issueDate = "Required";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onContinue() {
    if (!draftId) return;
    if (!validate(active)) return;
    saveCertifications(draftId, list);
    navigate(`/onboarding/languages/${draftId}`);
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
          tip="Certifications validate your expertise and help you stand out to recruiters."
          progressPercent={75}
          completedThrough={3}
          steps={PROFILE_FLOW_STEPS}
          title="You're almost there!"
          subtitle="Complete your profile to unlock better job matches."
        />
      }
    >
      <OnboardingStepper activeIndex={4} steps={PROFILE_FLOW_STEPS} />

      <div className="mt-5 flex min-h-0 flex-1 flex-col">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">Add your certifications</h1>
        <p className="mt-1 text-sm text-slate-500">
          Include professional certificates, licenses, and completed training.
        </p>

        {list.length > 1 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {list.map((e, i) => (
              <button
                key={e.id}
                type="button"
                onClick={() => {
                  setActiveIndex(i);
                  setErrors({});
                }}
                className={`cursor-pointer rounded-lg px-3 py-1 text-xs font-medium ${
                  i === activeIndex ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                }`}
              >
                Cert {i + 1}
              </button>
            ))}
          </div>
        ) : null}

        <div className="mt-5 space-y-4 overflow-y-auto">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1.5 block font-medium text-slate-700">
                Certification name <RequiredMark />
              </span>
              <input
                className={fieldClass}
                placeholder="e.g. Microsoft Power BI Data Analyst"
                value={active.name}
                onChange={(e) => setField("name", e.target.value)}
              />
              {errors.name ? <p className="mt-1 text-xs text-danger-600">{errors.name}</p> : null}
            </label>

            <label className="block text-sm">
              <span className="mb-1.5 block font-medium text-slate-700">
                Issuing organization <RequiredMark />
              </span>
              <input
                className={fieldClass}
                placeholder="e.g. Microsoft"
                value={active.issuer}
                onChange={(e) => setField("issuer", e.target.value)}
              />
              {errors.issuer ? <p className="mt-1 text-xs text-danger-600">{errors.issuer}</p> : null}
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1.5 block font-medium text-slate-700">
                Issue date <RequiredMark />
              </span>
              <input
                type="month"
                className={fieldClass}
                value={active.issueDate}
                onChange={(e) => setField("issueDate", e.target.value)}
              />
              {errors.issueDate ? <p className="mt-1 text-xs text-danger-600">{errors.issueDate}</p> : null}
            </label>

            <div>
              <label className="block text-sm">
                <span className="mb-1.5 block font-medium text-slate-700">Expiration date</span>
                <input
                  type="month"
                  className={fieldClass}
                  value={active.expirationDate}
                  disabled={active.doesNotExpire}
                  onChange={(e) => setField("expirationDate", e.target.value)}
                />
                {errors.expirationDate ? (
                  <p className="mt-1 text-xs text-danger-600">{errors.expirationDate}</p>
                ) : null}
              </label>
              <label className="mt-2 flex items-center gap-2 text-sm font-medium text-slate-700">
                <input
                  type="checkbox"
                  className="size-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
                  checked={active.doesNotExpire}
                  onChange={(e) => {
                    setField("doesNotExpire", e.target.checked);
                    if (e.target.checked) setField("expirationDate", "");
                  }}
                />
                This credential does not expire
              </label>
            </div>
          </div>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Credential ID</span>
            <input
              className={fieldClass}
              placeholder="Enter credential ID"
              value={active.credentialId}
              onChange={(e) => setField("credentialId", e.target.value)}
            />
          </label>

          <label className="block text-sm">
            <span className="mb-1.5 block font-medium text-slate-700">Credential URL</span>
            <input
              type="url"
              className={fieldClass}
              placeholder="https://"
              value={active.credentialUrl}
              onChange={(e) => setField("credentialUrl", e.target.value)}
            />
          </label>
        </div>

        <button
          type="button"
          onClick={() => {
            setEntries((prev) => [...(prev ?? initial), emptyCertification()]);
            setActiveIndex(list.length);
            setErrors({});
          }}
          className="mt-4 inline-flex cursor-pointer items-center gap-2 self-start rounded-xl border border-brand-600 px-4 py-2.5 text-sm font-semibold text-brand-600 hover:bg-brand-50"
        >
          <span aria-hidden="true">+</span>
          Add another certification
        </button>

        <div className="mt-auto pt-6">
          <OnboardingNav
            onBack={() => navigate(`/onboarding/skills/${draftId}`)}
            onContinue={onContinue}
          />
          <OnboardingSecurityNote />
        </div>
      </div>
    </OnboardingFrame>
  );
}
