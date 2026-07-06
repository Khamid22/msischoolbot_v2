import {
  AlertTriangle,
  CalendarDays,
  Clock3,
  MapPin,
  Megaphone,
  Plus,
  ShieldCheck,
} from "lucide-react";
import {
  AcademicDirectorPageShell,
  HeadOfDepartmentPageShell,
} from "@/roles/common/components/AcademicDirectorShell";
import { EmptyState } from "@/shared/ui/EmptyState";
import { MetricCard } from "@/shared/ui/MetricCard";
import { MetricGrid } from "@/shared/ui/MetricGrid";
import { PageHeader } from "@/shared/ui/PageHeader";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type WorkspaceKind = "timetable" | "announcements";
type Row = Record<string, unknown>;

interface AcademicDepartmentWorkspaceProps {
  authLogin?: string;
  authRole?: string;
  role?: string;
  csrfToken?: string;
  workspace?: WorkspaceKind;
  adminAcademicSchedules?: Row[];
  adminAcademicSessions?: Row[];
  adminAnnouncements?: Row[];
  warning?: string;
}

function asText(value: unknown) {
  return String(value ?? "").trim();
}

function rowsFrom(value: unknown): Row[] {
  return Array.isArray(value) ? value.filter((row): row is Row => Boolean(row && typeof row === "object")) : [];
}

function uniqueCount(rows: Row[], keys: string[]) {
  const values = new Set<string>();
  rows.forEach((row) => {
    for (const key of keys) {
      const value = asText(row[key]);
      if (value) {
        values.add(value.toLowerCase());
        break;
      }
    }
  });
  return values.size;
}

function statusTone(value: unknown): "neutral" | "success" | "warning" | "danger" | "info" {
  const normalized = asText(value).toLowerCase();
  if (["published", "active", "scheduled"].includes(normalized)) return "success";
  if (["draft", "pending"].includes(normalized)) return "warning";
  if (["cancelled", "rejected"].includes(normalized)) return "danger";
  if (normalized) return "info";
  return "neutral";
}

function workspaceRole(value: unknown) {
  return asText(value).replace(/-/g, "_").toLowerCase();
}

function scheduleTitle(row: Row, fallback: string) {
  return (
    asText(row.title) ||
    [asText(row.group_name), asText(row.subject_name)].filter(Boolean).join(" · ") ||
    fallback
  );
}

function TimetableContent({
  schedules,
  sessions,
}: {
  schedules: Row[];
  sessions: Row[];
}) {
  const items = [
    ...sessions.map((row) => ({ row, kind: "Session" })),
    ...schedules.map((row) => ({ row, kind: "Schedule" })),
  ];
  const sourceRows = items.map((item) => item.row);

  return (
    <>
      <MetricGrid>
        <MetricCard label="Sessions" value={sessions.length} detail="dated lessons" tone="success" />
        <MetricCard label="Schedules" value={schedules.length} detail="recurring rules" tone="info" />
        <MetricCard label="Groups" value={uniqueCount(sourceRows, ["group_id", "group_name"])} detail="visible groups" />
        <MetricCard label="Subjects" value={uniqueCount(sourceRows, ["subject_id", "subject_name"])} detail="visible scopes" />
      </MetricGrid>

      {items.length ? (
        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map(({ row, kind }, index) => {
            const isSession = kind === "Session";
            const date = asText(row.session_date) || asText(row.start_date) || "Date not set";
            const start = asText(row.start_time);
            const end = asText(row.end_time);
            const room = asText(row.room) || asText(row.online_url) || "Room not set";
            const status = asText(row.status) || (isSession ? "scheduled" : "active");
            return (
              <article key={`${kind}-${asText(row.id) || index}`} className="rounded-xl border border-border bg-surface p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[11px] font-black uppercase tracking-wide text-primary">{kind}</p>
                    <h2 className="mt-1 line-clamp-2 text-base font-black text-foreground">
                      {scheduleTitle(row, isSession ? "Scheduled lesson" : "Timetable rule")}
                    </h2>
                    <p className="mt-1 truncate text-xs font-bold text-muted-foreground">
                      {asText(row.teacher_name) || "Teacher not assigned"}
                    </p>
                  </div>
                  <StatusBadge tone={statusTone(status)} className="shrink-0 text-[10px]">
                    {status}
                  </StatusBadge>
                </div>
                <dl className="mt-4 grid gap-2 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2">
                    <CalendarDays className="h-4 w-4 shrink-0 text-primary" />
                    <span className="truncate font-bold text-foreground">
                      {date}
                      {!isSession && asText(row.end_date) ? ` - ${asText(row.end_date)}` : ""}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2">
                    <Clock3 className="h-4 w-4 shrink-0 text-primary" />
                    <span className="truncate font-bold text-foreground">
                      {[start, end].filter(Boolean).join(" - ") || asText(row.weekdays) || "Time not set"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2">
                    <MapPin className="h-4 w-4 shrink-0 text-primary" />
                    <span className="truncate font-bold text-foreground">{room}</span>
                  </div>
                </dl>
              </article>
            );
          })}
        </section>
      ) : (
        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title="No timetable entries yet"
          detail="Scheduled sessions and recurring timetable rules will appear here when they exist."
        />
      )}
    </>
  );
}

