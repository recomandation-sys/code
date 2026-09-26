import { Link } from "react-router-dom";

import { Button } from "../../../components/Button.js";
import { EmptyState } from "../../../components/EmptyState.js";
import { PageHeader } from "../../../components/PageHeader.js";

export function MyJobsPage() {
  return (
    <div className="jl-fade-up">
      <PageHeader title="My jobs" description="Roles you’ve liked or applied to from JOBLIK." />
      <EmptyState
        title="Nothing saved yet"
        description="Like or apply from your recommendations — they’ll show up here."
        action={
          <Link to="/jobs">
            <Button className="font-semibold">Go to jobs</Button>
          </Link>
        }
      />
    </div>
  );
}
