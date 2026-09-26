import { useMemo, useState } from "react";
import { Controller, useFieldArray, useFormContext } from "react-hook-form";
import type { CandidateDraft } from "@job-recommender/contracts";

import { Button } from "../../../components/Button.js";
import { Card, CardHeader } from "../../../components/Card.js";
import { ChipList } from "../../../components/ChipList.js";
import { useSkillSearch } from "../hooks/useSkillSearch.js";
import type { ReviewFormValues } from "../../../schemas/review-form.schema.js";

const EVIDENCE_LABELS: Record<string, string> = {
  SKILLS_SECTION: "Skills section",
  PROFESSIONAL_EXPERIENCE: "Experience",
  INTERNSHIP: "Internship",
  ALTERNANCE: "Alternance",
  PROJECT: "Project",
  CERTIFICATION: "Certification",
  EDUCATION: "Education",
  PROFILE: "Profile",
};

function AddSkillBox({ onSelect }: { onSelect: (skill: { id: string; name: string }) => void }) {
  const [query, setQuery] = useState("");
  const { data: results = [], isFetching } = useSkillSearch(query);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search a skill, e.g. React"
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />
      {query.trim().length > 1 && (
        <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg">
          {isFetching ? <li className="px-3 py-2 text-sm text-slate-400">Searching…</li> : null}
          {!isFetching && results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-slate-400">No canonical skill found.</li>
          ) : null}
          {results.map((skill) => (
            <li key={skill.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(skill);
                  setQuery("");
                }}
                className="block w-full px-3 py-2 text-left text-sm hover:bg-brand-50"
              >
                {skill.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function SkillsSection({ draft }: { draft: CandidateDraft }) {
  const { control, getValues, setValue, watch } = useFormContext<ReviewFormValues>();
  const skills = useFieldArray({ control, name: "skills" });
  const uncertainSkills = useFieldArray({ control, name: "uncertainSkills" });
  const customSkills = watch("customSkills");

  const evidenceById = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const skill of draft.skills.detected) {
      map.set(
        skill.id,
        skill.evidence.map((e) => e.label ?? EVIDENCE_LABELS[e.source] ?? e.source),
      );
    }
    return map;
  }, [draft.skills.detected]);

  return (
    <Card>
      <CardHeader title="5. Skills" description="Remove anything wrong, and add anything missing." />

      <div className="mb-5">
        <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">Detected skills</span>
        {skills.fields.length === 0 ? (
          <p className="text-sm text-slate-400">No skills detected yet.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {skills.fields.map((field, index) => {
              const evidence = evidenceById.get(field.id) ?? [];
              return (
                <li
                  key={field.id}
                  className="group flex flex-col gap-1 rounded-xl bg-brand-50 px-3 py-1.5 text-sm text-brand-700"
                  title={evidence.length > 0 ? `Found in: ${evidence.join(", ")}` : undefined}
                >
                  <span className="flex items-center gap-1.5">
                    {field.name}
                    <button
                      type="button"
                      aria-label={`Remove ${field.name}`}
                      onClick={() => skills.remove(index)}
                      className="text-brand-500 hover:text-brand-800"
                    >
                      ×
                    </button>
                  </span>
                  {evidence.length > 0 ? (
                    <span className="text-[11px] font-normal text-brand-500">Found in: {evidence.join(", ")}</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="mb-5">
        <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">+ Add skill</span>
        <AddSkillBox
          onSelect={(skill) => {
            const exists = getValues("skills").some((s) => s.id === skill.id);
            if (!exists) skills.append(skill);
          }}
        />
      </div>

      {uncertainSkills.fields.length > 0 ? (
        <div className="mb-5">
          <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">Possible technologies</span>
          <ul className="space-y-2">
            {uncertainSkills.fields.map((field, index) => (
              <li key={field.id} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2">
                <span className="text-sm text-slate-700">{field.rawName}</span>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setValue("customSkills", [...customSkills, field.rawName]);
                      uncertainSkills.remove(index);
                    }}
                  >
                    Add as skill
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => uncertainSkills.remove(index)}>
                    Ignore
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <Controller
        name="customSkills"
        control={control}
        render={({ field }) => (
          <ChipList
            label="Custom skills"
            items={field.value}
            onAdd={(value) => field.onChange([...field.value, value])}
            onRemove={(index) => field.onChange(field.value.filter((_, i) => i !== index))}
            placeholder="Add a skill not in our list"
          />
        )}
      />
    </Card>
  );
}
