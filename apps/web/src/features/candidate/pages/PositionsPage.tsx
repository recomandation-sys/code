import { Link } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { EmptyState } from "../../../components/EmptyState.js";
import { PageHeader } from "../../../components/PageHeader.js";

export function PositionsPage() {
  return (
    <div className="jl-fade-up">
      <PageHeader
        title="Suitable positions"
        description="Job titles scored against your experience and skills."
      />
      <EmptyState
        title="Positions unlock after your profile"
        description="Complete CV onboarding so we can suggest titles that fit your background."
        action={
          <Link to="/onboarding/upload-cv">
            <Button className="font-semibold">Build your profile</Button>
          </Link>
        }
      />
    </div>
  );
}
