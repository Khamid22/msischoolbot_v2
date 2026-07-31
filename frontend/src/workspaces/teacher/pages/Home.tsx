import { useMemo, useState, type ReactNode } from "react";
import {
  BookOpen,
  BookMarked,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleUserRound,
  Clock3,
  FileText,
  GraduationCap,
  Home,
  KeyRound,
  LogOut,
  Mail,
  MessageSquareText,
  Phone,
  Sparkles,
  Target,
  Trophy,
  UserRoundCheck,
} from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { TeacherSubjectCurriculum } from "@/features/academics/subject-curriculum/TeacherSubjectCurriculum";
import type { SubjectCurriculumCatalog } from "@/features/academics/subject-curriculum/model";

type TeacherHomeProps = {
  authLogin?: string;
  academyTeacher?: Record<string, unknown> | null;
  teacherProfile?: Record<string, unknown> | null;
  subjectCurriculumCatalog?: SubjectCurriculumCatalog;
  initialTab?: string;
  csrfToken?: string;
};

type AcademyTab = "overview" | "lessons" | "curriculum" | "timetable" | "updates" | "profile";
type AcademyRecord = Record<string, unknown>;

const tabItems: Array<{ key: AcademyTab; label: string; icon: typeof Home }> = [
  { key: "overview", label: "Overview", icon: Home },
  { key: "lessons", label: "Lessons", icon: BookOpen },
  { key: "curriculum", label: "Curriculum", icon: BookMarked },
  { key: "timetable", label: "Schedule", icon: CalendarDays },
  { key: "updates", label: "Updates", icon: MessageSquareText },
  { key: "profile", label: "Profile", icon: CircleUserRound },
];

function asText(value: unknown, fallback = "Not set") {
  const text = typeof value === "string" || typeof value === "number" ? String(value).trim() : "";
  return text || fallback;
}

function asNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function asRecords(value: unknown): AcademyRecord[] {
  return Array.isArray(value) ? value.filter((item): item is AcademyRecord => Boolean(item) && typeof item === "object") : [];
}

function dateValue(value: unknown) {
  if (!value) return null;
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value: unknown, includeTime = false) {
  const date = dateValue(value);
  if (!date) return "Not scheduled";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Tashkent",
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "T";
}

function assignmentStatus(status: unknown) {
  const normalized = asText(status, "assigned").toLowerCase();
  if (["passed", "accepted", "completed"].includes(normalized)) {
    return { label: normalized === "completed" ? "Completed" : "Passed", className: "bg-success/12 text-success" };
  }
  if (["failed", "returned", "needs_improvement"].includes(normalized)) {
    return { label: "Needs review", className: "bg-destructive/10 text-destructive" };
  }
  if (["assessed", "submitted"].includes(normalized)) {
    return { label: "Assessed", className: "bg-info/12 text-info" };
  }
  return { label: "Assigned", className: "bg-primary/10 text-primary" };
}

function SectionCard({ title, icon, action, children, className = "" }: { title: string; icon: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`overflow-hidden rounded-xl border border-border/80 bg-surface shadow-card ${className}`}>
      <header className="flex min-h-12 items-center justify-between gap-3 border-b border-border/70 px-4 py-2.5">
        <h2 className="flex min-w-0 items-center gap-2 text-sm font-black text-foreground">
          <span className="text-primary">{icon}</span>
          {title}
        </h2>
        {action}
      </header>
      {children}
    </section>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return <p className="m-3 rounded-lg border border-dashed border-border bg-muted/35 px-4 py-8 text-center text-sm font-semibold text-muted-foreground">{children}</p>;
}

