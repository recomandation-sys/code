import { useFormContext } from "react-hook-form";
import type { CandidateDraft } from "@job-recommender/contracts";

import { Card, CardHeader } from "../../../components/Card.js";
import { ReviewBadge } from "../../../components/ReviewBadge.js";
import type { ReviewFormValues } from "../../../schemas/review-form.schema.js";

export function IdentitySection({ draft }: { draft: CandidateDraft }) {
  const {
    register,
    formState: { errors },
  } = useFormContext<ReviewFormValues>();

  return (
    <Card>
      <CardHeader
        title="1. Personal information"
        description="Contact details and current country are read from your CV when available."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block sm:col-span-2">
          <span className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-700">
            Full name
            {draft.identity.fullName.needsReview ? <ReviewBadge /> : null}
          </span>
          <input
            {...register("identity.fullName")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {errors.identity?.fullName ? (
            <p className="mt-1 text-xs text-red-600">{errors.identity.fullName.message}</p>
          ) : null}
        </label>

        <label className="block">
          <span className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-700">
            Email
            {draft.identity.email.needsReview ? <ReviewBadge /> : null}
          </span>
          <input
            type="email"
            {...register("identity.email")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {errors.identity?.email ? <p className="mt-1 text-xs text-red-600">{errors.identity.email.message}</p> : null}
        </label>

        <label className="block">
          <span className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-700">
            Phone
            {draft.identity.phone.needsReview ? <ReviewBadge /> : null}
          </span>
          <input
            {...register("identity.phone")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>

        <label className="block sm:col-span-2">
          <span className="mb-1 flex items-center gap-2 text-sm font-medium text-slate-700">
            Country (current)
            {draft.identity.country.needsReview ? <ReviewBadge /> : null}
          </span>
          <input
            {...register("identity.country")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>
      </div>
    </Card>
  );
}
