import { useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
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
  X,
} from "lucide-react";
import { ChartCard } from "@/components/ChartCard";
import { routes } from "@/lib/routes";
import { asNumber, asString } from "../shared";

type Audience = "all" | "students" | "teachers" | "year10" | "year11";
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
  teachers: "All teachers",
  year10: "Year 10",
  year11: "Year 11",
};

const priorityLabels: Record<Priority, string> = {
  info: "Info",
  important: "Important",
  urgent: "Urgent",
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

const emptyForm = {
  title: "",
  body: "",
  audience: "all" as Audience,
  priority: "info" as Priority,
  status: "published" as Status,
  pinned: false,
};

export default function AnnouncementsPanel({ state }: { state: any }) {
  const props = state.props || {};
  const csrf = asString(props.csrfToken);
  const [items, setItems] = useState<Announcement[]>(
    Array.isArray(props.adminAnnouncements)
      ? props.adminAnnouncements.map((row: Record<string, unknown>) => normalizeAnnouncement(row))
      : [],
  );
  const [tab, setTab] = useState<"all" | Status>("all");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Announcement | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const filtered = useMemo(
    () =>
      items
        .filter((item) => (tab === "all" ? true : item.status === tab))
        .sort((left, right) => Number(right.pinned) - Number(left.pinned)),
    [items, tab],
  );

  const stats = useMemo(
    () => ({
      total: items.length,
      published: items.filter((item) => item.status === "published").length,
      drafts: items.filter((item) => item.status === "draft").length,
      reach: items.reduce((sum, item) => sum + item.views, 0),
    }),
    [items],
  );

  function openNew() {
    setEditing(null);
    setForm(emptyForm);
    setError("");
    setOpen(true);
  }

  function openEdit(item: Announcement) {
    setEditing(item);
    setForm({
      title: item.title,
      body: item.body,
      audience: item.audience,
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
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf,
            "X-Requested-With": "XMLHttpRequest",
          },
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
      if (!res.ok || !json.ok) {
        setError(asString(json.message) || "Unable to save announcement.");
        return;
      }
      const saved = normalizeAnnouncement(json.announcement || {});
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
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ ...item, ...values }),
    });
    const json = await res.json();
    if (!res.ok || !json.ok) return;
    const updated = normalizeAnnouncement(json.announcement || {});
    setItems((prev) => prev.map((entry) => (entry.id === updated.id ? updated : entry)));
  }

  async function deleteItem(item: Announcement) {
    if (!window.confirm(`Delete "${item.title}"?`)) return;
    const res = await fetch(routes.adminAnnouncementApi(item.id), {
      method: "DELETE",
      headers: {
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    if (res.ok) {
      setItems((prev) => prev.filter((entry) => entry.id !== item.id));
    }
  }

  return (
    <div className="space-y-4">
      <ChartCard
        title="Announcements"
        subtitle="Publish news and updates to students and teachers."
        icon={<Megaphone className="h-4 w-4 text-info" />}
        headerActions={
          <button
            type="button"
            onClick={openNew}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-bold text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            New Announcement
          </button>
        }
      >
        <div className="grid gap-3 sm:grid-cols-4">
          <StatTile icon={<Megaphone className="h-4 w-4" />} label="Total" value={stats.total} />
          <StatTile icon={<Send className="h-4 w-4" />} label="Published" value={stats.published} />
          <StatTile icon={<Pencil className="h-4 w-4" />} label="Drafts" value={stats.drafts} />
          <StatTile icon={<Users className="h-4 w-4" />} label="Reach" value={stats.reach} />
        </div>
      </ChartCard>

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

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="rounded-lg border border-foreground/10 bg-surface px-4 py-10 text-center text-sm text-muted-foreground">
            Nothing here yet.
          </div>
        ) : (
          filtered.map((item) => (
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
                    <span>{audienceLabels[item.audience]}</span>
                    <span>|</span>
                    <span>{item.author}</span>
                    <span>|</span>
                    <span>{formatDate(item.publishedAt || item.updatedAt || item.createdAt)}</span>
                    {item.status === "published" ? (
                      <>
                        <span>|</span>
                        <span>{item.views} views</span>
                      </>
                    ) : null}
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap gap-1">
                  {item.status !== "published" ? (
                    <IconButton
                      label="Publish"
                      onClick={() => patchItem(item, { status: "published" })}
                    >
                      <Send className="h-4 w-4" />
                    </IconButton>
                  ) : null}
                  <IconButton
                    label={item.pinned ? "Unpin" : "Pin"}
                    onClick={() => patchItem(item, { pinned: !item.pinned })}
                  >
                    {item.pinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
                  </IconButton>
                  <IconButton label="Edit" onClick={() => openEdit(item)}>
                    <Pencil className="h-4 w-4" />
                  </IconButton>
                  <IconButton label="Delete" danger onClick={() => deleteItem(item)}>
                    <Trash2 className="h-4 w-4" />
                  </IconButton>
                </div>
              </div>
            </article>
          ))
        )}
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4">
          <form
            onSubmit={save}
            className="flex max-h-[88dvh] w-full max-w-xl flex-col overflow-hidden rounded-lg bg-surface shadow-card-hover"
          >
            <div className="flex items-center justify-between border-b border-foreground/5 px-5 py-3">
              <h3 className="text-sm font-bold">
                {editing ? "Edit Announcement" : "New Announcement"}
              </h3>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
              {error ? <p className="text-xs font-semibold text-destructive">{error}</p> : null}
              <label className="block">
                <FieldLabel>Title</FieldLabel>
                <input
                  value={form.title}
                  onChange={(event) => setForm((prev) => ({ ...prev, title: event.target.value }))}
                  maxLength={120}
                  className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  placeholder="Midterm exam schedule"
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
                  placeholder="Write the announcement..."
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
                    {Object.entries(audienceLabels).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
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
            <div className="flex justify-end gap-2 border-t border-foreground/5 px-5 py-3">
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
                {saving ? "Saving..." : editing ? "Save Changes" : form.status === "published" ? "Publish" : "Save Draft"}
              </button>
            </div>
          </form>
        </div>
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

function StatTile({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-lg border border-foreground/10 bg-background p-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold tabular-nums">{value}</p>
        </div>
      </div>
    </div>
  );
}

function IconButton({
  children,
  label,
  danger = false,
  onClick,
}: {
  children: ReactNode;
  label: string;
  danger?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted ${
        danger ? "text-destructive" : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}
