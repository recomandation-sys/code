import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState.js";

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="jl-fade-up">
      <EmptyState
        title="Job unavailable"
        description={
          id
            ? "This listing isn’t loaded from your live matches yet. Upload your CV to unlock recommendations."
            : "Choose a job from your recommendations when they’re ready."
        }
        action={
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/jobs" className="text-sm font-semibold text-brand-600 hover:underline">
              Back to jobs
            </Link>
            <Link to="/onboarding/upload-cv" className="text-sm font-semibold text-brand-600 hover:underline">
              Upload CV
            </Link>
          </div>
        }
      />
    </div>
  );
}
