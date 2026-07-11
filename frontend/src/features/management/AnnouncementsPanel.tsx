import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  AlertTriangle,
  Megaphone,
  Pencil,
  Pin,
  PinOff,
  Plus,
  Send,
  Sparkles,
  Trash2,
  Users,
} from "lucide-react";
import { ActionMenu, type ActionMenuItem } from "@/shared/ui/ActionMenu";
import { ChartCard } from "@/shared/ui/ChartCard";
import { EmptyState } from "@/shared/ui/EmptyState";
import { IconButton } from "@/shared/ui/IconButton";
import { MetricCard } from "@/shared/ui/MetricCard";
import { Modal } from "@/shared/ui/Modal";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "@/features/managementTypes";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders, csrfHeaders } from "@/shared/lib/api";

type Audience =
  | "all"
  | "students"
  | "parents"
  | "teachers"
  | "year10"
  | "year11"
  | "trainees"
  | "candidates"
  | "staff";
type Priority = "info" | "important" | "urgent";
type Status = "published" | "draft" | "scheduled";

type Announcement = {
  id: number;
  title: string;
  body: string;
  audience: Audience;
  priority: Priority;
  status: Status;
  pinned: boolean;
  author: string;
  views: number;
  createdAt: string;
  updatedAt: string;
  publishedAt: string;
};

const audienceLabels: Record<Audience, string> = {
  all: "Everyone",
  students: "All students",
  parents: "Parents",
  teachers: "Active teachers",
  year10: "Year 10",
  year11: "Year 11",
  trainees: "Trainees",
  candidates: "Candidates",
  staff: "All staff",
};

const priorityLabels: Record<Priority, string> = {
  info: "Info",
  important: "Important",
  urgent: "Urgent",
};

const defaultAudienceOptions: Audience[] = ["all", "students", "parents", "teachers", "year10", "year11"];
const hrAudienceOptions: Audience[] = ["teachers", "trainees", "candidates", "staff"];
const hrAudienceSet = new Set<Audience>(hrAudienceOptions);
const teacherAudienceSet = new Set<Audience>(["all", "teachers", "staff"]);

const hrBroadcastTemplates: Array<{
  key: string;
  label: string;
  summary: string;
  title: string;
  body: string;
  audience: Audience;
  priority: Priority;
}> = [
  {
    key: "interview",
    label: "Interview Reminder",
    summary: "Prompt candidates before an interview day.",
    title: "Interview reminder",
    body:
      "Reminder: your interview is scheduled for tomorrow. Please arrive 10 minutes early and be ready for a short fluency and professionalism check.",
    audience: "candidates",
    priority: "important",
  },
  {
    key: "training",
    label: "Practice Session",
    summary: "Share a lesson practice or observation update.",
    title: "Practice session update",
    body:
      "Please review the lesson plan and be ready for the upcoming practice session. Bring your notebook, teaching materials, and arrive on time.",
    audience: "trainees",
    priority: "important",
  },
  {
    key: "documents",
    label: "Documents Request",
    summary: "Collect missing onboarding or hiring files.",
    title: "Required documents",
    body:
      "Please send the remaining required documents today so we can continue your hiring process without delay.",
    audience: "candidates",
    priority: "urgent",
  },
  {
    key: "staff",
    label: "Staff Notice",
    summary: "Broadcast a policy or staffing update.",
    title: "HR policy update",
    body:
      "Please review the latest HR update and follow the revised process from today onward. Reach out to HR if anything is unclear.",
    audience: "staff",
    priority: "info",
  },
];

type AnnouncementForm = {
  title: string;
  body: string;
  audience: Audience;
  priority: Priority;
  status: Status;
  pinned: boolean;
};

function normalizeAnnouncement(row: Record<string, unknown>): Announcement {
  const audience = asString(row.audience) as Audience;
  const priority = asString(row.priority) as Priority;
  const status = asString(row.status) as Status;
  return {
    id: asNumber(row.id),
    title: asString(row.title),
    body: asString(row.body),
    audience: audienceLabels[audience] ? audience : "all",
    priority: priorityLabels[priority] ? priority : "info",
    status: status === "published" || status === "scheduled" ? status : "draft",
    pinned: Boolean(row.pinned),
    author: asString(row.author) || "Admin",
    views: asNumber(row.views),
    createdAt: asString(row.createdAt),
    updatedAt: asString(row.updatedAt),
    publishedAt: asString(row.publishedAt),
  };
}

function formatDate(value: string) {
  if (!value) return "Draft";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(parsed));
}

function priorityClass(priority: Priority) {
  if (priority === "urgent") return "border-red-200 bg-red-50 text-red-700";
  if (priority === "important") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-foreground/10 bg-muted text-muted-foreground";
}

