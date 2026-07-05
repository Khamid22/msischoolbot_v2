const PREVIEW_ROLE_KEY = "devPreviewRole";
const LEGACY_ADMIN_MODE_KEY = "msi_admin_mode";
const TEACHER_PREVIEW_KEY = "msi_teacher_preview_key";
const LEGACY_TEACHER_PREVIEW_ID_KEY = "msi_teacher_preview_id";

export const staleRolePreviewStorageKeys = [
  PREVIEW_ROLE_KEY,
  LEGACY_ADMIN_MODE_KEY,
  TEACHER_PREVIEW_KEY,
  LEGACY_TEACHER_PREVIEW_ID_KEY,
] as const;

function normalizeRole(value: unknown) {
  return String(value || "").trim().toLowerCase().replace(/-/g, "_");
}

export function canUseAdminPreviewForRole(role: unknown) {
  const normalized = normalizeRole(role);
  return normalized === "admin" || normalized === "system_admin";
}

export function clearStaleRolePreviewStorage(role: unknown) {
  if (canUseAdminPreviewForRole(role) || typeof window === "undefined") {
    return;
  }
  try {
    staleRolePreviewStorageKeys.forEach((key) => window.localStorage.removeItem(key));
  } catch {
    /* Ignore storage access errors in private/embedded browsers. */
  }
}
