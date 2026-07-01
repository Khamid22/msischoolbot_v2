import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Check, Copy, Eye, Filter, Pencil, Plus, Search, UserPlus, Users, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { Pagination } from "@/shared/ui/Pagination";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, formatLastSeen, getStudentCode, getStudentRowId, parseTimestampUtc } from "../shared";

type ActivityFilter = "all" | "recent" | "inactive" | "never";
const STUDENTS_PAGE_SIZE = 10;

type CreatedStudent = {
  studentCode?: string;
  password?: string;
  fullName?: string;
  schoolName?: string;
  subjectName?: string;
  groupName?: string;
};

function AddStudentModal({
  schools,
  groups,
  csrf,
  onClose,
}: {
  schools: Array<Record<string, unknown>>;
  groups: Array<Record<string, unknown>>;
  csrf: string;
  onClose: () => void;
}) {
  const [schoolCode, setSchoolCode] = useState(() => asString(schools[0]?.code));
  const [fullName, setFullName] = useState("");
  const [groupId, setGroupId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CreatedStudent | null>(null);
  const [copied, setCopied] = useState(false);

  const schoolGroups = useMemo(
    () => groups.filter((group) => asString(group.school_code) === schoolCode),
    [groups, schoolCode],
  );

  useEffect(() => {
    // Keep the group valid whenever the chosen school changes.
    setGroupId(asString(schoolGroups[0]?.id));
  }, [schoolGroups]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(routes.adminStudentsApi, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ full_name: fullName.trim(), group_id: Number(groupId) }),
      });
      const json = await res.json();
      if (!res.ok || !json.ok) {
        setError(asString(json.message) || "Could not add student.");
        return;
      }
      setCreated(json.student as CreatedStudent);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    // After a successful create, reload so the server-rendered list includes
    // the new student; otherwise just dismiss.
    if (created) window.location.reload();
    else onClose();
  }

  async function copyCredentials() {
    if (!created) return;
    const text = `Student code: ${asString(created.studentCode)}\nPassword: ${asString(created.password)}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-md overflow-hidden rounded-xl bg-surface shadow-card-hover"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <h3 className="inline-flex items-center gap-2 text-sm font-bold">
            <UserPlus className="h-4 w-4 text-info" />
            Add Student
          </h3>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {created ? (
          <div className="space-y-4 px-4 py-4">
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
              <p className="text-sm font-bold text-emerald-800">{asString(created.fullName)} added</p>
              <p className="mt-0.5 text-xs text-emerald-700">
                Enrolled in {asString(created.groupName)} · {asString(created.subjectName)} · {asString(created.schoolName)}
              </p>
            </div>
            <div className="rounded-lg border border-foreground/10 bg-background p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Login credentials</p>
              <div className="mt-2 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[11px] text-muted-foreground">Student code</p>
                  <p className="text-sm font-bold">{asString(created.studentCode)}</p>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground">Password</p>
                  <p className="text-sm font-bold">{asString(created.password)}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={copyCredentials}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-foreground/10 px-2.5 py-1.5 text-xs font-bold text-muted-foreground hover:bg-muted"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? "Copied" : "Copy credentials"}
              </button>
              <p className="mt-2 text-[11px] text-muted-foreground">
                The initial password is the student code. Share it with the student to log in.
              </p>
            </div>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-3 px-4 py-4">
            {error ? (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p>
            ) : null}
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Full Name</span>
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                placeholder="e.g. Гафурова Амина"
                className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Client School</span>
              <select
                value={schoolCode}
                onChange={(event) => setSchoolCode(event.target.value)}
                required
                className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              >
                {schools.map((school) => (
                  <option key={asString(school.code)} value={asString(school.code)}>
                    {asString(school.name)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Group</span>
              <select
                value={groupId}
                onChange={(event) => setGroupId(event.target.value)}
                required
                disabled={schoolGroups.length === 0}
                className="w-full rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30 disabled:opacity-50"
              >
                {schoolGroups.length === 0 ? (
                  <option value="">No groups for this school</option>
                ) : (
                  schoolGroups.map((group) => (
                    <option key={asNumber(group.id)} value={asString(group.id)}>
                      {asString(group.name)} · {asString(group.subject_name)}
                    </option>
                  ))
                )}
              </select>
              <span className="mt-1 block text-[11px] text-muted-foreground">
                The group sets the student's subject and school. The gradebook will show them right away.
              </span>
            </label>
            <div className="flex justify-end gap-2 border-t border-foreground/8 pt-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg bg-muted px-4 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !fullName.trim() || !groupId}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-4 w-4" />
                {submitting ? "Adding..." : "Add Student"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

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
  const timestamp = parseTimestampUtc(raw);
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

  const props = state.props || {};
  const isTeacherMode = asString(state.adminMode).toLowerCase() === "teacher";
  const academicSchools = Array.isArray(props.adminAcademicSchools) ? props.adminAcademicSchools : [];
  const academicGroups = Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [];
  const csrf = asString(props.csrfToken);

  const [subjectFilter, setSubjectFilter] = useState("all");
  const [activityFilter, setActivityFilter] = useState<ActivityFilter>("all");
  const [addOpen, setAddOpen] = useState(false);
  const [page, setPage] = useState(1);
  const canAddStudents = !isTeacherMode && academicSchools.length > 0 && academicGroups.length > 0;

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

  const totalPages = Math.max(1, Math.ceil(visibleStudents.length / STUDENTS_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedStudents = visibleStudents.slice(
    (currentPage - 1) * STUDENTS_PAGE_SIZE,
    currentPage * STUDENTS_PAGE_SIZE,
  );

  useEffect(() => {
    setPage(1);
  }, [activityFilter, searchQuery, subjectFilter, currentSchool]);

  return (
    <div className="workspace-fit flex flex-col gap-3 lg:h-full lg:min-h-0">
      {addOpen && !isTeacherMode ? (
        <AddStudentModal
          schools={academicSchools}
          groups={academicGroups}
          csrf={csrf}
          onClose={() => setAddOpen(false)}
        />
      ) : null}
      <div className="grid shrink-0 gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Students" value={stats.total} hint={`${filteredStudents.length} before filters`} />
        <MetricCard label="Recently Active" value={stats.recent} hint="Seen in the last 7 days" />
        <MetricCard label="Subjects" value={stats.subjects} hint="In current results" />
        <MetricCard label="Never Seen" value={stats.never} hint="No activity recorded" />
      </div>

      <div className="shrink-0 rounded-lg bg-background/95 pb-2 pt-1">
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-[minmax(200px,1fr)_170px_170px_190px]">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Name, student code, subject, or school"
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
        className="flex min-h-0 flex-1 flex-col"
        bodyClassName="flex min-h-0 flex-1 flex-col gap-2"
        headerActions={
          <div className="flex items-center gap-2">
            {!isTeacherMode ? (
              <button
                type="button"
                onClick={() => setAddOpen(true)}
                disabled={!canAddStudents}
                title={canAddStudents ? "Add a new student" : "Add a client school and group first"}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Student
              </button>
            ) : null}
            <span className="hidden items-center gap-1.5 rounded-lg border border-foreground/10 px-2.5 py-1.5 text-xs font-semibold text-muted-foreground sm:inline-flex">
              <Filter className="h-3.5 w-3.5" />
              {subjectFilter === "all" ? "All subjects" : subjectFilter}
            </span>
          </div>
        }
      >
        {visibleStudents.length ? (
          <div className="space-y-2 sm:hidden">
            {pagedStudents.map((student: Record<string, unknown>) => {
              const seen = formatLastSeen(student.last_seen_at);
              const studentRowId = getStudentRowId(student);
              const studentCode = getStudentCode(student);
              return (
                <div key={`${studentRowId}-mobile`} className="rounded-lg border border-foreground/8 bg-background p-3">
                  <div className="flex items-start gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold">
                      {initialsFor(student.full_name) || "ST"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <a
                        href={routes.adminStudentPanel(studentRowId, currentSchool)}
                        className="block break-words text-sm font-bold leading-snug hover:underline"
                      >
                        {asString(student.full_name)}
                      </a>
                      <p className="mt-0.5 text-xs text-muted-foreground">Code {studentCode || "-"}</p>
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">{asString(student.school_name)}</p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <a
                        href={routes.adminStudentPanel(studentRowId, currentSchool)}
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
                        aria-label={`Open ${asString(student.full_name)} dashboard`}
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </a>
                      <a
                        href={routes.adminStudentProfile(studentRowId)}
                        className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
                        aria-label={`Edit ${asString(student.full_name)}`}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {subjectList(student.subjects).slice(0, 3).map((subject) => (
                      <span
                        key={`${studentRowId}-mobile-${subject}`}
                        title={subject}
                        className="max-w-[160px] truncate rounded border border-foreground/10 bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground"
                      >
                        {subject}
                      </span>
                    ))}
                  </div>
                  <p className={`mt-2 text-xs ${seen.online ? "font-semibold text-green-600" : "text-muted-foreground"}`}>
                    {seen.label}
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="rounded-lg border border-dashed border-foreground/15 bg-background px-3 py-8 text-center text-sm text-muted-foreground sm:hidden">
            No students match your filters.
          </p>
        )}

        <div className="hidden min-h-0 flex-1 overflow-y-auto rounded-lg border border-foreground/8 sm:block">
          <table className="h-full w-full table-fixed text-left">
            <thead className="sticky top-0 z-20 bg-surface shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
              <tr className="border-b border-foreground/5">
                {["Student", "Student Code", "Subjects", "School", "Last Seen", ""].map((heading) => (
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
                pagedStudents.map((student: Record<string, unknown>) => {
                  const seen = formatLastSeen(student.last_seen_at);
                  const studentRowId = getStudentRowId(student);
                  const studentCode = getStudentCode(student);
                  return (
                    <tr key={studentRowId} className="border-b border-foreground/5 hover:bg-muted/40">
                      <td className="w-[30%] px-3 py-2.5">
                        <a
                          href={routes.adminStudentPanel(studentRowId, currentSchool)}
                          className="flex min-w-0 items-center gap-3 hover:underline"
                        >
                          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold">
                            {initialsFor(student.full_name) || "ST"}
                          </span>
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-semibold">{asString(student.full_name)}</span>
                            <span className="block truncate text-xs text-muted-foreground">Code {studentCode || "-"}</span>
                          </span>
                        </a>
                      </td>
                      <td className="w-[12%] px-3 py-2.5 text-xs font-bold">{studentCode || "-"}</td>
                      <td className="w-[26%] px-3 py-2.5">
                        <div className="flex flex-wrap items-center gap-1">
                          {subjectList(student.subjects).slice(0, 2).map((subject) => (
                            <span
                              key={`${studentRowId}-${subject}`}
                              title={subject}
                              className="max-w-[150px] truncate rounded border border-foreground/10 bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground"
                            >
                              {subject}
                            </span>
                          ))}
                          {subjectList(student.subjects).length > 2 ? (
                            <span className="rounded border border-foreground/10 bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
                              +{subjectList(student.subjects).length - 2}
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td className="w-[14%] truncate px-3 py-2.5 text-xs text-muted-foreground">{asString(student.school_name)}</td>
                      <td className="w-[12%] px-3 py-2.5 text-xs">
                        <span className={seen.online ? "font-semibold text-green-600" : "text-muted-foreground"}>
                          {seen.label}
                        </span>
                      </td>
                      <td className="w-[4%] px-3 py-2.5">
                        <div className="flex justify-end gap-1.5">
                          <a
                            href={routes.adminStudentPanel(studentRowId, currentSchool)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
                            aria-label={`Open ${asString(student.full_name)} dashboard`}
                            title="Dashboard"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </a>
                          <a
                            href={routes.adminStudentProfile(studentRowId)}
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
        <Pagination
          page={currentPage}
          totalPages={totalPages}
          onPageChange={setPage}
          label={`Showing ${pagedStudents.length} of ${visibleStudents.length} students`}
        />
      </ChartCard>
    </div>
  );
}
