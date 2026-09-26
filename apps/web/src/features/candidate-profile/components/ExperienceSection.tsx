import { useFieldArray, useFormContext } from "react-hook-form";
import { EXPERIENCE_TYPES, type CandidateDraft, type ExperienceType } from "@job-recommender/contracts";

import { Button } from "../../../components/Button.js";
import { Card, CardHeader } from "../../../components/Card.js";
import { formatMonths } from "../../../utils/format-duration.js";
import type { ReviewFormValues } from "../../../schemas/review-form.schema.js";

const TYPE_LABELS: Record<ExperienceType, string> = {
  PROFESSIONAL: "Professional",
  INTERNSHIP: "Internship",
  ALTERNANCE: "Alternance",
  FREELANCE: "Freelance",
  UNKNOWN: "Other",
};

function emptyRecord() {
  const currentYear = new Date().getFullYear();
  return {
    id: crypto.randomUUID(),
    type: "PROFESSIONAL" as ExperienceType,
    title: "",
    startYear: currentYear,
    startMonth: null,
    endYear: currentYear,
    endMonth: null,
    isCurrent: false,
    technologies: [],
  };
}

export function ExperienceSection({ draft }: { draft: CandidateDraft }) {
  const {
    control,
    register,
    watch,
    formState: { errors },
  } = useFormContext<ReviewFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: "experience" });

  return (
    <Card>
      <CardHeader title="4. Experience" description="Totals are informational — the final duration is recomputed on save." />

      <dl className="mb-5 grid grid-cols-2 gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Professional</dt>
          <dd className="font-medium text-slate-800">{formatMonths(draft.experience.professionalMonths)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Internships</dt>
          <dd className="font-medium text-slate-800">{formatMonths(draft.experience.internshipMonths)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Alternance</dt>
          <dd className="font-medium text-slate-800">{formatMonths(draft.experience.alternanceMonths)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Freelance</dt>
          <dd className="font-medium text-slate-800">{formatMonths(draft.experience.freelanceMonths)}</dd>
        </div>
      </dl>

      <div className="space-y-4">
        {fields.map((field, index) => {
          const isCurrent = watch(`experience.${index}.isCurrent`);
          return (
            <div key={field.id} className="rounded-xl border border-slate-200 p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-500">Type</span>
                  <select
                    {...register(`experience.${index}.type`)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  >
                    {EXPERIENCE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {TYPE_LABELS[type]}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-500">Title</span>
                  <input
                    {...register(`experience.${index}.title`)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </label>

                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-500">Start year</span>
                  <input
                    type="number"
                    {...register(`experience.${index}.startYear`, { valueAsNumber: true })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-500">Start month</span>
                  <input
                    type="number"
                    min={1}
                    max={12}
                    {...register(`experience.${index}.startMonth`, { valueAsNumber: true })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </label>

                {!isCurrent && (
                  <>
                    <label className="block">
                      <span className="mb-1 block text-xs font-medium text-slate-500">End year</span>
                      <input
                        type="number"
                        {...register(`experience.${index}.endYear`, { valueAsNumber: true })}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      />
                    </label>
                    <label className="block">
                      <span className="mb-1 block text-xs font-medium text-slate-500">End month</span>
                      <input
                        type="number"
                        min={1}
                        max={12}
                        {...register(`experience.${index}.endMonth`, { valueAsNumber: true })}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      />
                    </label>
                  </>
                )}
              </div>

              <div className="mt-3 flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" {...register(`experience.${index}.isCurrent`)} className="h-4 w-4 rounded border-slate-300" />
                  I currently work here
                </label>
                <Button type="button" variant="danger" onClick={() => remove(index)}>
                  Delete
                </Button>
              </div>
              {errors.experience?.[index]?.endYear ? (
                <p className="mt-2 text-xs text-red-600">{errors.experience[index]?.endYear?.message}</p>
              ) : null}
            </div>
          );
        })}
      </div>

      <Button type="button" variant="secondary" className="mt-4" onClick={() => append(emptyRecord())}>
        + Add experience
      </Button>
    </Card>
  );
}
