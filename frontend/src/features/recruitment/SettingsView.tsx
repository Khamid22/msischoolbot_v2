import { Check, Clock3, Link2, Loader2, LockKeyhole, Pencil, Plus, RotateCcw, Search, Tags, Trash2, X } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { stageLabels, humanize, type RecruitmentSetting, type RecruitmentSettingsData } from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, buttonClass, fieldClass, queryError } from "@/features/recruitment/ui";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";

type SettingCategory = RecruitmentSetting["category"];
type MutationPayload = { message: string; setting: RecruitmentSetting };

function groupByParent(items: RecruitmentSetting[], parentOrderIds: number[], parentLabelById: Record<number, string>) {
  const buckets = new Map<number, RecruitmentSetting[]>();
  const orphans: RecruitmentSetting[] = [];
  items.forEach((item) => {
    const parentId = item.parent_id;
    if (!parentId) { orphans.push(item); return; }
    if (!buckets.has(parentId)) buckets.set(parentId, []);
    buckets.get(parentId)!.push(item);
  });
  const orderedIds = [...parentOrderIds, ...Array.from(buckets.keys()).filter((id) => !parentOrderIds.includes(id))];
  const groups = orderedIds
    .filter((id) => buckets.has(id))
    .map((parentId) => ({ key: String(parentId), label: parentLabelById[parentId] || "Unknown source", items: buckets.get(parentId)! }));
  if (orphans.length) groups.push({ key: "none", label: "No source", items: orphans });
  return groups;
}

