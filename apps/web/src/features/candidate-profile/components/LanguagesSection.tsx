import { useFieldArray, useFormContext } from "react-hook-form";
import { LANGUAGE_LEVELS } from "@job-recommender/contracts";

import { Button } from "../../../components/Button.js";
import { Card, CardHeader } from "../../../components/Card.js";
import type { ReviewFormValues } from "../../../schemas/review-form.schema.js";

export function LanguagesSection() {
  const { control, register } = useFormContext<ReviewFormValues>();
  const { fields, append, remove } = useFieldArray({ control, name: "languages" });

  return (
    <Card>
      <CardHeader title="6. Languages" />
      <div className="space-y-3">
        {fields.map((field, index) => (
          <div key={field.id} className="flex items-center gap-3">
            <input
              {...register(`languages.${index}.language`)}
              placeholder="Language"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <select {...register(`languages.${index}.level`)} className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm">
              {LANGUAGE_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
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
        onClick={() => append({ id: crypto.randomUUID(), language: "", level: "UNKNOWN" })}
      >
        + Add language
      </Button>
    </Card>
  );
}