function AnnouncementsContent({ announcements }: { announcements: Row[] }) {
  const publishedCount = announcements.filter((row) => asText(row.status).toLowerCase() === "published").length;
  const urgentCount = announcements.filter((row) => asText(row.priority).toLowerCase() === "urgent").length;
  const pinnedCount = announcements.filter((row) => Boolean(row.pinned)).length;

  return (
    <>
      <MetricGrid>
        <MetricCard label="Announcements" value={announcements.length} detail="visible records" tone="info" />
        <MetricCard label="Published" value={publishedCount} detail="live updates" tone="success" />
        <MetricCard label="Pinned" value={pinnedCount} detail="highlighted" />
        <MetricCard label="Urgent" value={urgentCount} detail="priority posts" tone={urgentCount ? "warning" : "default"} />
      </MetricGrid>

      {announcements.length ? (
        <section className="space-y-3">
          {announcements.map((item, index) => {
            const title = asText(item.title) || "Announcement";
            const status = asText(item.status) || "draft";
            return (
              <article key={`${asText(item.id) || title}-${index}`} className="rounded-xl border border-border bg-surface p-4 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="break-words text-base font-black text-foreground">{title}</h2>
                      <StatusBadge tone={statusTone(status)} className="text-[10px]">{status}</StatusBadge>
                      {item.pinned ? <StatusBadge tone="info" className="text-[10px]">Pinned</StatusBadge> : null}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                      {asText(item.body) || "No message body."}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
                    <span className="rounded-full border border-border bg-muted px-2 py-1">{asText(item.audience) || "all"}</span>
                    <span className="rounded-full border border-border bg-muted px-2 py-1">{asText(item.priority) || "info"}</span>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      ) : (
        <EmptyState
          icon={<Megaphone className="h-6 w-6" />}
          title="No announcements yet"
          detail="Existing announcement records will appear here when the announcement service returns them."
        />
      )}
    </>
  );
}

export default function AcademicDepartmentWorkspace({
  authLogin = "",
  authRole = "",
  role = "",
  csrfToken = "",
  workspace = "timetable",
  adminAcademicSchedules = [],
  adminAcademicSessions = [],
  adminAnnouncements = [],
  warning = "",
}: AcademicDepartmentWorkspaceProps) {
  const normalizedRole = workspaceRole(role || authRole);
  const isHod = normalizedRole === "head_of_department";
  const isAnnouncements = workspace === "announcements";
  const active = isAnnouncements ? "announcements" : "timetable";
  const roleLabel = isHod ? "Head of Department" : "Academic Director";
  const title = isAnnouncements ? "Announcements" : "Timetable";
  const description = isAnnouncements
    ? isHod
      ? "Subject-scoped academic updates and staff announcements."
      : "Academic announcements from the existing announcement service."
    : isHod
      ? "Subject-scoped scheduled sessions and timetable rules."
      : "Scheduled sessions and recurring timetable rules across Academic Department.";
  const schedules = rowsFrom(adminAcademicSchedules);
  const sessions = rowsFrom(adminAcademicSessions);
  const announcements = rowsFrom(adminAnnouncements);
  const content = (
    <>
      <PageHeader
        title={title}
        subtitle={description}
        badge={
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-black uppercase tracking-wide text-primary">
            {roleLabel}
          </span>
        }
        actions={
          <>
            {authLogin ? (
              <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-border bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
                <span className="truncate">{authLogin}</span>
              </div>
            ) : null}
            {isAnnouncements ? (
              <button
                type="button"
                disabled
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground opacity-80"
              >
                <Plus className="h-4 w-4" />
                Coming soon
              </button>
            ) : null}
          </>
        }
      />

      {warning ? (
        <section className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <p className="text-sm font-semibold leading-6">{warning}</p>
        </section>
      ) : null}

      {isAnnouncements ? (
        <AnnouncementsContent announcements={announcements} />
      ) : (
        <TimetableContent schedules={schedules} sessions={sessions} />
      )}
    </>
  );

  if (isHod) {
    return (
      <HeadOfDepartmentPageShell authLogin={authLogin} csrfToken={csrfToken} active={active} maxWidthClass="max-w-6xl">
        {content}
      </HeadOfDepartmentPageShell>
    );
  }

  return (
    <AcademicDirectorPageShell authLogin={authLogin} csrfToken={csrfToken} active={active} maxWidthClass="max-w-6xl">
      {content}
    </AcademicDirectorPageShell>
  );
}
