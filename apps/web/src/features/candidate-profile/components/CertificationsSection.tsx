import { useFieldArray, useFormContext } from "react-hook-form";

import { Button } from "../../../components/Button.js";
import { Card, CardHeader } from "../../../components/Card.js";
import type { ReviewFormValues } from "../../../schemas/review-form.schema.js";

export function CertificationsSection() {
  const {
    control,
    register,
    formState: { errors },
  } = useFormContext<ReviewFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: "certifications" });

  return (
    <Card>
      <CardHeader title="7. Certifications" />
      <div className="space-y-3">
        {fields.map((field, index) => (
          <div key={field.id} className="grid items-start gap-3 sm:grid-cols-[2fr_2fr_1fr_auto]">
            <div>
              <input
                {...register(`certifications.${index}.name`)}
                placeholder="Certification name"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              {errors.certifications?.[index]?.name ? (
                <p className="mt-1 text-xs text-red-600">{errors.certifications[index]?.name?.message}</p>
              ) : null}
            </div>
            <input
              {...register(`certifications.${index}.issuer`)}
              placeholder="Issuer (optional)"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="number"
              {...register(`certifications.${index}.year`, { valueAsNumber: true })}
              placeholder="Year"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <Button type="button" variant="danger" onClick={() => remove(index)}>
              Remove
            </Button>
          </div>
        ))}
      </div>
      <Button
        type="button"
        variant="secondary"
        className="mt-4"
        onClick={() => append({ id: crypto.randomUUID(), name: "", issuer: null, year: null })}
      >
        + Add certification
      </Button>
    </Card>
  );
}
