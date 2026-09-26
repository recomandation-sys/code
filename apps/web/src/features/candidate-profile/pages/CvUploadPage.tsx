import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiClientError } from "../../../api/client.js";
import {
  OnboardingFrame,
  OnboardingNav,
  OnboardingSecurityNote,
  OnboardingSidebar,
  OnboardingStepper,
} from "../components/OnboardingChrome.js";
import { useManualDraft } from "../hooks/useManualDraft.js";
import { useParseCv } from "../hooks/useParseCv.js";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

type UploadState = "IDLE" | "FILE_SELECTED" | "UPLOADING" | "SUCCESS" | "ERROR";

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  const isPdfExtension = name.endsWith(".pdf");
  const isPdfMime = file.type === "" || file.type === "application/pdf";
  if (!isPdfExtension || !isPdfMime) {
    return "Please select a valid PDF file.";
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "This file is larger than 10 MB. Please choose a smaller PDF.";
  }
  return null;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CvUploadPage() {
  const navigate = useNavigate();
  const parseCv = useParseCv();
  const manualDraft = useManualDraft();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const state: UploadState = parseCv.isError
    ? "ERROR"
    : parseCv.isPending
      ? "UPLOADING"
      : parseCv.isSuccess
        ? "SUCCESS"
        : file
          ? "FILE_SELECTED"
          : "IDLE";

  function handleFile(selected: File | undefined) {
    if (!selected) return;
    const error = validateFile(selected);
    if (error) {
      setValidationError(error);
      setFile(null);
      return;
    }
    setValidationError(null);
    setFile(selected);
    parseCv.reset();
  }

  function handleUpload() {
    if (!file) return;
    parseCv.mutate(file, {
      onSuccess: (draft) =>
        navigate(`/onboarding/cv-check/${draft.id}`, { state: { fileName: file.name } }),
    });
  }

  function handleManualEntry() {
    manualDraft.mutate(undefined, {
      onSuccess: (draft) => navigate(`/onboarding/personal-info/${draft.id}`),
    });
  }

  function clearFile() {
    setFile(null);
    setValidationError(null);
    parseCv.reset();
    if (inputRef.current) inputRef.current.value = "";
  }

  const parserErrorMessage =
    parseCv.error instanceof ApiClientError ? parseCv.error.message : "We couldn't analyze your CV right now.";

  return (
    <OnboardingFrame
      sidebar={
        <OnboardingSidebar
          heroSrc="/cv-upload-hero.png"
          tip="Uploading your CV lets us pre-fill your profile so recruiters see your skills faster — you stay in control of every field."
          progressPercent={0}
          completedThrough={0}
        />
      }
    >
      <OnboardingStepper activeIndex={0} />

      <div className="mt-5">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">Upload your CV</h1>
        <p className="mt-1 text-sm text-slate-500">
          Add your CV to pre-fill your profile. You can review everything before continuing.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFile(e.dataTransfer.files[0]);
        }}
        className={`mt-4 flex flex-1 flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors sm:py-10 ${
          isDragging ? "border-brand-600 bg-brand-50" : "border-brand-200 bg-slate-50/60"
        }`}
      >
        <div className="mb-3 flex size-12 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
              stroke="currentColor"
              strokeWidth="1.6"
            />
            <path d="M14 3v5h5" stroke="currentColor" strokeWidth="1.6" />
            <text x="8.2" y="17" fill="currentColor" fontSize="5.5" fontWeight="700">
              PDF
            </text>
          </svg>
        </div>
        <p className="text-sm text-slate-600">
          Drag &amp; drop your CV here or{" "}
          <button
            type="button"
            className="cursor-pointer font-semibold text-brand-600 underline-offset-2 hover:underline"
            onClick={() => inputRef.current?.click()}
          >
            browse files
          </button>
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        <p className="mt-2 text-xs text-slate-400">PDF or DOCX · Max 10 MB</p>
      </div>

      {file ? (
        <div className="mt-3 flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5">
          <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-md bg-red-50 text-[10px] font-bold text-red-600">
            PDF
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-800">{file.name}</p>
            <p className="text-xs text-slate-400">PDF · {formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              clearFile();
              inputRef.current?.click();
            }}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M4 20h4l10-10-4-4L4 16v4zM14 6l4 4"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Change
          </button>
        </div>
      ) : null}

      {validationError ? <p className="mt-2 text-sm text-danger-600">{validationError}</p> : null}

      {state === "UPLOADING" ? (
        <p className="mt-2 text-sm text-slate-500" role="status" aria-live="polite">
          Reading your CV…
        </p>
      ) : null}

      {state === "ERROR" ? (
        <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-danger-600">
          <p>{parserErrorMessage}</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => parseCv.reset()}
              className="cursor-pointer rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={handleManualEntry}
              disabled={manualDraft.isPending}
              className="cursor-pointer text-sm font-medium text-brand-600 hover:underline disabled:opacity-60"
            >
              Enter information manually
            </button>
          </div>
        </div>
      ) : null}

      <OnboardingNav
        onBack={() => navigate(-1)}
        onContinue={handleUpload}
        continueDisabled={!file || state === "UPLOADING"}
      />

      {state !== "ERROR" ? (
        <p className="mt-3 text-center text-xs text-slate-400">
          Prefer not to upload?{" "}
          <button
            type="button"
            onClick={handleManualEntry}
            disabled={manualDraft.isPending}
            className="cursor-pointer font-medium text-brand-600 hover:underline disabled:opacity-60"
          >
            Create your profile manually
          </button>
        </p>
      ) : null}

      <OnboardingSecurityNote />
    </OnboardingFrame>
  );
}
