import { Link } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { EmptyState } from "../../../components/EmptyState.js";
import { PageHeader } from "../../../components/PageHeader.js";

export function SkillsGapPage() {
  return (
    <div className="jl-fade-up">
      <PageHeader
        title="Skills gap"
        description="Missing skills for your target roles — based on your CV and preferences."
      />
      <EmptyState
        title="No skill gaps to show"
        description="Once your profile and target roles are set, we’ll show skills to learn next."
        action={
          <Link to="/onboarding/upload-cv">
            <Button className="font-semibold">Upload your CV</Button>
          </Link>
        }
      />
    </div>
  );
}