function createEmptyForm(defaultAudience: Audience): AnnouncementForm {
  return {
    title: "",
    body: "",
    audience: defaultAudience,
    priority: "info",
    status: "published",
    pinned: false,
  };
}

export default function AnnouncementsPanel({ state }: { state: any }) {
  const props = state.props || {};
  const csrf = asString(props.csrfToken);
  const adminMode = asString(state.adminMode).toLowerCase();
  const isHrMode = adminMode === "hr_manager";
  const isTeacherMode = adminMode === "teacher";
  const audienceOptions = isHrMode ? hrAudienceOptions : defaultAudienceOptions;
  const defaultAudience: Audience = isHrMode ? "trainees" : "all";
  const [items, setItems] = useState<Announcement[]>(
    Array.isArray(props.adminAnnouncements)
      ? props.adminAnnouncements.map((row: Record<string, unknown>) => normalizeAnnouncement(row))
      : [],
  );
  const [tab, setTab] = useState<"all" | Status>("all");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Announcement | null>(null);
  const [form, setForm] = useState<AnnouncementForm>(() => createEmptyForm(defaultAudience));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const workspaceItems = useMemo(
    () =>
      isHrMode
        ? items.filter((item) => hrAudienceSet.has(item.audience))
        : isTeacherMode
          ? items.filter((item) => item.status === "published" && teacherAudienceSet.has(item.audience))
        : items,
    [isHrMode, isTeacherMode, items],
  );

  const filtered = useMemo(
    () =>
      workspaceItems
        .filter((item) => (tab === "all" || isTeacherMode ? true : item.status === tab))
        .sort((left, right) => Number(right.pinned) - Number(left.pinned)),
    [isTeacherMode, workspaceItems, tab],
  );

  const stats = useMemo(() => {
    const published = workspaceItems.filter((item) => item.status === "published").length;
    const drafts = workspaceItems.filter((item) => item.status === "draft").length;
    const pinned = workspaceItems.filter((item) => item.pinned).length;
    const urgent = workspaceItems.filter((item) => item.priority === "urgent").length;
    return {
      total: workspaceItems.length,
      published,
      drafts,
      reach: workspaceItems.reduce((sum, item) => sum + item.views, 0),
      pinned,
      urgent,
    };
  }, [workspaceItems]);

  const panelTitle = isHrMode ? "HR Broadcasts" : isTeacherMode ? "Updates" : "Announcements";
  const panelSubtitle = isHrMode
    ? "Internal updates for candidates, trainees, and teaching staff."
    : isTeacherMode
      ? "School updates for teachers."
    : "Publish news and updates to students and teachers.";
  const createButtonLabel = isHrMode ? "New Broadcast" : "New Announcement";
  const emptyStateLabel = isHrMode ? "No HR broadcasts yet." : isTeacherMode ? "No teacher updates yet." : "Nothing here yet.";

  function applyHrTemplate(template: (typeof hrBroadcastTemplates)[number]) {
    setForm((prev) => ({
      ...prev,
      title: template.title,
      body: template.body,
      audience: template.audience,
      priority: template.priority,
    }));
    setError("");
  }

  function openNew() {
    setEditing(null);
    setForm(createEmptyForm(defaultAudience));
    setError("");
    setOpen(true);
  }

  function openEdit(item: Announcement) {
    const nextAudience = audienceOptions.includes(item.audience) ? item.audience : defaultAudience;
    setEditing(item);
    setForm({
      title: item.title,
      body: item.body,
      audience: nextAudience,
      priority: item.priority,
      status: item.status,
      pinned: item.pinned,
    });
    setError("");
    setOpen(true);
  }

  async function save(event?: FormEvent) {
    event?.preventDefault();
    if (saving) return;
    if (!form.title.trim() || !form.body.trim()) {
      setError("Title and message are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(
        editing ? routes.adminAnnouncementApi(editing.id) : routes.adminAnnouncementsApi,
        {
          method: editing ? "PATCH" : "POST",
          headers: jsonCsrfHeaders(csrf),
          body: JSON.stringify({
            title: form.title,
            body: form.body,
            audience: form.audience,
            priority: form.priority,
            status: form.status,
            pinned: form.pinned,
          }),
        },
      );
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setError(apiErrorMessage(json, "Unable to save announcement."));
        return;
      }
      const saved = normalizeAnnouncement(apiData<{ announcement?: Record<string, unknown> }>(json).announcement || {});
      setItems((prev) =>
        editing
          ? prev.map((item) => (item.id === saved.id ? saved : item))
          : [saved, ...prev],
      );
      setOpen(false);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function patchItem(item: Announcement, values: Partial<Announcement>) {
    const res = await fetch(routes.adminAnnouncementApi(item.id), {
      method: "PATCH",
      headers: jsonCsrfHeaders(csrf),
      body: JSON.stringify({ ...item, ...values }),
    });
    const json = await res.json();
    if (!apiSucceeded(res, json)) return;
    const updated = normalizeAnnouncement(apiData<{ announcement?: Record<string, unknown> }>(json).announcement || {});
    setItems((prev) => prev.map((entry) => (entry.id === updated.id ? updated : entry)));
  }

  async function deleteItem(item: Announcement) {
    if (!window.confirm(`Delete "${item.title}"?`)) return;
    const res = await fetch(routes.adminAnnouncementApi(item.id), {
      method: "DELETE",
      headers: csrfHeaders(csrf),
    });
    if (res.ok) {
      setItems((prev) => prev.filter((entry) => entry.id !== item.id));
    }
  }

  return (
    <div className="space-y-4">
      <ChartCard
        title={panelTitle}
        subtitle={panelSubtitle}
        icon={<Megaphone className="h-4 w-4 text-info" />}
        headerActions={isTeacherMode ? null :
          <button
            type="button"
            onClick={openNew}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            {createButtonLabel}
          </button>
        }
      >
        {isHrMode ? (
          <div className="mb-3 rounded-lg border border-sky-100 bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-700">
            Only HR audiences are shown here. Student-facing school announcements stay outside this workspace.
          </div>
        ) : null}
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {isHrMode ? (
            <>
              <MetricCard icon={<Send className="h-4 w-4" />} label="Published" value={stats.published} detail="sent broadcasts" tone="success" />
              <MetricCard icon={<Pencil className="h-4 w-4" />} label="Drafts" value={stats.drafts} detail="in progress" />
              <MetricCard icon={<Pin className="h-4 w-4" />} label="Pinned" value={stats.pinned} detail="highlighted" tone="info" />
              <MetricCard icon={<AlertTriangle className="h-4 w-4" />} label="Urgent" value={stats.urgent} detail="priority notices" tone="warning" />
            </>
          ) : (
            <>
              <MetricCard icon={<Megaphone className="h-4 w-4" />} label="Total" value={stats.total} detail="all announcements" tone="info" />
              <MetricCard icon={<Send className="h-4 w-4" />} label="Published" value={stats.published} detail="visible posts" tone="success" />
              <MetricCard icon={<Pencil className="h-4 w-4" />} label="Drafts" value={stats.drafts} detail="not published" />
              <MetricCard icon={<Users className="h-4 w-4" />} label="Reach" value={stats.reach} detail="target audience" />
            </>
          )}
        </div>
      </ChartCard>

      {!isTeacherMode ? (
        <div className="flex flex-wrap gap-2">
          {(["all", "published", "draft", "scheduled"] as const).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`rounded-lg px-3 py-2 text-xs font-bold ${
                tab === key
                  ? "bg-primary text-primary-foreground"
                  : "border border-foreground/10 bg-surface text-muted-foreground hover:bg-muted"
              }`}
            >
              {key === "all" ? "All" : key[0].toUpperCase() + key.slice(1)}
            </button>
          ))}
        </div>
      ) : null}

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <EmptyState title={emptyStateLabel} icon={<Megaphone className="h-6 w-6" />} />
        ) : (
          filtered.map((item) => {
            const menuItems: ActionMenuItem[] = [
              {
                key: "edit",
                label: "Edit",
                icon: <Pencil className="h-4 w-4" />,
                onClick: () => openEdit(item),
              },
              { separator: true, key: "delete-separator" },
              {
                key: "delete",
                label: "Delete",
                icon: <Trash2 className="h-4 w-4" />,
                onClick: () => deleteItem(item),
                danger: true,
              },
            ];

            return (
              <article
                key={item.id}
                className={`rounded-lg border bg-surface p-4 shadow-card ${
                  item.pinned ? "border-primary/40" : "border-foreground/10"
                }`}
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {item.pinned ? <Pin className="h-4 w-4 text-primary" /> : null}
                      <h3 className="text-base font-semibold text-foreground">{item.title}</h3>
                      <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-bold ${priorityClass(item.priority)}`}>
                        {item.priority === "urgent" ? <AlertTriangle className="h-3 w-3" /> : null}
                        {item.priority === "info" ? <Sparkles className="h-3 w-3" /> : null}
                        {priorityLabels[item.priority]}
                      </span>
                      <span className="rounded-full border border-foreground/10 bg-background px-2 py-0.5 text-[11px] font-bold text-muted-foreground">
                        {audienceLabels[item.audience]}
                      </span>
                      {item.status !== "published" ? (
                        <span className="rounded-full border border-foreground/10 px-2 py-0.5 text-[11px] font-bold text-muted-foreground">
                          {item.status}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                      {item.body}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>{item.author}</span>
                      <span>|</span>
                      <span>{formatDate(item.publishedAt || item.updatedAt || item.createdAt)}</span>
                      {item.status === "published" && !isHrMode ? (
                        <>
                          <span>|</span>
                          <span>{item.views} views</span>
                        </>
                      ) : null}
                    </div>
                  </div>
                  {!isTeacherMode ? (
                    <div className="flex shrink-0 items-center gap-2 md:justify-end">
                      <button
                        type="button"
                        onClick={() =>
                          item.status !== "published"
                            ? patchItem(item, { status: "published" })
                            : openEdit(item)
                        }
                        className="inline-flex h-9 min-w-[5.5rem] items-center justify-center gap-1 rounded-lg bg-primary px-3 text-xs font-black text-primary-foreground transition active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100"
                      >
                        {item.status !== "published" ? <Send className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                        {item.status !== "published" ? "Publish" : "Edit"}
                      </button>
                      <IconButton
                        label={item.pinned ? "Unpin" : "Pin"}
                        onClick={() => patchItem(item, { pinned: !item.pinned })}
                      >
                        {item.pinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
                      </IconButton>
                      <ActionMenu items={menuItems} label={`Actions for ${item.title}`} />
                    </div>
                  ) : null}
                </div>
              </article>
            );
          })
        )}
      </div>

      {open ? (
        <Modal
          title={editing ? (isHrMode ? "Edit Broadcast" : "Edit Announcement") : isHrMode ? "New Broadcast" : "New Announcement"}
          onClose={() => setOpen(false)}
          size="md"
        >
          <form onSubmit={save} className="flex min-h-0 flex-1 flex-col">
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
              {error ? <p className="text-xs font-semibold text-destructive">{error}</p> : null}
              {isHrMode ? (
                <div className="rounded-lg border border-foreground/10 bg-background p-3">
                  <FieldLabel>Quick Templates</FieldLabel>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {hrBroadcastTemplates.map((template) => (
                      <button
                        key={template.key}
                        type="button"
                        onClick={() => applyHrTemplate(template)}
                        className="rounded-lg border border-foreground/10 bg-surface px-3 py-3 text-left transition-colors hover:bg-muted"
                      >
                        <p className="text-sm font-bold">{template.label}</p>
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">{template.summary}</p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
              <label className="block">
                <FieldLabel>Title</FieldLabel>
                <input
                  value={form.title}
                  onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                  maxLength={120}
                  className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  placeholder={isHrMode ? "Practice session update" : "Midterm exam schedule"}
                />
              </label>
              <label className="block">
                <FieldLabel>Message</FieldLabel>
                <textarea
                  value={form.body}
                  onChange={(event) => setForm((prev) => ({ ...prev, body: event.target.value }))}
                  maxLength={1000}
                  rows={5}
                  className="w-full resize-none rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  placeholder={isHrMode ? "Write the broadcast..." : "Write the announcement..."}
                />
                <p className="mt-1 text-xs text-muted-foreground">{form.body.length}/1000</p>
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <FieldLabel>Audience</FieldLabel>
                  <select
                    value={form.audience}
                    onChange={(event) => setForm((prev) => ({ ...prev, audience: event.target.value as Audience }))}
                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  >
                    {audienceOptions.map((value) => (
                      <option key={value} value={value}>
                        {audienceLabels[value]}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <FieldLabel>Priority</FieldLabel>
                  <select
                    value={form.priority}
                    onChange={(event) => setForm((prev) => ({ ...prev, priority: event.target.value as Priority }))}
                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  >
                    {Object.entries(priorityLabels).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex items-center justify-between rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm">
                  <span className="inline-flex items-center gap-2 font-semibold">
                    <Pin className="h-4 w-4" />
                    Pin to top
                  </span>
                  <input
                    type="checkbox"
                    checked={form.pinned}
                    onChange={(event) => setForm((prev) => ({ ...prev, pinned: event.target.checked }))}
                    className="h-4 w-4 accent-primary"
                  />
                </label>
                <label className="block">
                  <FieldLabel>Status</FieldLabel>
                  <select
                    value={form.status}
                    onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value as Status }))}
                    className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  >
                    <option value="published">Published</option>
                    <option value="draft">Draft</option>
                    <option value="scheduled">Scheduled</option>
                  </select>
                </label>
              </div>
            </div>
            <div className="flex flex-col-reverse gap-2 border-t border-foreground/5 px-5 py-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg border border-foreground/10 px-4 py-2 text-sm font-bold text-muted-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground disabled:opacity-60"
              >
                {saving ? "Saving..." : editing ? "Save Changes" : form.status === "published" ? (isHrMode ? "Publish Broadcast" : "Publish") : "Save Draft"}
              </button>
            </div>
          </form>
        </Modal>
      ) : null}
    </div>
  );
}

function FieldLabel({ children }: { children: string }) {
  return (
    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  );
}
