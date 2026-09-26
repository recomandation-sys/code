import { Controller, useFormContext } from "react-hook-form";

import { Card, CardHeader } from "../../../components/Card.js";
import { ChipList } from "../../../components/ChipList.js";
import type { ReviewFormValues } from "../../../schemas/review-form.schema.js";

export function TargetPositionsSection() {
  const {
    control,
    formState: { errors },
  } = useFormContext<ReviewFormValues>();

  return (
    <Card>
      <CardHeader title="2. Target positions" description="At least one desired position is required." />
      <Controller
        name="positions"
        control={control}
        render={({ field }) => (
          <ChipList
            label="Target positions"
            items={field.value}
            onAdd={(value) => field.onChange([...field.value, value])}
            onRemove={(index) => field.onChange(field.value.filter((_, i) => i !== index))}
            placeholder="e.g. Backend Developer"
          />
        )}
      />
      {errors.positions ? <p className="mt-2 text-xs text-red-600">{errors.positions.message}</p> : null}
    </Card>
  );
}
