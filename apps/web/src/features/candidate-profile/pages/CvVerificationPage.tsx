import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { ApiClientError } from "../../../api/client.js";
import {
  OnboardingFrame,
  OnboardingNav,
  OnboardingSecurityNote,
  OnboardingSidebar,
  OnboardingStepper,
} from "../components/OnboardingChrome.js";
import { useCandidateDraft } from "../hooks/useCandidateDraft.js";
import { seedWizardFromDraft } from "../utils/wizard-storage.js";

type LocationState = {
  fileName?: string;
};

const RING_SIZE = 148;
const RING_R = (RING_SIZE - 12) / 2;
const RING_C = 2 * Math.PI * RING_R;

function ReadingRing({ percent }: { percent: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(percent)));
  const offset = RING_C - (pct / 100) * RING_C;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: RING_SIZE, height: RING_SIZE }}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Reading progress ${pct} percent`}
    >
      <svg width={RING_SIZE} height={RING_SIZE} className="-rotate-90" aria-hidden="true">
        <circle
          cx={RING_SIZE / 2}
          cy={RING_SIZE / 2}
          r={RING_R}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="10"
        />
        <circle
          cx={RING_SIZE / 2}
          cy={RING_SIZE / 2}
          r={RING_R}
          fill="none"
          stroke="#0070fd"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={RING_C}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-300 ease-out"
        />
      </svg>
      <span className="absolute text-3xl font-bold tracking-tight text-brand-600 tabular-nums">{pct}%</span>
    </div>
  );
}

export function CvVerificationPage() {
  const navigate = useNavigate();
  const { draftId } = useParams<{ draftId: string }>();
  const location = useLocation();
  const fileName = (location.state as LocationState | null)?.fileName ?? "your-cv.pdf";
  const { data: draft, isLoading, isError, error } = useCandidateDraft(draftId);
  const ready = !isLoading && !!draft && !isError;
  const [pct, setPct] = useState(0);

  // ponytail: cosmetic progress while draft loads; real % would need parser streaming
  useEffect(() => {
    if (ready) {
      setPct(100);
      return;
    }
    if (isError) return;
    const id = window.setInterval(() => {
      setPct((p) => (p >= 92 ? p : p + 1 + Math.floor(Math.random() * 2)));
    }, 80);
    return () => window.clearInterval(id);
  }, [ready, isError]);

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

  function onContinue() {
    if (draft) seedWizardFromDraft(draft);
    navigate(`/onboarding/personal-info/${draftId}`);
  }

  const statusText = isError
    ? "Something went wrong"
    : ready
      ? "CV ready — continue when you are"
      : "Reading your CV…";

  return (
    <OnboardingFrame
      sidebar={
        <OnboardingSidebar
          heroSrc="/cv-check-hero.png"
          tip="An ATS-friendly CV helps recruiters find your skills and experience faster."
          progressPercent={0}
          completedThrough={0}
        />
      }
    >
      <OnboardingStepper activeIndex={0} />

      <div className="jl-fade-up mt-5 flex flex-1 flex-col items-center justify-center text-center">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">Analyzing your CV</h1>
        <p className="mt-2 max-w-sm text-sm text-slate-500">
          We&apos;re extracting your details so the next steps are already filled in.
        </p>

        <div className="mt-5 inline-flex max-w-full items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
          <span className="inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-red-50 text-[10px] font-bold text-red-600">
            PDF
          </span>
          <span className="truncate text-sm font-medium text-slate-800">{fileName}</span>
        </div>

        <div className="relative mt-8">
          {!ready && !isError ? (
            <span
              className="pointer-events-none absolute inset-[-10px] rounded-full border-2 border-brand-200/60 border-t-brand-500 animate-spin"
              aria-hidden="true"
            />
          ) : null}
          <ReadingRing percent={pct} />
        </div>

        <p
          className={`mt-6 text-base font-medium text-brand-600 ${!ready && !isError ? "animate-pulse" : ""}`}
          role="status"
          aria-live="polite"
        >
          {statusText}
        </p>

        {isError ? (
          <p className="mt-3 max-w-md text-sm text-danger-600">
            {error instanceof ApiClientError ? error.message : "Could not load parsed CV data."}
          </p>
        ) : null}
      </div>

      <OnboardingNav
        onBack={() => navigate("/onboarding/upload-cv")}
        onContinue={onContinue}
        continueDisabled={isLoading || !draft}
      />
      <OnboardingSecurityNote />
    </OnboardingFrame>
  );
}
