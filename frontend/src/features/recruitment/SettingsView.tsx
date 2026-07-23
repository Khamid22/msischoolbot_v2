import {
  BellRing,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  Clock3,
  Link2,
  Loader2,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  ShieldAlert,
  Tags,
  Trash2,
  UsersRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";

import { jsonBody, recruitmentRequest } from "@/features/recruitment/api";
import { humanize, type RecruitmentSetting, type RecruitmentSettingsData } from "@/features/recruitment/model";
import { RECRUITMENT_API, EmptyLine, PageState, buttonClass, fieldClass, queryError } from "@/features/recruitment/ui";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";

type SettingCategory = RecruitmentSetting["category"];
type MutationPayload = { message: string; setting: RecruitmentSetting };

function SettingsSectionHeading({
  id,
  title,
  detail,
  icon: Icon,
}: {
  id: string;
  title: string;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <div className="mb-3 flex items-start gap-2.5">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <h2 id={id} className="text-base font-bold tracking-tight text-foreground">
          {title}
        </h2>
        <p className="mt-0.5 max-w-3xl text-[0.8125rem] leading-5 text-muted-foreground">
          {detail}
        </p>
      </div>
    </div>
  );
}

function AppointmentReminderSettings({
  leadMinutes,
  version,
  readOnly,
  busy,
  onSave,
}: {
  leadMinutes: number;
  version: number;
  readOnly: boolean;
  busy: boolean;
  onSave: (leadMinutes: number, version: number) => void;
}) {
  const [draft, setDraft] = useState(String(leadMinutes));
  return (
    <section className="rounded-xl border border-border bg-card shadow-sm">
      <div className="border-b border-border px-4 py-3">
        <h3 className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-muted-foreground">
          Appointment reminder
        </h3>
        <p className="mt-1 text-[0.8125rem] leading-5 text-foreground">
          One browser alert before every scheduled interview or demo.
        </p>
      </div>
      <div className="p-4">
        <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(event) => {
          event.preventDefault();
          const value = Number(draft);
          if (!Number.isInteger(value) || value < 5 || value > 120 || value === leadMinutes) return;
          onSave(value, version);
        }}>
          <label className="min-w-0 flex-1 text-xs font-semibold">
            Remind before session
            <span className="mt-1 flex items-center gap-2">
              <input
                type="number"
                min={5}
                max={120}
                inputMode="numeric"
                value={draft}
                disabled={readOnly || busy}
                onChange={(event) => setDraft(event.target.value)}
                className={`${fieldClass} min-h-11 min-w-0`}
                aria-describedby="reminder-minutes-help"
              />
              <span className="shrink-0 text-xs font-medium text-muted-foreground">
                minutes
              </span>
            </span>
          </label>
          {!readOnly ? (
            <button
              type="submit"
              className={`${buttonClass} min-h-11 sm:min-w-24`}
              disabled={
                busy ||
                Number(draft) === leadMinutes ||
                Number(draft) < 5 ||
                Number(draft) > 120
              }
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              Save
            </button>
          ) : null}
        </form>
        <p id="reminder-minutes-help" className="mt-2 text-xs leading-5 text-muted-foreground">
          Range 5–120 minutes. Short-notice appointments created inside this
          window skip the reminder.
        </p>
        {readOnly ? (
          <p className="mt-2 inline-flex rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground">
            Read-only CEO view
          </p>
        ) : null}
      </div>
    </section>
  );
}

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
    <div
      key={item.id}
      className="grid min-h-14 grid-cols-[minmax(0,1fr)_auto] items-center gap-2 px-4 py-2 transition-colors duration-150 hover:bg-muted/25 motion-reduce:transition-none"
    >
      {renamingId === item.id ? (
        <form
          className="col-span-2 flex min-w-0 items-center gap-1.5"
          onSubmit={(event) => {
            event.preventDefault();
            commitRename(item);
          }}
        >
          <label className="min-w-0 flex-1">
            <span className="sr-only">Option name</span>
            <input
              autoFocus
              value={renameDraft}
              onChange={(event) => setRenameDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape") cancelRename();
              }}
              maxLength={120}
              className={`${fieldClass} min-h-11 flex-1`}
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-emerald-700 transition-colors hover:bg-emerald-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 disabled:opacity-50 motion-reduce:transition-none dark:text-emerald-300"
            aria-label="Save name"
          >
            <Check className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={cancelRename}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none"
            aria-label="Cancel rename"
          >
            <X className="h-4 w-4" />
          </button>
        </form>
      ) : (
        <>
          <div className="min-w-0">
            <p className="flex min-w-0 flex-wrap items-center gap-1.5 text-[0.8125rem] font-semibold text-foreground">
              <span className="min-w-0 break-words">{item.label}</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              <span className="inline-flex rounded-full bg-muted/80 px-2 py-0.5 font-medium tabular-nums">
                {item.usage_count || 0} candidate
                {item.usage_count === 1 ? "" : "s"}
              </span>
            </p>
          </div>
          {!readOnly ? (
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={() => startRename(item)}
                disabled={busy}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50 motion-reduce:transition-none"
                aria-label={`Rename ${item.label}`}
                title={`Rename ${item.label}`}
              >
                <Pencil className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => onRemove(item)}
                disabled={busy}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/30 disabled:opacity-50 motion-reduce:transition-none"
                aria-label={`Remove ${item.label}`}
                title={`Remove ${item.label}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );

  return (
    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-start gap-2.5 border-b border-border px-4 py-3.5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-foreground">{title}</h3>
            <span className="rounded-full bg-muted px-2 py-1 text-[0.6875rem] font-semibold tabular-nums text-muted-foreground">
              {activeItems.length} active
            </span>
          </div>
          <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{detail}</p>
        </div>
      </div>
      {activeItems.length > 8 ? (
        <label className="block border-b border-border px-4 py-3 text-xs font-semibold">
          Search
          <span className="relative mt-1 block">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={`Search ${title.toLowerCase()}`}
              className={`${fieldClass} min-h-11 pl-9`}
            />
          </span>
        </label>
      ) : null}
      <div
        className={`hidden border-b border-border bg-muted/35 px-4 py-2 text-[0.6875rem] font-bold uppercase tracking-[0.08em] text-muted-foreground sm:grid ${
          readOnly ? "grid-cols-1" : "grid-cols-[minmax(0,1fr)_7rem]"
        }`}
      >
        <span>{readOnly ? "Option & usage" : "Option"}</span>
        {!readOnly ? <span className="text-right">Actions</span> : null}
      </div>
      {grouped ? (
        <div>
          {grouped.map((group, index) => (
            <div
              key={group.key}
              className={index > 0 ? "border-t border-border" : undefined}
            >
              <div className="bg-muted/40 px-4 py-2 text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground">
                {group.label}
              </div>
              <div className="divide-y divide-border border-t border-border">
                {group.items.map(renderRow)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="divide-y divide-border">{visibleActive.map(renderRow)}</div>
      )}
      {!visibleActive.length ? (
        <div className="p-4">
          <EmptyLine>{normalizedSearch ? "No matches." : "No active options."}</EmptyLine>
        </div>
      ) : null}
      {!readOnly && inactiveItems.length ? (
        <div className="border-t border-border px-4 py-3">
          <button
            type="button"
            className="min-h-11 rounded-lg px-2 text-xs font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none"
            onClick={() => setShowRemoved((value) => !value)}
            aria-expanded={showRemoved}
          >
            {showRemoved ? "Hide removed" : `Show removed (${inactiveItems.length})`}
          </button>
          {showRemoved ? (
            <div className="mt-2 divide-y divide-dashed divide-border overflow-hidden rounded-lg border border-dashed border-border">
              {inactiveItems.map((item) => (
                <div
                  key={item.id}
                  className="flex min-h-14 items-center justify-between gap-2 px-3 py-2"
                >
                  <span className="min-w-0 break-words text-[0.8125rem] text-muted-foreground line-through">
                    {item.label}
                  </span>
                  <button
                    type="button"
                    onClick={() => onRestore(item)}
                    disabled={busy}
                    className="inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold text-primary transition-colors hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50 motion-reduce:transition-none"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Restore
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {!readOnly ? (
        <form
          onSubmit={submit}
          className={`grid gap-2 border-t border-border bg-muted/20 px-4 py-3 ${
            parentItems?.length
              ? "sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
              : "sm:grid-cols-[minmax(0,1fr)_auto]"
          }`}
        >
          {parentItems?.length ? (
            <label className="min-w-0 text-xs font-semibold">
              Source
              <select
                value={parentId}
                onChange={(event) => setParentId(event.target.value)}
                className={`${fieldClass} mt-1 min-h-11`}
                required
              >
                <option value="">Select source</option>
                {parentItems.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label className="min-w-0 text-xs font-semibold">
            New option
            <input
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              maxLength={120}
              placeholder={`Add ${title.toLowerCase()}`}
              className={`${fieldClass} mt-1 min-h-11`}
            />
          </label>
          <button
            type="submit"
            className={`${buttonClass} min-h-11 self-end`}
            disabled={
              busy ||
              !label.trim() ||
              Boolean(parentItems?.length && !parentId)
            }
          >
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Add
          </button>
        </form>
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
  const reminderMutation = useMutation({
    mutationFn: ({ leadMinutes, expectedVersion }: { leadMinutes: number; expectedVersion: number }) =>
      recruitmentRequest<{ message: string; appointment_reminders: unknown }>(`${RECRUITMENT_API}/settings/appointment-reminders`, {
        method: "PATCH",
        body: jsonBody({ lead_minutes: leadMinutes, expected_version: expectedVersion }),
      }),
    onSuccess: (result) => {
      onAnnouncement(result.message || "Appointment reminder timing updated.");
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
    { category: "withdrawal_reason", title: "Withdrawal reasons", detail: "Standard reasons used whenever HR records that a candidate withdrew.", icon: <Tags className="h-4 w-4" /> },
  ];

  const sourceItems = settings.data.items.filter((item) => item.category === "source");
  const activeSourceItems = sourceItems.filter((item) => item.is_active);
  const sourceOrderIds = sourceItems.map((item) => item.id);
  const sourceLabelById = Object.fromEntries(sourceItems.map((item) => [item.id, item.label]));
  const renderPanel = (category: SettingCategory) => {
    const panel = panels.find((item) => item.category === category);
    if (!panel) return null;
    return (
      <SettingsPanel
        key={panel.category}
        {...panel}
        items={settings.data.items.filter(
          (item) => item.category === panel.category,
        )}
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
    );
  };

  return (
    <>
      <div className="space-y-8 pb-4">
        <section aria-labelledby="automation-settings-title">
          <SettingsSectionHeading
            id="automation-settings-title"
            title="Automation & SLAs"
            detail="Define target response times and automated reminders for each recruitment stage."
            icon={BellRing}
          />
          <div className="max-w-lg">
            <AppointmentReminderSettings
              key={`${settings.data.appointment_reminders.version}:${settings.data.appointment_reminders.lead_minutes}`}
              leadMinutes={settings.data.appointment_reminders.lead_minutes}
              version={settings.data.appointment_reminders.version}
              readOnly={settings.data.read_only}
              busy={reminderMutation.isPending}
              onSave={(leadMinutes, expectedVersion) =>
                reminderMutation.mutate({ leadMinutes, expectedVersion })
              }
            />
          </div>
          <section className="mt-3 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            <div className="border-b border-border px-4 py-3">
              <h3 className="text-[0.6875rem] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Stage SLA targets (max days)
              </h3>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Calendar days in Asia/Tashkent. Changes apply only to future
                stage entries.
              </p>
            </div>
            <div className="grid gap-2 p-4 sm:grid-cols-2 xl:grid-cols-5">
              {settings.data.sla_rules.map((rule) => (
                <label
                  key={rule.stage}
                  className="rounded-lg border border-border bg-muted/15 p-2.5 text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground"
                >
                  {rule.stage_label || humanize(rule.stage)}
                  <span className="relative mt-1.5 block">
                    <input
                      type="number"
                      min={1}
                      max={90}
                      inputMode="numeric"
                      defaultValue={rule.target_days}
                      disabled={settings.data.read_only}
                      className={`${fieldClass} min-h-11 min-w-0 pr-14 tabular-nums`}
                      onBlur={(event) => {
                        const target = Number(event.target.value);
                        if (
                          !Number.isFinite(target) ||
                          target === rule.target_days
                        )
                          return;
                        if (target < 1 || target > 90) {
                          event.target.value = String(rule.target_days);
                          return;
                        }
                        const input = event.target;
                        slaMutation.mutate(
                          { stage: rule.stage, target_days: target },
                          {
                            onError: () => {
                              input.value = String(rule.target_days);
                            },
                          },
                        );
                      }}
                    />
                    <span className="pointer-events-none absolute right-3 top-3.5 text-[0.625rem] font-semibold normal-case tracking-normal text-muted-foreground">
                      days
                    </span>
                  </span>
                  <span className="mt-1.5 flex min-h-4 items-center text-[0.625rem] font-medium normal-case tracking-normal">
                    {slaMutation.isPending &&
                    slaMutation.variables?.stage === rule.stage ? (
                      <>
                        <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />
                        Saving…
                      </>
                    ) : savedStage === rule.stage ? (
                      <span className="inline-flex items-center text-emerald-700 dark:text-emerald-300">
                        <Check className="mr-1 h-3.5 w-3.5" />
                        Saved
                      </span>
                    ) : (
                      <span>1–90 days</span>
                    )}
                  </span>
                </label>
              ))}
            </div>
            {settings.data.read_only ? (
              <div className="border-t border-border px-4 py-3">
                <span className="inline-flex rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground">
                  Read-only CEO view
                </span>
              </div>
            ) : null}
          </section>
        </section>

        <section aria-labelledby="candidate-sources-settings-title">
          <SettingsSectionHeading
            id="candidate-sources-settings-title"
            title="Candidate Sources"
            detail="Manage acquisition channels and the universities, referrals, or partners tracked under them."
            icon={UsersRound}
          />
          <div className="grid gap-3 xl:grid-cols-2">
            {renderPanel("source")}
            {renderPanel("subsource")}
          </div>
        </section>

        <section aria-labelledby="candidate-profile-settings-title">
          <SettingsSectionHeading
            id="candidate-profile-settings-title"
            title="Candidate Profile Options"
            detail="Maintain the canonical values used across registration forms, filters, and recruitment analytics."
            icon={BriefcaseBusiness}
          />
          <div className="grid gap-3 lg:grid-cols-2">
            {renderPanel("position")}
            {renderPanel("english_level")}
            {renderPanel("expected_salary")}
            {renderPanel("teaching_experience")}
          </div>
        </section>

        <section aria-labelledby="schedule-availability-settings-title">
          <SettingsSectionHeading
            id="schedule-availability-settings-title"
            title="Schedules & Availability"
            detail="Manage the standard schedule preferences and employment availability choices used during recruitment."
            icon={CalendarDays}
          />
          <div className="grid gap-3 lg:grid-cols-2">
            {renderPanel("schedule")}
            {renderPanel("availability")}
          </div>
        </section>

        <section aria-labelledby="evaluation-settings-title">
          <SettingsSectionHeading
            id="evaluation-settings-title"
            title="Candidate Outcome Reasons"
            detail="Control the database-backed reasons used for rejection and candidate withdrawal without changing historical records."
            icon={ShieldAlert}
          />
          <div className="grid gap-3 lg:grid-cols-2">
            {renderPanel("rejection_reason")}
            {renderPanel("withdrawal_reason")}
          </div>
        </section>
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
