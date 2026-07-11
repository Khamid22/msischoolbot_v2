import { X } from "lucide-react";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { Candidate } from "./shared";

export function CandidateModal({
  csrf,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  csrf: string;
  submitting: boolean;
  error: string;
  onSubmit: (fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    onSubmit(fields);
  }

  const panelRef = useDismissibleLayer<HTMLDivElement>({ onDismiss: onClose });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4" role="dialog" aria-modal="true">
      <div ref={panelRef} className="flex max-h-[88dvh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover">
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="text-sm font-bold">Add Candidate</h3>
            <p className="text-xs text-muted-foreground">Basic details are enough to start the pipeline.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="min-h-0 overflow-y-auto px-4 py-4">
          <input type="hidden" name="csrf_token" value={csrf} />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Full Name
              </span>
              <input
                type="text"
                name="candidate_full_name"
                required
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Subject
              </span>
              <input
                type="text"
                name="candidate_subject"
                placeholder="IGCSE Mathematics A"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Phone
              </span>
              <input
                type="text"
                name="candidate_phone"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Telegram
              </span>
              <input
                type="text"
                name="candidate_telegram"
                placeholder="@username"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Email
              </span>
              <input
                type="email"
                name="candidate_email"
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Source
              </span>
              <input
                type="text"
                name="candidate_source"
                placeholder="Telegram, referral, HH..."
                className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Notes
              </span>
              <textarea
                name="candidate_notes"
                rows={3}
                className="w-full resize-none rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none"
              />
            </label>
          </div>

          {error ? (
            <p className="mt-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p>
          ) : null}

          <div className="mt-5 flex justify-end gap-2 border-t border-foreground/8 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border-2 border-foreground/10 px-4 py-2 text-sm font-bold hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60"
            >
              {submitting ? "Saving..." : "Save Candidate"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
