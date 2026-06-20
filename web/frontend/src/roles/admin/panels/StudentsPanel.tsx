import { useMemo, useState } from "react";
import { Eye, Filter, Pencil, Search, Users } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { adminStickyTop, asNumber, asString, formatLastSeen } from "../shared";

type ActivityFilter = "all" | "recent" | "inactive" | "never";

function subjectList(value: unknown) {
  return asString(value)
    .split(",")
    .map((item) => asString(item))
    .filter(Boolean);
}

function initialsFor(name: unknown) {
  const parts = asString(name).split(/\s+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("");
}

function activityBucket(lastSeen: unknown): ActivityFilter {
  const raw = typeof lastSeen === "string" ? lastSeen.trim() : "";
  if (!raw) return "never";
  const timestamp = Date.parse(raw);
  if (!Number.isFinite(timestamp)) return "never";
  const diffDays = (Date.now() - timestamp) / 86_400_000;
  return diffDays <= 7 ? "recent" : "inactive";
}

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint: string;
}) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-surface px-3 py-3">
      <p className="text-xs font-semibold text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-bold leading-none">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

export default function StudentsPanel({ state }: { state: any }) {
  const {
    searchQuery,
    setSearchQuery,
    currentSchool,
    schoolOptions,
    filteredStudents,
  } = state;

  const [subjectFilter, setSubjectFilter] = useState("all");
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");

  const subjectOptions = useMemo(() => {
    const subjects = new Set<string>();
    filteredStudents.forEach((student: Record<string, unknown>) => {
      subjectList(student.subjects).forEach((subject) => subjects.add(subject));
    });
    return Array.from(subjects).sort((left, right) => left.localeCompare(right));
  }, [filteredStudents]);

  const visibleStudents = useMemo(
    () =>
      filteredStudents.filter((student: Record<string, unknown>) => {
        const subjects = subjectList(student.subjects);
        const matchesSubject = subjectFilter === "all" || subjects.includes(subjectFilter);
        const bucket = activityBucket(student.last_seen_at);
        const matchesActivity = activityFilter === "all" || bucket === activityFilter;
        return matchesSubject && matchesActivity;
      }),
    [activityFilter, filteredStudents, subjectFilter],
  );

  const stats = useMemo(() => {
    const schoolSet = new Set<string>();
    const subjectSet = new Set<string>();
    let recent = 0;
    let never = 0;

    visibleStudents.forEach((student: Record<string, unknown>) => {
      const school = asString(student.school_name);
      if (school) schoolSet.add(school);
      subjectList(student.subjects).forEach((subject) => subjectSet.add(subject));
      const bucket = activityBucket(student.last_seen_at);
      if (bucket === "recent") recent += 1;
      if (bucket === "never") never += 1;
    });

    return {
      total: visibleStudents.length,
      schools: schoolSet.size,
      subjects: subjectSet.size,
      recent,
      never,
    };
  }, [visibleStudents]);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Students" value={stats.total} hint={`${filteredStudents.length} before filters`} />
        <MetricCard label="Recently Active" value={stats.recent} hint="Seen in the last 7 days" />
        <MetricCard label="Subjects" value={stats.subjects} hint="In current results" />
        <MetricCard label="Never Seen" value={stats.never} hint="No activity recorded" />
      </div>

      <div
        className="sticky z-30 -mx-3 bg-background/95 px-3 pb-3 pt-1 backdrop-blur sm:-mx-4 sm:px-4 md:-mx-6 md:px-6"
        style={{ top: adminStickyTop }}
      >
        <div className="grid gap-2 lg:grid-cols-[minmax(220px,1fr),190px,190px,210px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Name, ID, subject, or school"
              className="h-10 w-full rounded-lg border border-foreground/10 bg-surface pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
            />
          </label>

          <select
            value={subjectFilter}
            onChange={(event) => setSubjectFilter(event.target.value)}
            className="h-10 rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-medium outline-none focus:border-foreground/30"
            aria-label="Subject"
          >
            <option value="all">All subjects</option>
            {subjectOptions.map((subject) => (
              <option key={subject} value={subject}>
                {subject}
              </option>
            ))}
          </select>

          <select
            value={activityFilter}
            onChange={(event) => setActivityFilter(event.target.value as ActivityFilter)}
            className="h-10 rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-medium outline-none focus:border-foreground/30"
            aria-label="Activity"
          >
            <option value="all">All activity</option>
            <option value="recent">Recently active</option>
            <option value="inactive">Inactive</option>
            <option value="never">Never seen</option>
          </select>

          <form action="/" method="get">
            <input type="hidden" name="panel" value="students" />
            <select
              name="school"
              defaultValue={currentSchool}
              onChange={(event) => event.currentTarget.form?.submit()}
              className="h-10 w-full rounded-lg border border-foreground/10 bg-surface px-3 text-sm font-semibold outline-none focus:border-foreground/30"
              aria-label="School"
            >
              {schoolOptions.map((option: { code: string; label: string }) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </form>
        </div>
      </div>

      <ChartCard
        title="Students"
        subtitle={`${visibleStudents.length} shown`}
        icon={<Users className="h-4 w-4 text-info" />}
        headerActions={
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-foreground/10 px-2.5 py-1.5 text-xs font-semibold text-muted-foreground">
            <Filter className="h-3.5 w-3.5" />
            {subjectFilter === "all" ? "All subjects" : subjectFilter}
          </span>
        }
      >
        <div className="max-h-[68dvh] overflow-auto">
          <table className="w-full min-w-[860px] text-left">
            <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/5">
                {["Student", "ID", "Subjects", "School", "Last Seen", ""].map((heading) => (
                  <th
                    key={heading || "actions"}
                    className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground"
                  >
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleStudents.length ? (
                visibleStudents.map((student: Record<string, unknown>) => {
                  const seen = formatLastSeen(student.last_seen_at);
                  const studentId = asNumber(student.id);
                  return (
                    <tr key={studentId} className="border-b border-foreground/5 hover:bg-muted/40">
                      <td className="px-3 py-2.5">
                        <a
                          href={routes.adminStudentDashboard(studentId, currentSchool)}
                          className="flex min-w-0 items-center gap-3 hover:underline"
                        >
                          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold">
                            {initialsFor(student.full_name) || "ST"}
                          </span>
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-semibold">{asString(student.full_name)}</span>
                            <span className="block truncate text-xs text-muted-foreground">{asString(student.student_id)}</span>
                          </span>
                        </a>
                      </td>
                      <td className="px-3 py-2.5 text-xs font-bold">{asString(student.student_id)}</td>
                      <td className="px-3 py-2.5">
                        <div className="flex max-w-xs flex-wrap gap-1">
                          {subjectList(student.subjects).map((subject) => (
                            <span
                              key={`${studentId}-${subject}`}
                              className="rounded-md border border-foreground/10 bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground"
                            >
                              {subject}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{asString(student.school_name)}</td>
                      <td className="px-3 py-2.5 text-xs">
                        <span className={seen.online ? "font-semibold text-green-600" : "text-muted-foreground"}>
                          {seen.label}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex justify-end gap-1.5">
                          <a
                            href={routes.adminStudentDashboard(studentId, currentSchool)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
                            aria-label={`Open ${asString(student.full_name)} dashboard`}
                            title="Dashboard"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </a>
                          <a
                            href={routes.adminStudentProfile(studentId)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
                            aria-label={`Edit ${asString(student.full_name)}`}
                            title="Edit"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-sm text-muted-foreground">
                    No students match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  );
}
