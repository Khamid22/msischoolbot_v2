// Pure gradebook formatting helpers shared by the admin gradebook panels.
// Extracted verbatim from AcademicPanel/GradebookPanel to remove duplication;
// behavior is unchanged.

export function scoreOutOfNine(value: unknown) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return 0;
  return Math.max(0, Math.min(9, Math.round(parsed * 10) / 10));
}

export function formatScoreOutOfNine(value: unknown) {
  const score = scoreOutOfNine(value);
  return score > 0 ? score.toFixed(score % 1 === 0 ? 0 : 1) : "—";
}

export function attLabel(v: string) {
  if (v === "present") return "P";
  if (v === "absent") return "A";
  if (v === "justified") return "J";
  return "";
}

export function attCls(v: string) {
  if (v === "present") return "bg-emerald-500 text-white";
  if (v === "absent") return "bg-red-500 text-white";
  if (v === "justified") return "bg-amber-400 text-white";
  return "";
}
