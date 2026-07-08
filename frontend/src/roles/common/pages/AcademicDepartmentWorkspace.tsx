import { useMemo, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  BookOpenCheck,
  CalendarDays,
  Clock3,
  ListFilter,
  MapPin,
  Megaphone,
  Plus,
  ShieldCheck,
} from "lucide-react";
import {
  AcademicDirectorPageShell,
  HeadOfDepartmentPageShell,
} from "@/roles/common/components/AcademicDirectorShell";
import { routes } from "@/shared/lib/routes";
import { EmptyState } from "@/shared/ui/EmptyState";
import { MetricCard } from "@/shared/ui/MetricCard";
import { PageHeader } from "@/shared/ui/PageHeader";
import { ResponsiveTable } from "@/shared/ui/ResponsiveTable";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type WorkspaceKind = "timetable" | "announcements";
type Row = Record<string, unknown>;
type TimetableRange = "today" | "week";

type TimetableItem = {
  row: Row;
  index: number;
};

interface AcademicDepartmentWorkspaceProps {
  authLogin?: string;
  authRole?: string;
  role?: string;
  csrfToken?: string;
  workspace?: WorkspaceKind;
  adminAcademyLessonEvents?: Row[];
  adminAnnouncements?: Row[];
  warning?: string;
}

function asText(value: unknown) {
  return String(value ?? "").trim();
}

function rowsFrom(value: unknown): Row[] {
  return Array.isArray(value) ? value.filter((row): row is Row => Boolean(row && typeof row === "object")) : [];
}

function uniqueOptions(rows: Row[], keys: string[]) {
  const values = new Set<string>();
  rows.forEach((row) => {
    for (const key of keys) {
      const value = asText(row[key]);
      if (value) {
        values.add(value);
        break;
      }
    }
  });
  return [...values].sort((a, b) => a.localeCompare(b));
}

function statusTone(value: unknown): "neutral" | "success" | "warning" | "danger" | "info" {
  const normalized = asText(value).toLowerCase();
  if (["published", "active", "scheduled", "completed"].includes(normalized)) return "success";
  if (["draft", "pending", "assigned"].includes(normalized)) return "warning";
  if (["cancelled", "canceled", "rejected", "missing"].includes(normalized)) return "danger";
  if (normalized) return "info";
  return "neutral";
}

function priorityTone(value: unknown): "neutral" | "success" | "warning" | "danger" | "info" {
  const normalized = asText(value).toLowerCase();
  if (["urgent", "high"].includes(normalized)) return "danger";
  if (["important", "medium"].includes(normalized)) return "warning";
  if (normalized) return "info";
  return "neutral";
}

function workspaceRole(value: unknown) {
  return asText(value).replace(/-/g, "_").toLowerCase();
}

function pad2(value: number) {
  return String(value).padStart(2, "0");
}

