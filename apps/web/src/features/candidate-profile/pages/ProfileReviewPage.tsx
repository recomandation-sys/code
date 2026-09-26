import { useParams } from "react-router-dom";

import { ApiClientError } from "../../../api/client.js";
import { useCandidateDraft } from "../hooks/useCandidateDraft.js";
import { ReviewForm } from "./ReviewForm.js";

export function ProfileReviewPage() {
  const { draftId } = useParams<{ draftId: string }>();
  const { data: draft, isLoading, isError, error } = useCandidateDraft(draftId);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16 text-center text-sm text-slate-500" role="status" aria-live="polite">
        Loading your draft…
      </div>
    );
  }

  if (isError || !draft) {
    const message = error instanceof ApiClientError ? error.message : "This draft could not be loaded.";
    return (
      <div className="mx-auto max-w-xl px-6 py-16 text-center">
        <p className="text-sm text-red-600">{message}</p>
        <a href="/onboarding/upload-cv" className="mt-4 inline-block text-sm font-medium text-brand-600 underline">
          Upload a CV
        </a>
      </div>
    );
  }

  return <ReviewForm key={draft.id} draft={draft} />;
}