function SettingsPanel({
  title,
  detail,
  icon,
  category,
  items,
  busy,
  readOnly,
  onAdd,
  onRemove,
  onRename,
  onRestore,
  parentItems,
  parentOrderIds,
  parentLabelById,
}: {
  title: string;
  detail: string;
  icon: ReactNode;
  category: SettingCategory;
  items: RecruitmentSetting[];
  busy: boolean;
  readOnly: boolean;
  onAdd: (category: SettingCategory, label: string, parentId?: number) => void;
  onRemove: (setting: RecruitmentSetting) => void;
  onRename: (setting: RecruitmentSetting, label: string) => void;
  onRestore: (setting: RecruitmentSetting) => void;
  parentItems?: RecruitmentSetting[];
  parentOrderIds?: number[];
  parentLabelById?: Record<number, string>;
}) {
  const [label, setLabel] = useState("");
  const [parentId, setParentId] = useState("");
  const [search, setSearch] = useState("");
  const [showRemoved, setShowRemoved] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameDraft, setRenameDraft] = useState("");

  const activeItems = items.filter((item) => item.is_active);
  const inactiveItems = items.filter((item) => !item.is_active);
  const normalizedSearch = search.trim().toLowerCase();
  const visibleActive = normalizedSearch ? activeItems.filter((item) => item.label.toLowerCase().includes(normalizedSearch)) : activeItems;
  const grouped = category === "subsource" ? groupByParent(visibleActive, parentOrderIds || [], parentLabelById || {}) : null;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = label.trim();
    if (!normalized) return;
    if (parentItems?.length && !parentId) return;
    onAdd(category, normalized, parentId ? Number(parentId) : undefined);
    setLabel("");
  };

  const startRename = (item: RecruitmentSetting) => { setRenamingId(item.id); setRenameDraft(item.label); };
  const cancelRename = () => { setRenamingId(null); setRenameDraft(""); };
  const commitRename = (item: RecruitmentSetting) => {
    const next = renameDraft.trim();
    if (next && next !== item.label) onRename(item, next);
    cancelRename();
  };

  const renderRow = (item: RecruitmentSetting) => (
    <div key={item.id} className="flex min-h-12 items-center justify-between gap-2 px-3 py-1.5">
      {renamingId === item.id ? (
        <form className="flex min-w-0 flex-1 items-center gap-1" onSubmit={(event) => { event.preventDefault(); commitRename(item); }}>
          <input autoFocus value={renameDraft} onChange={(event) => setRenameDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Escape") cancelRename(); }} maxLength={120} className={`${fieldClass} min-h-9 flex-1 py-1`} />
          <button type="submit" disabled={busy} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-emerald-700 hover:bg-emerald-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 disabled:opacity-50 dark:text-emerald-300" aria-label="Save name"><Check className="h-4 w-4" /></button>
          <button type="button" onClick={cancelRename} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" aria-label="Cancel rename"><X className="h-4 w-4" /></button>
        </form>
      ) : (
        <>
          <span className="min-w-0 truncate text-[13px] font-medium text-foreground">
            {item.label}
            {item.is_system ? <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"><LockKeyhole className="h-3 w-3" />System</span> : null}
            {item.usage_count ? <span className="ml-2 font-normal text-muted-foreground">· {item.usage_count} candidate{item.usage_count === 1 ? "" : "s"}</span> : null}
          </span>
          {!readOnly && !item.is_system ? (
            <div className="flex shrink-0 items-center gap-1">
              <button type="button" onClick={() => startRename(item)} disabled={busy} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50" aria-label={`Rename ${item.label}`} title={`Rename ${item.label}`}><Pencil className="h-4 w-4" /></button>
              <button type="button" onClick={() => onRemove(item)} disabled={busy} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/30 disabled:opacity-50" aria-label={`Remove ${item.label}`} title={`Remove ${item.label}`}><Trash2 className="h-4 w-4" /></button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );

  return (
    <section className="rounded-xl border border-border bg-card p-3 shadow-sm">
      <div className="flex items-start gap-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">{icon}</span>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{detail}</p>
        </div>
      </div>
      {!readOnly ? (
        <form onSubmit={submit} className="mt-3 flex gap-2">
          {parentItems?.length ? <label className="min-w-0 flex-1"><span className="sr-only">Parent source</span><select value={parentId} onChange={(event) => setParentId(event.target.value)} className={fieldClass} required><option value="">Select source</option>{parentItems.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label> : null}
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
          <button type="submit" className={buttonClass} disabled={busy || !label.trim() || Boolean(parentItems?.length && !parentId)}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            <span className="hidden sm:inline">Add</span>
          </button>
        </form>
      ) : null}
      {activeItems.length > 8 ? (
        <div className="relative mt-2">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Search ${title.toLowerCase()}`} className={`${fieldClass} pl-9`} />
        </div>
      ) : null}
      {grouped ? (
        <div className="mt-3 overflow-hidden rounded-lg border border-border">
          {grouped.map((group, index) => (
            <div key={group.key} className={index > 0 ? "border-t border-border" : undefined}>
              <div className="bg-muted/40 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{group.label}</div>
              <div className="divide-y divide-border border-t border-border">{group.items.map(renderRow)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-3 divide-y divide-border overflow-hidden rounded-lg border border-border">{visibleActive.map(renderRow)}</div>
      )}
      {!visibleActive.length ? <div className="mt-3"><EmptyLine>{normalizedSearch ? "No matches." : "No active options."}</EmptyLine></div> : null}
      {!readOnly && inactiveItems.length ? (
        <div className="mt-2">
          <button type="button" className="text-xs font-semibold text-muted-foreground underline-offset-2 hover:underline" onClick={() => setShowRemoved((value) => !value)}>
            {showRemoved ? "Hide removed" : `Show removed (${inactiveItems.length})`}
          </button>
          {showRemoved ? (
            <div className="mt-2 divide-y divide-dashed divide-border overflow-hidden rounded-lg border border-dashed border-border">
              {inactiveItems.map((item) => (
                <div key={item.id} className="flex min-h-12 items-center justify-between gap-2 px-3 py-1.5">
                  <span className="min-w-0 truncate text-[13px] text-muted-foreground line-through">{item.label}</span>
                  <button type="button" onClick={() => onRestore(item)} disabled={busy} className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-lg px-2 text-xs font-semibold text-primary hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50">
                    <RotateCcw className="h-3.5 w-3.5" />Restore
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export function SettingsView({ onAnnouncement }: { onAnnouncement: (message: string, tone?: FloatingToastTone) => void }) {
  const queryClient = useQueryClient();
  const [removeSetting, setRemoveSetting] = useState<RecruitmentSetting | null>(null);
  const [savedStage, setSavedStage] = useState<string | null>(null);
  const settings = useQuery({
    queryKey: ["recruitment", "settings"],
    queryFn: () => recruitmentRequest<RecruitmentSettingsData>(`${RECRUITMENT_API}/settings`),
  });
  const mutation = useMutation({
    mutationFn: ({ method, url, body }: { method: "POST" | "PATCH" | "DELETE"; url: string; body?: unknown }) =>
      recruitmentRequest<MutationPayload>(url, { method, body: body ? jsonBody(body) : undefined }),
    onSuccess: (result) => {
      onAnnouncement(result.message);
      setRemoveSetting(null);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "settings"] });
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "options"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });
  const slaMutation = useMutation({
    mutationFn: ({ stage, target_days }: { stage: string; target_days: number }) =>
      recruitmentRequest<{ message: string; rule: unknown }>(`${RECRUITMENT_API}/settings/sla-rules/${stage}`, { method: "PATCH", body: jsonBody({ target_days }) }),
    onSuccess: (result, variables) => {
      onAnnouncement(result.message || "SLA target updated.");
      setSavedStage(variables.stage);
      window.setTimeout(() => setSavedStage((current) => (current === variables.stage ? null : current)), 2000);
      void queryClient.invalidateQueries({ queryKey: ["recruitment", "settings"] });
    },
    onError: (error) => onAnnouncement(queryError(error), "error"),
  });

  if (settings.isLoading) return <PageState>Loading recruitment settings…</PageState>;
  if (settings.error || !settings.data) return <PageState tone="error">{queryError(settings.error)}</PageState>;

  const add = (category: SettingCategory, label: string, parentId?: number) => mutation.mutate({
    method: "POST",
    url: `${RECRUITMENT_API}/settings`,
    body: { category, label, parent_id: parentId || null },
  });
  const rename = (setting: RecruitmentSetting, label: string) => mutation.mutate({
    method: "PATCH",
    url: `${RECRUITMENT_API}/settings/${setting.id}`,
    body: { label },
  });
  const restore = (setting: RecruitmentSetting) => mutation.mutate({
    method: "POST",
    url: `${RECRUITMENT_API}/settings/${setting.id}/restore`,
  });

  const panels: Array<{ category: SettingCategory; title: string; detail: string; icon: ReactNode }> = [
    { category: "source", title: "Candidate sources", detail: "Stable top-level analytics sources.", icon: <Link2 className="h-4 w-4" /> },
    { category: "subsource", title: "Source details", detail: "Predefined universities, referrals, and channels under a source.", icon: <Link2 className="h-4 w-4" /> },
    { category: "position", title: "Teacher positions", detail: "Canonical teaching positions used by candidate forms, filters, and analytics.", icon: <Tags className="h-4 w-4" /> },
    { category: "english_level", title: "English levels", detail: "Standardized language levels used by filters and analytics.", icon: <Tags className="h-4 w-4" /> },
    { category: "schedule", title: "Schedules", detail: "Preferred teaching schedule options.", icon: <Clock3 className="h-4 w-4" /> },
    { category: "availability", title: "Availability", detail: "Standard employment availability options.", icon: <Clock3 className="h-4 w-4" /> },
    { category: "expected_salary", title: "Expected salary", detail: "Stable salary bands rather than free-form amounts.", icon: <Tags className="h-4 w-4" /> },
    { category: "teaching_experience", title: "Teaching experience", detail: "Comparable experience ranges for reporting.", icon: <Tags className="h-4 w-4" /> },
    { category: "rejection_reason", title: "Rejection reasons", detail: "Historical records remain intact when an option is disabled.", icon: <Tags className="h-4 w-4" /> },
  ];

  const sourceItems = settings.data.items.filter((item) => item.category === "source");
  const activeSourceItems = sourceItems.filter((item) => item.is_active);
  const sourceOrderIds = sourceItems.map((item) => item.id);
  const sourceLabelById = Object.fromEntries(sourceItems.map((item) => [item.id, item.label]));

  return (
    <>
      <section className="mb-3 rounded-xl border border-border bg-card p-3 shadow-sm">
        <div className="flex items-start gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><Clock3 className="h-4 w-4" /></span><div><h2 className="text-sm font-semibold">Stage SLA targets</h2><p className="mt-0.5 text-xs text-muted-foreground">Calendar days in Asia/Tashkent. Changes apply only to future stage entries.</p></div></div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {settings.data.sla_rules.map((rule) => (
            <label key={rule.stage} className="rounded-lg border border-border p-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {stageLabels[rule.stage] || humanize(rule.stage)}
              <div className="mt-1 flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={90}
                  defaultValue={rule.target_days}
                  disabled={settings.data.read_only}
                  className={`${fieldClass} min-w-0`}
                  onBlur={(event) => {
                    const target = Number(event.target.value);
                    if (!Number.isFinite(target) || target === rule.target_days) return;
                    if (target < 1 || target > 90) { event.target.value = String(rule.target_days); return; }
                    const input = event.target;
                    slaMutation.mutate({ stage: rule.stage, target_days: target }, { onError: () => { input.value = String(rule.target_days); } });
                  }}
                />
                <span className="text-xs normal-case">days</span>
                {slaMutation.isPending && slaMutation.variables?.stage === rule.stage ? (
                  <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
                ) : savedStage === rule.stage ? (
                  <Check className="h-3.5 w-3.5 shrink-0 text-emerald-600" aria-label="Saved" />
                ) : null}
              </div>
            </label>
          ))}
        </div>
        {settings.data.read_only ? <p className="mt-2 text-xs text-muted-foreground">Read-only CEO view.</p> : null}
      </section>
      <div className="grid gap-2 lg:grid-cols-2">
        {panels.map((panel) => (
          <SettingsPanel
            key={panel.category}
            {...panel}
            items={settings.data.items.filter((item) => item.category === panel.category)}
            parentItems={panel.category === "subsource" ? activeSourceItems : undefined}
            parentOrderIds={panel.category === "subsource" ? sourceOrderIds : undefined}
            parentLabelById={panel.category === "subsource" ? sourceLabelById : undefined}
            busy={mutation.isPending}
            readOnly={settings.data.read_only}
            onAdd={add}
            onRemove={setRemoveSetting}
            onRename={rename}
            onRestore={restore}
          />
        ))}
      </div>
      <ConfirmDialog
        open={Boolean(removeSetting)}
        title="Remove this option?"
        message={
          <>
            Remove <strong>{removeSetting?.label}</strong> from future recruitment forms.{" "}
            {removeSetting?.usage_count ? <>Used by <strong>{removeSetting.usage_count}</strong> candidate{removeSetting.usage_count === 1 ? "" : "s"}; existing records remain intact.</> : "Existing records will remain intact."}
          </>
        }
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
