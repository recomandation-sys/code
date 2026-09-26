import { Link } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { EmptyState } from "../../../components/EmptyState.js";
import { PageHeader } from "../../../components/PageHeader.js";

export function JobsPage() {
  return (
    <div className="jl-fade-up">
      <PageHeader
        title="Job recommendations"
        description="Matched from your CV skills and preferences — once your profile is ready."
      />
      <EmptyState
        title="No matches yet"
        description="Upload and confirm your CV so JOBLIK AI can recommend roles from your real profile."
        action={
          <Link to="/onboarding/upload-cv">
            <Button className="font-semibold">Upload your CV</Button>
          </Link>
        }
      />
    </div>
  );
}