function AcademyNav({ activeTab, onChange, mobile = false }: { activeTab: AcademyTab; onChange: (tab: AcademyTab) => void; mobile?: boolean }) {
  const items = mobile ? tabItems.filter(({ key }) => key !== "updates") : tabItems;
  if (mobile) {
    return (
      <nav
        aria-label="Teacher Academy navigation"
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-border/80 bg-surface/95 px-1 pt-1.5 shadow-[0_-0.5rem_1.5rem_hsl(var(--foreground)/0.08)] backdrop-blur md:hidden"
        style={{ paddingBottom: "calc(var(--app-bottom-inset) + 0.375rem)" }}
      >
        {items.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            aria-current={activeTab === key ? "page" : undefined}
            onClick={() => onChange(key)}
            className={`flex min-h-12 min-w-0 flex-col items-center justify-center gap-0.5 rounded-lg px-1 text-[0.625rem] font-black focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
              activeTab === key ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Icon className="h-[1.125rem] w-[1.125rem]" aria-hidden="true" />
            <span className="truncate">{label}</span>
          </button>
        ))}
      </nav>
    );
  }

  return (
    <nav aria-label="Teacher Academy navigation" className="mt-7 space-y-1 px-3">
      {items.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          aria-current={activeTab === key ? "page" : undefined}
          onClick={() => onChange(key)}
          className={`flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm font-black focus:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring ${
            activeTab === key ? "bg-sidebar-primary text-sidebar-primary-foreground" : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          }`}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
          {label}
        </button>
      ))}
    </nav>
  );
}

export default function TeacherHome({
  authLogin = "",
  academyTeacher = null,
  teacherProfile = null,
  subjectCurriculumCatalog,
  initialTab = "overview",
  csrfToken = "",
}: TeacherHomeProps) {
  const validInitialTab = tabItems.some(({ key }) => key === initialTab)
    ? (initialTab as AcademyTab)
    : "overview";
  const [activeTab, setActiveTab] = useState<AcademyTab>(validInitialTab);
  const teacher = academyTeacher ?? teacherProfile ?? {};
  const progress = teacher.progress && typeof teacher.progress === "object" ? (teacher.progress as AcademyRecord) : {};
  const assignments = useMemo(
    () => asRecords(teacher.assignments).sort((a, b) => asNumber(a.sequence_no) - asNumber(b.sequence_no)),
    [teacher.assignments],
  );
  const assessments = useMemo(
    () => asRecords(teacher.assessments).sort((a, b) => (dateValue(b.assessment_datetime)?.getTime() ?? 0) - (dateValue(a.assessment_datetime)?.getTime() ?? 0)),
    [teacher.assessments],
  );
  const assessmentByAssignment = useMemo(() => {
    const index = new Map<string, AcademyRecord>();
    assessments.forEach((assessment) => {
      const key = asText(assessment.lesson_assignment_id, "");
      if (key && !index.has(key)) index.set(key, assessment);
    });
    return index;
  }, [assessments]);
  const scheduledAssignments = useMemo(
    () => assignments.filter((assignment) => dateValue(assignment.session_datetime)).sort((a, b) => (dateValue(a.session_datetime)?.getTime() ?? 0) - (dateValue(b.session_datetime)?.getTime() ?? 0)),
    [assignments],
  );

  const name = asText(teacher.full_name, "Academy teacher");
  const assignedSubjects = asRecords(teacher.subjects);
  const subject = asText(
    teacher.subject_program_name,
    asText(teacher.subject, asText(assignedSubjects[0]?.name, "Subject not assigned")),
  );
  const academyStatus = asText(teacher.academy_status, "In Academy").replace(/_/g, " ");
  const assignedCount = asNumber(progress.assigned_count || assignments.length);
  const assessedCount = asNumber(progress.assessed_count || assessments.length);
  const passedCount = asNumber(progress.passed_count);
  const averageScore = asNumber(progress.average_score);
  const targetLessons = Math.max(asNumber(progress.target_lessons), assignedCount, 1);
  const completion = Math.min(100, Math.round((assessedCount / targetLessons) * 100));
  const nextAssignment = progress.next_assignment && typeof progress.next_assignment === "object"
    ? (progress.next_assignment as AcademyRecord)
    : scheduledAssignments.find((assignment) => (dateValue(assignment.session_datetime)?.getTime() ?? 0) >= Date.now()) ?? assignments.find((assignment) => !assessmentByAssignment.has(asText(assignment.id, "")));
  const latestAssessment = assessments[0];

  const updates = useMemo(() => {
    const items = [
      ...assignments.map((assignment) => ({
        id: `assignment-${asText(assignment.id, asText(assignment.sequence_no, "unknown"))}`,
        title: `Lesson ${asText(assignment.lesson_number, asText(assignment.sequence_no, ""))} assigned`,
        detail: asText(assignment.lesson_topic, "Academy lesson"),
        date: assignment.session_datetime || assignment.created_at,
        type: "Lesson",
      })),
      ...assessments.map((assessment) => ({
        id: `assessment-${asText(assessment.id, "unknown")}`,
        title: `Assessment recorded · ${asText(assessment.decision, "Reviewed")}`,
        detail: `Lesson ${asText(assessment.lesson_number, "")} · ${asText(assessment.lesson_topic, "Academy lesson")}`,
        date: assessment.assessment_datetime || assessment.created_at,
        type: "Report",
      })),
    ];
    return items.sort((a, b) => (dateValue(b.date)?.getTime() ?? 0) - (dateValue(a.date)?.getTime() ?? 0));
  }, [assignments, assessments]);

  if (!academyTeacher && !teacherProfile) {
    return (
      <main className="flex min-h-[var(--tg-viewport-height)] items-center justify-center bg-background px-4 text-foreground">
        <section className="w-full max-w-md rounded-2xl border border-border bg-surface p-7 text-center shadow-card">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-sidebar text-white"><GraduationCap className="h-6 w-6" /></span>
          <h1 className="mt-4 text-lg font-black">Your Academy profile isn't available yet.</h1>
          <p className="mt-2 text-sm font-semibold text-muted-foreground">Please contact your Academic Director. Your teacher account is signed in correctly.</p>
          <div className="mt-5 grid gap-2 sm:grid-cols-2">
            <a href={routes.accountSecurity} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border bg-background px-4 text-sm font-black focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"><KeyRound className="h-4 w-4" />Password</a>
            <form action={routes.logout} method="post">
              <input type="hidden" name="csrf_token" value={csrfToken} />
              <button type="submit" className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"><LogOut className="h-4 w-4" />Logout</button>
            </form>
          </div>
        </section>
      </main>
    );
  }

  return (
    <div className="min-h-[var(--tg-viewport-height)] overflow-x-hidden bg-muted/35 text-foreground md:flex">
      <aside className="sticky top-0 hidden h-dvh w-[var(--workspace-sidebar-width)] shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex">
        <div className="flex items-center gap-3 border-b border-sidebar-border px-4 py-5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sidebar-primary text-sidebar-primary-foreground"><GraduationCap className="h-5 w-5" /></span>
          <div className="min-w-0">
            <p className="truncate text-sm font-black">MSI School</p>
            <p className="truncate text-xs font-semibold text-sidebar-foreground/55">Teacher Workspace</p>
          </div>
        </div>
        <AcademyNav activeTab={activeTab} onChange={setActiveTab} />
        <div className="mt-auto border-t border-sidebar-border p-3">
          <div className="mb-2 flex items-center gap-2 rounded-lg px-2 py-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sidebar-foreground text-xs font-black text-sidebar">{initials(name)}</span>
            <div className="min-w-0"><p className="truncate text-xs font-black">{name}</p><p className="truncate text-[0.6875rem] text-sidebar-foreground/55">{authLogin || "Teacher"}</p></div>
          </div>
          <div className="grid grid-cols-2 gap-1">
            <a href={routes.accountSecurity} className="flex min-h-11 items-center justify-center rounded-lg text-sidebar-foreground/65 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring" aria-label="Change password"><KeyRound className="h-4 w-4" /></a>
            <form action={routes.logout} method="post"><input type="hidden" name="csrf_token" value={csrfToken} /><button type="submit" className="flex min-h-11 w-full items-center justify-center rounded-lg text-sidebar-foreground/65 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring" aria-label="Log out"><LogOut className="h-4 w-4" /></button></form>
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 border-b border-border/80 bg-surface/95 backdrop-blur md:hidden" style={{ paddingTop: "var(--app-top-inset)" }}>
          <div className="flex min-h-14 items-center gap-3 px-4">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-sidebar text-white"><GraduationCap className="h-5 w-5" /></span>
            <div className="min-w-0"><p className="truncate text-sm font-black">{name}</p><p className="truncate text-xs font-semibold text-muted-foreground">Teacher Workspace · {authLogin}</p></div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[var(--workspace-content-max-width)] px-3 py-4 pb-[calc(var(--app-bottom-inset)+5.5rem)] sm:px-5 md:px-[var(--workspace-gutter-desktop)] md:py-6 md:pb-8">
          {activeTab === "overview" && (
            <div className="space-y-4">
              <section className="overflow-hidden rounded-xl border border-primary/15 bg-surface shadow-card">
                <div className="grid gap-5 p-4 sm:p-5 lg:grid-cols-[1fr_auto] lg:items-center">
                  <div className="flex min-w-0 items-start gap-3 sm:items-center">
                    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-sm font-black text-primary-foreground">{initials(name)}</span>
                    <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h1 className="truncate font-display text-xl font-black sm:text-2xl">{name}</h1><span className="rounded-full bg-warning/15 px-2.5 py-1 text-[0.625rem] font-black uppercase tracking-wide text-warning">{academyStatus}</span></div><p className="mt-1 text-sm font-semibold text-muted-foreground">{subject}</p></div>
                  </div>
                  <div className="min-w-[13rem]">
                    <div className="mb-1.5 flex items-center justify-between text-xs font-black"><span>Academy progress</span><span>{completion}%</span></div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary transition-[width] motion-reduce:transition-none" style={{ width: `${completion}%` }} /></div>
                    <p className="mt-1.5 text-[0.6875rem] font-semibold text-muted-foreground">{assessedCount} of {targetLessons} lessons assessed</p>
                  </div>
                </div>
              </section>

              <section aria-label="Academy progress metrics" className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
                {[
                  { label: "Assigned", value: assignedCount, detail: "lessons", icon: BookOpen, tone: "bg-info/10 text-info" },
                  { label: "Assessed", value: assessedCount, detail: `of ${targetLessons}`, icon: Clock3, tone: "bg-primary/10 text-primary" },
                  { label: "Passed", value: passedCount, detail: "accepted", icon: Trophy, tone: "bg-success/10 text-success" },
                  { label: "Average", value: averageScore ? averageScore.toFixed(1) : "—", detail: "weighted", icon: Target, tone: "bg-warning/10 text-warning" },
                ].map(({ label, value, detail, icon: Icon, tone }) => (
                  <article key={label} className="rounded-xl border border-border/80 bg-surface p-3.5 shadow-card"><div className="flex items-center justify-between gap-2"><p className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">{label}</p><span className={`flex h-8 w-8 items-center justify-center rounded-lg ${tone}`}><Icon className="h-4 w-4" /></span></div><p className="mt-3 text-2xl font-black">{value}</p><p className="text-xs font-semibold text-muted-foreground">{detail}</p></article>
                ))}
              </section>

              <div className="grid gap-4 lg:grid-cols-2">
                <SectionCard title="Next Academy lesson" icon={<CalendarDays className="h-4 w-4" />} action={<button type="button" onClick={() => setActiveTab("timetable")} className="min-h-9 rounded-lg px-2.5 text-xs font-black text-primary hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">View schedule</button>}>
                  {nextAssignment ? <div className="p-4"><p className="text-xs font-black uppercase tracking-wide text-primary">Lesson {asText(nextAssignment.lesson_number, asText(nextAssignment.sequence_no, ""))}</p><p className="mt-1 text-lg font-black">{asText(nextAssignment.lesson_topic, "Academy lesson")}</p><div className="mt-3 grid gap-2 text-xs font-semibold text-muted-foreground sm:grid-cols-2"><p className="flex items-center gap-2"><Clock3 className="h-4 w-4 text-primary" />{formatDate(nextAssignment.session_datetime, true)}</p><p className="flex items-center gap-2"><UserRoundCheck className="h-4 w-4 text-primary" />{asText(nextAssignment.evaluator_name, "Evaluator not assigned")}</p></div>{asText(nextAssignment.focus_areas, "") && <p className="mt-3 rounded-lg bg-muted/60 p-3 text-xs font-semibold text-muted-foreground">Focus: {asText(nextAssignment.focus_areas, "")}</p>}</div> : <EmptyState>No lesson has been assigned yet.</EmptyState>}
                </SectionCard>
                <SectionCard title="Latest assessment" icon={<FileText className="h-4 w-4" />} action={<button type="button" onClick={() => setActiveTab("lessons")} className="min-h-9 rounded-lg px-2.5 text-xs font-black text-primary hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">All reports</button>}>
                  {latestAssessment ? <div className="p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-wide text-muted-foreground">Lesson {asText(latestAssessment.lesson_number, "")}</p><p className="mt-1 font-black">{asText(latestAssessment.lesson_topic, "Assessment report")}</p></div><span className="rounded-lg bg-primary/10 px-3 py-1.5 text-lg font-black text-primary">{asNumber(latestAssessment.weighted_overall_score) || "—"}</span></div><p className="mt-3 text-xs font-semibold text-muted-foreground">{asText(latestAssessment.final_recommendation, asText(latestAssessment.areas_for_improvement, "Your assessment report is ready."))}</p></div> : <EmptyState>No assessment report has been recorded.</EmptyState>}
                </SectionCard>
              </div>
              {updates.length ? (
                <SectionCard title="Recent updates" icon={<Sparkles className="h-4 w-4" />}>
                  <ol className="divide-y divide-border/70">
                    {updates.slice(0, 3).map((item) => (
                      <li key={item.id} className="flex gap-3 px-4 py-3">
                        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                          {item.type === "Report" ? <CheckCircle2 className="h-4 w-4" /> : <BookOpen className="h-4 w-4" />}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-black">{item.title}</p>
                          <p className="mt-0.5 text-xs font-semibold text-muted-foreground">
                            {item.detail} · {formatDate(item.date, true)}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ol>
                </SectionCard>
              ) : null}
            </div>
          )}

          {activeTab === "lessons" && (
            <div className="space-y-4">
              <div><p className="text-xs font-black uppercase tracking-[0.16em] text-primary">Teacher Academy</p><h1 className="mt-1 font-display text-2xl font-black">Lessons & reports</h1><p className="mt-1 text-sm font-semibold text-muted-foreground">Open a lesson to see its assignment and assessment details.</p></div>
              <SectionCard title={`${assignments.length} selected lessons`} icon={<BookOpen className="h-4 w-4" />}>
                {assignments.length ? <div className="divide-y divide-border/70">{assignments.map((assignment, index) => {
                  const report = assessmentByAssignment.get(asText(assignment.id, ""));
                  const status = assignmentStatus(assignment.status);
                  return <details key={asText(assignment.id, String(index))} className="group"><summary className="flex min-h-16 cursor-pointer list-none items-center gap-3 px-4 py-3 hover:bg-muted/45 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40"><span className="w-7 shrink-0 text-center text-xs font-black text-muted-foreground">{asText(assignment.sequence_no, String(index + 1))}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-black">Lesson {asText(assignment.lesson_number, "")} · {asText(assignment.lesson_topic, "Academy lesson")}</p><p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{formatDate(assignment.session_datetime, true)} · {asText(assignment.evaluator_name, "Evaluator not assigned")}</p></div><span className={`hidden rounded-full px-2 py-1 text-[0.625rem] font-black uppercase sm:inline ${status.className}`}>{status.label}</span><ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-90 motion-reduce:transition-none" /></summary><div className="border-t border-border/60 bg-muted/25 px-4 py-4 sm:pl-14"><div className="grid gap-3 text-xs sm:grid-cols-2"><div><p className="font-black uppercase tracking-wide text-muted-foreground">Focus areas</p><p className="mt-1 font-semibold">{asText(assignment.focus_areas)}</p></div><div><p className="font-black uppercase tracking-wide text-muted-foreground">Trainee notes</p><p className="mt-1 font-semibold">{asText(assignment.notes_to_trainee)}</p></div></div>{report ? <div className="mt-4 rounded-lg border border-primary/15 bg-surface p-3"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-black">Assessment report</p><span className="rounded-md bg-primary/10 px-2.5 py-1 text-sm font-black text-primary">Score {asNumber(report.weighted_overall_score) || "—"}</span></div><div className="mt-3 grid gap-3 text-xs sm:grid-cols-2"><div><p className="font-black text-success">Strengths</p><p className="mt-1 font-semibold text-muted-foreground">{asText(report.strengths)}</p></div><div><p className="font-black text-warning">Improve next</p><p className="mt-1 font-semibold text-muted-foreground">{asText(report.areas_for_improvement)}</p></div></div>{asText(report.final_recommendation, "") && <p className="mt-3 border-t border-border pt-3 text-xs font-semibold"><span className="font-black">Recommendation:</span> {asText(report.final_recommendation, "")}</p>}</div> : <p className="mt-4 rounded-lg border border-dashed border-border bg-surface px-3 py-3 text-xs font-semibold text-muted-foreground">Assessment pending for this lesson.</p>}</div></details>;
                })}</div> : <EmptyState>No Academy lessons have been selected yet.</EmptyState>}
              </SectionCard>
            </div>
          )}

          {activeTab === "timetable" && (
            <div className="space-y-4">
              <div><p className="text-xs font-black uppercase tracking-[0.16em] text-primary">Teacher Academy</p><h1 className="mt-1 font-display text-2xl font-black">Lesson schedule</h1><p className="mt-1 text-sm font-semibold text-muted-foreground">All times are shown in Asia/Tashkent.</p></div>
              <SectionCard title="Scheduled lessons" icon={<CalendarDays className="h-4 w-4" />}>
                {scheduledAssignments.length ? <div className="divide-y divide-border/70">{scheduledAssignments.map((assignment, index) => <article key={asText(assignment.id, String(index))} className="grid gap-3 px-4 py-4 sm:grid-cols-[9rem_1fr_auto] sm:items-center"><div><p className="text-sm font-black text-primary">{formatDate(assignment.session_datetime, true)}</p><p className="mt-0.5 text-xs font-semibold text-muted-foreground">Asia/Tashkent</p></div><div className="min-w-0"><p className="truncate text-sm font-black">Lesson {asText(assignment.lesson_number, "")} · {asText(assignment.lesson_topic, "Academy lesson")}</p><p className="mt-1 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground"><UserRoundCheck className="h-3.5 w-3.5" />{asText(assignment.evaluator_name, "Evaluator not assigned")}</p></div><span className={`w-fit rounded-full px-2 py-1 text-[0.625rem] font-black uppercase ${assignmentStatus(assignment.status).className}`}>{assignmentStatus(assignment.status).label}</span></article>)}</div> : <EmptyState>No lessons have a scheduled date yet.</EmptyState>}
              </SectionCard>
            </div>
          )}

          {activeTab === "curriculum" && (
            <TeacherSubjectCurriculum
              initialCatalog={subjectCurriculumCatalog}
              csrfToken={csrfToken}
            />
          )}

          {activeTab === "updates" && (
            <div className="space-y-4">
              <div><p className="text-xs font-black uppercase tracking-[0.16em] text-primary">Teacher Academy</p><h1 className="mt-1 font-display text-2xl font-black">Updates</h1><p className="mt-1 text-sm font-semibold text-muted-foreground">Your latest lesson assignments and assessment reports.</p></div>
              <SectionCard title="Recent activity" icon={<Sparkles className="h-4 w-4" />}>
                {updates.length ? <ol className="divide-y divide-border/70">{updates.map((item) => <li key={item.id} className="flex gap-3 px-4 py-4"><span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${item.type === "Report" ? "bg-success/10 text-success" : "bg-primary/10 text-primary"}`}>{item.type === "Report" ? <CheckCircle2 className="h-4 w-4" /> : <BookOpen className="h-4 w-4" />}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-start justify-between gap-2"><p className="text-sm font-black">{item.title}</p><time className="text-[0.6875rem] font-semibold text-muted-foreground">{formatDate(item.date, true)}</time></div><p className="mt-1 text-xs font-semibold text-muted-foreground">{item.detail}</p></div></li>)}</ol> : <EmptyState>No Academy updates yet.</EmptyState>}
              </SectionCard>
            </div>
          )}

          {activeTab === "profile" && (
            <div className="space-y-4">
              <div><p className="text-xs font-black uppercase tracking-[0.16em] text-primary">Teacher Academy</p><h1 className="mt-1 font-display text-2xl font-black">Profile</h1><p className="mt-1 text-sm font-semibold text-muted-foreground">Your Academy contact and support information.</p></div>
              <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
                <SectionCard title="Teacher information" icon={<CircleUserRound className="h-4 w-4" />}>
                  <dl className="grid gap-px bg-border/70 sm:grid-cols-2">{[
                    ["Full name", name, CircleUserRound], ["Subject", subject, GraduationCap], ["Phone", asText(teacher.phone), Phone], ["Email", asText(teacher.email), Mail], ["Telegram", asText(teacher.telegram_username), MessageSquareText], ["Academy start", formatDate(teacher.academy_start_date), CalendarDays],
                  ].map(([label, value, Icon]) => { const ItemIcon = Icon as typeof CircleUserRound; return <div key={String(label)} className="bg-surface p-4"><dt className="flex items-center gap-2 text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground"><ItemIcon className="h-3.5 w-3.5 text-primary" />{String(label)}</dt><dd className="mt-1.5 text-sm font-black">{String(value)}</dd></div>; })}</dl>
                </SectionCard>
                <div className="space-y-4">
                  <SectionCard title="Academy support" icon={<UserRoundCheck className="h-4 w-4" />}><dl className="space-y-3 p-4 text-sm"><div><dt className="text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">Mentor</dt><dd className="mt-1 font-black">{asText(teacher.mentor_name)}</dd></div><div><dt className="text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">Department head</dt><dd className="mt-1 font-black">{asText(teacher.department_head_name)}</dd></div><div><dt className="text-[0.625rem] font-black uppercase tracking-wide text-muted-foreground">Status</dt><dd className="mt-1 capitalize font-black">{academyStatus}</dd></div></dl></SectionCard>
                  <SectionCard title="Account" icon={<KeyRound className="h-4 w-4" />}><div className="space-y-2 p-4"><p className="text-xs font-semibold text-muted-foreground">Signed in as <span className="font-black text-foreground">{authLogin || "Teacher"}</span></p><a href={routes.accountSecurity} className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-border bg-background px-4 text-sm font-black hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"><KeyRound className="h-4 w-4" />Change password</a><form action={routes.logout} method="post"><input type="hidden" name="csrf_token" value={csrfToken} /><button type="submit" className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"><LogOut className="h-4 w-4" />Log out</button></form></div></SectionCard>
                </div>
              </div>
            </div>
          )}
        </main>
        <AcademyNav mobile activeTab={activeTab} onChange={setActiveTab} />
      </div>
    </div>
  );
}
