import { useState } from "react";

interface ChipListProps {
  label: string;
  items: string[];
  onAdd: (value: string) => void;
  onRemove: (index: number) => void;
  placeholder?: string;
}

/** Editable list of free-text chips (section 19 target positions, section 23 custom skills). */
export function ChipList({ label, items, onAdd, onRemove, placeholder }: ChipListProps) {
  const [draft, setDraft] = useState("");

  function commit() {
    const value = draft.trim();
    if (value.length > 0) {
      onAdd(value);
      setDraft("");
    }
  }

  return (
    <div>
      <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      <ul className="mb-2 flex flex-wrap gap-2">
        {items.map((item, index) => (
          <li
            key={`${item}-${index}`}
            className="flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-700"
          >
            {item}
            <button
              type="button"
              aria-label={`Remove ${item}`}
              onClick={() => onRemove(index)}
              className="rounded-full text-brand-500 hover:text-brand-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      <div className="flex gap-2">
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            }
          }}
          placeholder={placeholder}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        <button
          type="button"
          onClick={commit}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          Add
        </button>
      </div>
    </div>
  );
}