function dateKeyFromDate(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function parseDateKey(value: unknown) {
  const raw = asText(value);
  if (!raw) return "";

  const ddmmyyyy = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (ddmmyyyy) {
    return `${ddmmyyyy[3]}-${pad2(Number(ddmmyyyy[2]))}-${pad2(Number(ddmmyyyy[1]))}`;
  }

  const iso = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (iso) {
    return `${iso[1]}-${pad2(Number(iso[2]))}-${pad2(Number(iso[3]))}`;
  }

  const parsed = Date.parse(raw);
  if (Number.isFinite(parsed)) {
    return dateKeyFromDate(new Date(parsed));
  }
  return "";
}

function displayDateFromKey(key: string, fallback = "Date not set") {
  if (!key) return fallback;
  const parsed = new Date(`${key}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return fallback;
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(parsed);
}

function timetableDateKey(item: TimetableItem) {
  return parseDateKey(item.row.session_date) || parseDateKey(item.row.session_datetime);
}

function timetableTitle(item: TimetableItem) {
  return (
    asText(item.row.title) ||
    [asText(item.row.group_name), asText(item.row.subject_name)].filter(Boolean).join(" · ") ||
    "Academy lesson"
  );
}

function timetableStatus(item: TimetableItem) {
  return asText(item.row.status) || "scheduled";
}

function timetableTime(row: Row) {
  const explicit = [asText(row.start_time), asText(row.end_time)].filter(Boolean).join(" - ");
  if (explicit) return explicit;
  const sessionTime = asText(row.session_datetime).replace(" ", "T").split("T", 2)[1]?.slice(0, 5) || "";
  return sessionTime || asText(row.weekdays) || "Time not set";
}

function timetableLocation(row: Row) {
  return asText(row.room) || asText(row.online_url) || "Room not set";
}

function sortTimetableItems(items: TimetableItem[]) {
  const todayKey = dateKeyFromDate(new Date());
  return [...items].sort((a, b) => {
    const dateA = timetableDateKey(a) || "9999-99-99";
    const dateB = timetableDateKey(b) || "9999-99-99";
    const upcomingA = dateA >= todayKey ? 0 : 1;
    const upcomingB = dateB >= todayKey ? 0 : 1;
    if (upcomingA !== upcomingB) return upcomingA - upcomingB;
    if (dateA !== dateB) return dateA.localeCompare(dateB);
    return timetableTime(a.row).localeCompare(timetableTime(b.row));
  });
}

function TimetableEventCard({ item, className = "" }: { item: TimetableItem; className?: string }) {
  const row = item.row;
  const dateKey = timetableDateKey(item);
  const status = timetableStatus(item);

  return (
    <article className={`rounded-lg border border-border bg-surface p-3 shadow-sm ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-black uppercase tracking-wide text-primary">Academy lesson</p>
          <h2 className="mt-1 line-clamp-2 text-sm font-black text-foreground">{timetableTitle(item)}</h2>
          <p className="mt-1 truncate text-[11px] font-bold text-muted-foreground">
            {asText(row.teacher_name) || "Teacher not assigned"}
          </p>
        </div>
        <StatusBadge tone={statusTone(status)} className="shrink-0 text-[10px]">
          {status}
        </StatusBadge>
      </div>
      <dl className="mt-3 grid gap-1.5 text-xs text-muted-foreground">
        <div className="flex items-center gap-2 rounded-md bg-muted px-2 py-1.5">
          <CalendarDays className="h-3.5 w-3.5 shrink-0 text-primary" />
          <span className="truncate font-bold text-foreground">{displayDateFromKey(dateKey)}</span>
        </div>
        <div className="flex items-center gap-2 rounded-md bg-muted px-2 py-1.5">
          <Clock3 className="h-3.5 w-3.5 shrink-0 text-primary" />
          <span className="truncate font-bold text-foreground">{timetableTime(row)}</span>
        </div>
        <div className="flex items-center gap-2 rounded-md bg-muted px-2 py-1.5">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-primary" />
          <span className="truncate font-bold text-foreground">{timetableLocation(row)}</span>
        </div>
        {asText(row.evaluator_name) ? (
          <div className="flex items-center gap-2 rounded-md bg-muted px-2 py-1.5">
            <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-primary" />
            <span className="truncate font-bold text-foreground">Evaluator: {asText(row.evaluator_name)}</span>
          </div>
        ) : null}
      </dl>
    </article>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="min-w-0 flex-1">
      <span className="mb-1 block text-[10px] font-black uppercase tracking-wide text-muted-foreground">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm font-bold text-foreground outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
      >
        {children}
      </select>
    </label>
  );
}

function TimetableContent({
  academyLessons,
  isHod,
}: {
  academyLessons: Row[];
  isHod: boolean;
}) {
  const [range, setRange] = useState<TimetableRange>("week");
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [teacherFilter, setTeacherFilter] = useState("all");
  const [filtersOpen, setFiltersOpen] = useState(false);

  const items = useMemo<TimetableItem[]>(
    () => academyLessons.map((row, index) => ({ row, index })),
    [academyLessons],
  );
  const sourceRows = items.map((item) => item.row);
  const subjectOptions = uniqueOptions(sourceRows, ["subject_name"]);
  const teacherOptions = uniqueOptions(sourceRows, ["teacher_name"]);
  const todayKey = dateKeyFromDate(new Date());
  const todayCount = items.filter((item) => timetableDateKey(item) === todayKey).length;
  const upcomingCount = items.filter((item) => timetableDateKey(item) >= todayKey).length;
  const passedCount = items.filter((item) => asText(item.row.status).toLowerCase() === "passed").length;
  const academyHref = isHod ? routes.headOfDepartmentTeacherAcademy : routes.academicDirectorTeacherAcademy;
  const activeFilterCount = [subjectFilter !== "all", teacherFilter !== "all"].filter(Boolean).length;

  const filteredItems = sortTimetableItems(
    items.filter((item) => {
      const row = item.row;
      if (range === "today" && timetableDateKey(item) !== todayKey) return false;
      if (subjectFilter !== "all" && asText(row.subject_name) !== subjectFilter) return false;
      if (teacherFilter !== "all" && asText(row.teacher_name) !== teacherFilter) return false;
      return true;
    }),
  );

  const resetFilters = () => {
    setRange("week");
    setSubjectFilter("all");
    setTeacherFilter("all");
    setFiltersOpen(false);
  };

  return (
    <>
      <div className="grid grid-cols-4 gap-2">
        <MetricCard label="Today" value={todayCount} detail="dated" tone="success" density="compact" />
        <MetricCard label="Upcoming" value={upcomingCount} detail="scheduled" tone="info" density="compact" />
        <MetricCard label="Passed" value={passedCount} detail="assessed" density="compact" />
        <MetricCard label="Academy" value={academyLessons.length} detail="lessons" density="compact" />
      </div>

      <section className="relative rounded-lg border border-border bg-surface p-3 shadow-card">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <ListFilter className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-black text-foreground">Timetable View</h2>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="grid h-9 w-36 grid-cols-2 rounded-lg border border-border bg-background p-1">
              {(["today", "week"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setRange(option)}
                  className={`rounded-md px-2 text-xs font-black capitalize transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none ${
                    range === option ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setFiltersOpen((current) => !current)}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-border bg-background px-3 text-xs font-black text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
              aria-expanded={filtersOpen}
            >
              Filters
              {activeFilterCount ? (
                <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] text-primary-foreground">{activeFilterCount}</span>
              ) : null}
            </button>
          </div>
        </div>
        {filtersOpen ? (
          <div className="absolute left-3 right-3 top-[calc(100%+0.5rem)] z-20 rounded-lg border border-border bg-surface/95 p-3 shadow-card-hover backdrop-blur sm:left-auto sm:w-[22rem]">
            <div className="grid gap-3">
              {subjectOptions.length ? (
                <FilterSelect label="Subject filter" value={subjectFilter} onChange={setSubjectFilter}>
                  <option value="all">All subjects</option>
                  {subjectOptions.map((subject) => <option key={subject} value={subject}>{subject}</option>)}
                </FilterSelect>
              ) : null}
              {teacherOptions.length ? (
                <FilterSelect label="Teacher filter" value={teacherFilter} onChange={setTeacherFilter}>
                  <option value="all">All teachers</option>
                  {teacherOptions.map((teacher) => <option key={teacher} value={teacher}>{teacher}</option>)}
                </FilterSelect>
              ) : null}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={resetFilters}
                  className="inline-flex h-9 flex-1 items-center justify-center rounded-lg border border-border bg-background text-xs font-black text-foreground hover:bg-muted"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={() => setFiltersOpen(false)}
                  className="inline-flex h-9 flex-1 items-center justify-center rounded-lg bg-primary text-xs font-black text-primary-foreground"
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {items.length && filteredItems.length ? (
        <>
          <div className="md:hidden">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="truncate text-xs font-black uppercase tracking-wide text-muted-foreground">
                Upcoming first
              </p>
              <p className="shrink-0 text-[11px] font-bold text-muted-foreground">{filteredItems.length} events</p>
            </div>
            <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 [-webkit-overflow-scrolling:touch]">
              {filteredItems.map((item) => (
                <TimetableEventCard
                  key={asText(item.row.id) || item.index}
                  item={item}
                  className="min-w-[82%] snap-start"
                />
              ))}
            </div>
          </div>

          <ResponsiveTable showAt="md" className="rounded-xl border border-border bg-surface shadow-card">
            <table className="w-full min-w-[860px] divide-y divide-border text-left text-sm">
              <thead className="bg-muted/60 text-xs font-black uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Lesson / Subject</th>
                  <th className="px-4 py-3">Teacher</th>
                  <th className="px-4 py-3">Location</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredItems.map((item) => {
                  const row = item.row;
                  const status = timetableStatus(item);
                  return (
                    <tr key={asText(row.id) || item.index} className="transition-colors duration-150 hover:bg-muted/40 motion-reduce:transition-none">
                      <td className="whitespace-nowrap px-4 py-3 font-bold text-foreground">
                        {displayDateFromKey(timetableDateKey(item))}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-semibold text-muted-foreground">{timetableTime(row)}</td>
                      <td className="max-w-[18rem] px-4 py-3">
                        <p className="truncate font-black text-foreground">{timetableTitle(item)}</p>
                        <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{asText(row.subject_name) || "Subject not set"}</p>
                      </td>
                      <td className="max-w-[14rem] px-4 py-3">
                        <p className="truncate font-semibold text-muted-foreground">{asText(row.teacher_name) || "Not assigned"}</p>
                        {asText(row.evaluator_name) ? (
                          <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">Evaluator: {asText(row.evaluator_name)}</p>
                        ) : null}
                      </td>
                      <td className="max-w-[14rem] px-4 py-3">
                        <p className="truncate font-semibold text-muted-foreground">{timetableLocation(row)}</p>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <StatusBadge tone={statusTone(status)} className="text-[10px]">
                          {status}
                        </StatusBadge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </ResponsiveTable>
        </>
      ) : (
        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title={items.length ? "No academy lessons match these filters" : "No academy lessons scheduled yet"}
          detail={
            items.length
              ? "Try Week view or clear the subject and teacher filters."
              : "Scheduled Teacher Academy lessons will appear here once you schedule them."
          }
          action={
            items.length ? (
              <button
                type="button"
                onClick={resetFilters}
                className="inline-flex min-h-10 items-center justify-center rounded-lg border border-border bg-background px-4 text-sm font-black text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/25"
              >
                Reset filters
              </button>
            ) : (
              <a
                href={academyHref}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground"
              >
                <BookOpenCheck className="h-4 w-4" />
                Open Teacher Academy
              </a>
            )
          }
        />
      )}
    </>
  );
}

function AnnouncementsContent({ announcements }: { announcements: Row[] }) {
  const [activeTab, setActiveTab] = useState<"all" | "published" | "draft" | "urgent">("all");
  const publishedCount = announcements.filter((row) => asText(row.status).toLowerCase() === "published").length;
  const draftCount = announcements.filter((row) => asText(row.status).toLowerCase() === "draft").length;
  const urgentCount = announcements.filter((row) => ["urgent", "high"].includes(asText(row.priority).toLowerCase())).length;
  const pinnedCount = announcements.filter((row) => Boolean(row.pinned)).length;
  const tabs = [
    { key: "all" as const, label: "All", count: announcements.length, detail: "visible", tone: "info" },
    { key: "published" as const, label: "Published", count: publishedCount, detail: "live", tone: "success" },
    { key: "draft" as const, label: "Drafts", count: draftCount, detail: "draft", tone: draftCount ? "warning" : "default" },
    { key: "urgent" as const, label: "Urgent", count: urgentCount, detail: `${pinnedCount} pinned`, tone: urgentCount ? "danger" : "default" },
  ];
  const filteredAnnouncements = announcements.filter((row) => {
    if (activeTab === "all") return true;
    if (activeTab === "published") return asText(row.status).toLowerCase() === "published";
    if (activeTab === "draft") return asText(row.status).toLowerCase() === "draft";
    return ["urgent", "high"].includes(asText(row.priority).toLowerCase());
  });

  return (
    <>
      <div className="grid grid-cols-4 gap-2" role="tablist" aria-label="Announcement filters">
        {tabs.map((tab) => {
          const selected = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              role="tab"
              aria-selected={selected}
              className={`min-h-[3.875rem] rounded-lg border px-2 py-2 text-left shadow-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                selected
                  ? "border-primary/30 bg-primary text-primary-foreground"
                  : "border-border bg-card text-card-foreground hover:bg-muted"
              }`}
            >
              <span className={`block truncate text-[9px] font-black uppercase leading-3 tracking-wide ${selected ? "text-primary-foreground/80" : "text-muted-foreground"}`}>
                {tab.label}
              </span>
              <span className="mt-0.5 block truncate text-lg font-black leading-none tabular-nums sm:text-xl">{tab.count}</span>
              <span className={`mt-0.5 block truncate text-[10px] font-semibold leading-3 ${selected ? "text-primary-foreground/75" : "text-muted-foreground"}`}>
                {tab.detail}
              </span>
            </button>
          );
        })}
      </div>

      {filteredAnnouncements.length ? (
        <section className="grid gap-3">
          {filteredAnnouncements.map((item, index) => {
            const title = asText(item.title) || "Announcement";
            const status = asText(item.status) || "draft";
            const priority = asText(item.priority) || "normal";
            const audience = asText(item.audience) || "all";
            return (
              <article key={`${asText(item.id) || title}-${index}`} className="rounded-lg border border-border bg-surface p-3 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="break-words text-base font-black text-foreground">{title}</h2>
                      <StatusBadge tone={statusTone(status)} className="text-[10px]">{status}</StatusBadge>
                      <StatusBadge tone={priorityTone(priority)} className="text-[10px]">Priority: {priority}</StatusBadge>
                      {item.pinned ? <StatusBadge tone="info" className="text-[10px]">Pinned</StatusBadge> : null}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                      {asText(item.body) || "No message body."}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
                    <span className="rounded-full border border-border bg-muted px-2 py-1">Audience: {audience}</span>
                    <span className="rounded-full border border-border bg-muted px-2 py-1">Status: {status}</span>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      ) : (
        <EmptyState
          icon={<Megaphone className="h-6 w-6" />}
          title={announcements.length ? `No ${activeTab} announcements` : "No announcements yet"}
          detail={announcements.length ? "Choose a different announcement tab." : "Existing announcement records will appear here when the announcement service returns them."}
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
  adminAcademyLessonEvents = [],
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
      ? "Scheduled Teacher Academy lessons within your subject scope."
      : "Scheduled Teacher Academy lessons across Academic Department.";
  const academyLessons = rowsFrom(adminAcademyLessonEvents);
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
              <a
                href="/?panel=announcements&audience=all"
                aria-label="Write announcement to everyone"
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-xs font-black text-primary-foreground"
              >
                <Plus className="h-4 w-4" />
                Write Announcement to Everyone
              </a>
            ) : (
              <a
                href={isHod ? routes.headOfDepartmentTeacherAcademy : routes.academicDirectorTeacherAcademy}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-xs font-black text-primary-foreground"
              >
                <BookOpenCheck className="h-4 w-4" />
                Schedule Academy Lesson
              </a>
            )}
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
        <TimetableContent academyLessons={academyLessons} isHod={isHod} />
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
