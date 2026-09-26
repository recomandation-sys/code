/** User-facing "please double check" indicator — never renders raw confidence codes (section 58). */
export function ReviewBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
      <span aria-hidden="true">●</span>
      Please double-check
    </span>
  );
}
