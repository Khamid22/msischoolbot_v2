import { AlertTriangle, RefreshCw, X } from "lucide-react";
import type { SupportApiError } from "@/features/customer-support/api";
import { secondaryButton } from "@/features/customer-support/shared/ui";

export type SupportErrorState = {
  error: SupportApiError;
  canReload?: boolean;
};

function errorMessage(state: SupportErrorState) {
  switch (state.error.code) {
    case "school_scope_denied":
      return "This record is outside your assigned schools and has been removed from the current view.";
    case "record_not_found":
      return "This record is no longer available. It has been removed from the current view.";
    case "version_conflict":
      return "This record changed after you opened it. Reload the latest version before trying again.";
    case "active_dependencies":
      return state.error.message || "Active academic groups are blocking this change.";
    default:
      return state.error.message || "The request could not be completed.";
  }
}

export function SupportErrorAlert({
  state,
  onReload,
  onDismiss,
}: {
  state: SupportErrorState | null;
  onReload?: () => void;
  onDismiss: () => void;
}) {
  if (!state) return null;
  const groups = state.error.code === "active_dependencies" ? state.error.details?.groups || [] : [];

  return (
    <div className="rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive" role="alert" aria-live="assertive">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="break-words font-bold">{errorMessage(state)}</p>
          {groups.length ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs font-semibold">
              {groups.map((group, index) => (
                <li key={`${group.group_id || "group"}-${index}`}>
                  {[group.subject_name, group.group_name].filter(Boolean).join(" · ") || "Active group"}
                </li>
              ))}
            </ul>
          ) : null}
          {state.error.code === "version_conflict" && state.canReload && onReload ? (
            <button type="button" className={`${secondaryButton} mt-3`} onClick={onReload}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Reload latest
            </button>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-destructive hover:bg-destructive/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/30"
          aria-label="Dismiss error"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
