/**
 * Canonical status → tone mapping for StatusBadge. Pure module (no React /
 * .tsx imports) so node:test can exercise it directly. Tone names mirror
 * BadgeTone in Badge.tsx.
 */
export type StatusTone = "neutral" | "success" | "warning" | "danger" | "info";

export type KnownStatus =
  | "active"
  | "in_training"
  | "in_academy"
  | "ready"
  | "completed"
  | "needs_support"
  | "scheduled"
  | "assigned"
  | "assessed"
  | "draft"
  | "published"
  | "missing";

export const statusToneMap: Record<KnownStatus, StatusTone> = {
  active: "success",
  in_training: "info",
  in_academy: "info",
  ready: "success",
  completed: "success",
  needs_support: "warning",
  scheduled: "info",
  assigned: "neutral",
  assessed: "success",
  draft: "neutral",
  published: "success",
  missing: "danger",
};

const statusLabels: Record<KnownStatus, string> = {
  active: "Active",
  in_training: "In Training",
  in_academy: "In Academy",
  ready: "Ready",
  completed: "Completed",
  needs_support: "Needs Support",
  scheduled: "Scheduled",
  assigned: "Assigned",
  assessed: "Assessed",
  draft: "Draft",
  published: "Published",
  missing: "Missing",
};

/** "In Training" / "in-training" / "IN_TRAINING" → "in_training". */
export function normalizeStatus(status: string): string {
  return String(status || "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
}

export function statusTone(status: string): StatusTone {
  const key = normalizeStatus(status) as KnownStatus;
  return statusToneMap[key] || "neutral";
}

export function statusLabel(status: string): string {
  const key = normalizeStatus(status) as KnownStatus;
  return statusLabels[key] || String(status || "").trim();
}
