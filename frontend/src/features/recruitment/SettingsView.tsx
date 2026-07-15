import { Link2, Loader2, Plus, Tags, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import type { RecruitmentSetting, RecruitmentSettingsData } from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, buttonClass, fieldClass, queryError } from "@/features/recruitment/ui";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";

type SettingCategory = "source" | "rejection_reason";
type MutationPayload = { message: string; setting: RecruitmentSetting };

function SettingsPanel({
  title,
  detail,
  icon,
  category,
  items,
  busy,
  onAdd,
  onRemove,
}: {
  title: string;
  detail: string;
  icon: ReactNode;
  category: SettingCategory;
  items: RecruitmentSetting[];
  busy: boolean;
  onAdd: (category: SettingCategory, label: string) => void;
  onRemove: (setting: RecruitmentSetting) => void;
}) {
  const [label, setLabel] = useState("");
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = label.trim();
    if (!normalized) return;
    onAdd(category, normalized);
    setLabel("");
  };
  return (
    <section className="rounded-xl border border-border bg-card p-3 shadow-sm">
      <div className="flex items-start gap-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">{icon}</span>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{detail}</p>
        </div>
      </div>
      <form onSubmit={submit} className="mt-3 flex gap-2">
        <label className="min-w-0 flex-1">
          <span className="sr-only">New {title.toLowerCase()}</span>
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            maxLength={120}
            placeholder={`Add ${title.toLowerCase()}`}
            className={fieldClass}
          />
        </label>
        <button type="submit" className={buttonClass} disabled={busy || !label.trim()}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          <span className="hidden sm:inline">Add</span>
        </button>
      </form>
      <div className="mt-3 divide-y divide-border overflow-hidden rounded-lg border border-border">
        {items.map((item) => (
          <div key={item.id} className="flex min-h-12 items-center justify-between gap-2 px-3 py-1.5">
            <span className="min-w-0 truncate text-[13px] font-medium text-foreground">{item.label}</span>
            <button
              type="button"
              onClick={() => onRemove(item)}
              disabled={busy}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/30 disabled:opacity-50"
              aria-label={`Remove ${item.label}`}
              title={`Remove ${item.label}`}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
      {!items.length ? <div className="mt-3"><EmptyLine>No active options.</EmptyLine></div> : null}
    </section>
  );
}

export function SettingsView({ onAnnouncement }: { onAnnouncement: (message: string) => void }) {
  const queryClient = useQueryClient();
  const [removeSetting, setRemoveSetting] = useState<RecruitmentSetting | null>(null);
  const settings = useQuery({
    queryKey: ["recruitment", "settings"],
    queryFn: () => recruitmentRequest<RecruitmentSettingsData>(`${RECRUITMENT_API}/settings`),
  });
  const mutation = useMutation({
    mutationFn: ({ method, url, body }: { method: "POST" | "DELETE"; url: string; body?: unknown }) =>
      recruitmentRequest<MutationPayload>(url, { method, body: body ? jsonBody(body) : undefined }),
    onSuccess: (result) => {
      onAnnouncement(result.message);
      setRemoveSetting(null);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "settings"] });
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "options"] });
    },
    onError: (error) => onAnnouncement(queryError(error)),
  });

  if (settings.isLoading) return <PageState>Loading recruitment settings…</PageState>;
  if (settings.error || !settings.data) return <PageState tone="error">{queryError(settings.error)}</PageState>;

  const add = (category: SettingCategory, label: string) => mutation.mutate({
    method: "POST",
    url: `${RECRUITMENT_API}/settings`,
    body: { category, label },
  });

  return (
    <>
      <div className="grid gap-3 lg:grid-cols-2">
        <SettingsPanel
          title="Candidate sources"
          detail="Shown when HR creates or filters candidates. Existing candidate values remain unchanged."
          icon={<Link2 className="h-4 w-4" />}
          category="source"
          items={settings.data.sources}
          busy={mutation.isPending}
          onAdd={add}
          onRemove={setRemoveSetting}
        />
        <SettingsPanel
          title="Rejection reasons"
          detail="Used by Academic Director and CEO decisions. Removing an option keeps historical records."
          icon={<Tags className="h-4 w-4" />}
          category="rejection_reason"
          items={settings.data.rejection_reasons}
          busy={mutation.isPending}
          onAdd={add}
          onRemove={setRemoveSetting}
        />
      </div>
      <ConfirmDialog
        open={Boolean(removeSetting)}
        title="Remove this option?"
        message={<>Remove <strong>{removeSetting?.label}</strong> from future recruitment forms. Existing records will remain intact.</>}
        confirmLabel="Remove"
        danger
        busy={mutation.isPending}
        onCancel={() => setRemoveSetting(null)}
        onConfirm={() => {
          if (removeSetting) mutation.mutate({
            method: "DELETE",
            url: `${RECRUITMENT_API}/settings/${removeSetting.id}`,
          });
        }}
      />
    </>
  );
}
