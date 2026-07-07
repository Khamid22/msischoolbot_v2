import { Suspense, lazy, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  Bell,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  GraduationCap,
  Home,
  LogOut,
  Star,
  TrendingUp,
  UserRound,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { useLazyVisible } from "@/shared/lib/useLazyVisible";
import { bottomNavActiveKey, type TeacherTabKey } from "@/roles/teacher/teacherNav";

const ActiveTeacherCharts = lazy(() => import("@/roles/teacher/components/ActiveTeacherCharts"));

type TeacherInfo = {
  id: number;
  full_name: string;
  login: string;
  assigned_group: string;
  category: string;
  semester_stage: string;
  performance_score?: number;
};

type Lesson = {
  id: number;
  lessonNumber: string;
  topic: string;
  date: string;
  order: number;
};

type Enrollment = {
  enrollmentId: number;
  fullName: string;
  averageGrade: number;
  coins: number;
  attendance: Record<string, string>;
  homework: Record<string, number>;
  exams: Record<string, number>;
};

type GroupGradebook = {
  group: { id: number; name: string; code: string; schoolCode: string; subjectName: string };
  lessons: Lesson[];
  examLabels: string[];
  enrollments: Enrollment[];
};

type AcademyAssignment = {
  id: number;
  sequence_no: number;
  lesson_number: string;
  lesson_topic: string;
  status: string;
  session_datetime: string;
  start_time?: string;
  end_time?: string;
  deadline_date: string;
  evaluator_name: string;
  assignment_type?: string;
  specification_points: string;
  book_pages: string;
};

type AcademyAssessment = {
  id: number;
  lesson_assignment_id: number;
  lesson_number: string;
  lesson_topic: string;
  evaluator_name: string;
  assessment_datetime: string;
  session_type: string;
  weighted_overall_score: number;
  decision: string;
  strengths: string;
  areas_for_improvement: string;
  final_recommendation: string;
  scores?: Record<string, number>;
  section_feedback?: Record<string, unknown>;
};

type AcademyTeacher = {
  id: number;
  full_name: string;
  subject: string;
  subject_program_name: string;
  academy_status: string;
  academy_start_date?: string;
  training_end_date?: string;
  department_head_name?: string;
  login?: string;
  progress?: {
    assigned_count: number;
    assessed_count: number;
    passed_count: number;
    average_score: number | null;
    latest_score: number | null;
    target_lessons: number;
  };
};

type WorkspaceCard = {
  label: string;
  value: string;
  detail: string;
  tone?: string;
};

type AcademySummary = {
  assigned_count?: number;
  assessed_count?: number;
  completed_count?: number;
  remaining_count?: number;
  target_lessons?: number;
  progress_percent?: number;
  rank?: string;
  status?: string;
  subject?: string;
  training_start_date?: string;
  training_end_date?: string;
  average_score?: number | null;
  latest_score?: number | null;
  score_summary?: string;
};

type AcademyUpdate = {
  id: string | number;
  kind?: string;
  title: string;
  body?: string;
  source?: string;
  created_at?: string;
  priority?: string;
};

type TeacherPageProps = {
  authLogin?: string;
  csrfToken?: string;
  teacher: TeacherInfo;
  groups: GroupGradebook[];
  academy?: AcademyTeacher | null;
  academySummary?: AcademySummary;
  academyUpdates?: AcademyUpdate[];
  journey?: AcademyAssignment[];
  lessonReports?: AcademyAssessment[];
  trainingTimetable?: AcademyAssignment[];
  workspaceCards?: WorkspaceCard[];
};

type TabKey = TeacherTabKey;

const activeTeacherTabs: Array<{ key: TabKey; label: string; icon: LucideIcon }> = [
  { key: "home", label: "Home", icon: Home },
  { key: "reports", label: "Lesson Reports", icon: ClipboardList },
  { key: "timetable", label: "Timetable", icon: CalendarDays },
  { key: "career", label: "Career Growth", icon: TrendingUp },
  { key: "updates", label: "Updates", icon: Bell },
];

const academyTabs: Array<{ key: TabKey; label: string; icon: LucideIcon }> = [
  { key: "home", label: "Overview", icon: Home },
  { key: "reports", label: "Lessons", icon: ClipboardList },
  { key: "timetable", label: "Timetable", icon: CalendarDays },
  { key: "updates", label: "Updates", icon: Bell },
];

const teacherMobileTabs: Array<{ key: TabKey; label: string; icon: LucideIcon }> = [
  { key: "home", label: "Home", icon: Home },
  { key: "reports", label: "Lessons", icon: ClipboardList },
  { key: "updates", label: "Updates", icon: Bell },
  { key: "profile", label: "Profile", icon: UserRound },
];

const activeTeacherMobileTabs: Array<{ key: TabKey; label: string; icon: LucideIcon }> = [
  { key: "home", label: "Home", icon: Home },
  { key: "reports", label: "Reports", icon: ClipboardList },
  { key: "timetable", label: "Timetable", icon: CalendarDays },
  { key: "profile", label: "Profile", icon: UserRound },
];

function teacherInitials(name?: string, fallback = "T") {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!parts.length) return fallback;
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

const scoreLabels: Record<string, string> = {
  teacher_guidance_compliance_score: "Teacher Guidance Compliance",
  timing_adherence_score: "Timing Adherence",
  resource_familiarity_score: "Resource Familiarity",
  english_fluency_score: "English Fluency",
  confidence_delivery_score: "Confidence & Delivery",
  engagement_technique_score: "Student Engagement",
};

function asNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function displayDate(value: string) {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function displayDateOnly(value?: string) {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function displayTimeOnly(value?: string) {
  if (!value) return "Not set";
  if (/^\d{2}:\d{2}/.test(value)) return value.slice(0, 5);
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    new_academy_teacher: "New Academy Teacher",
    in_training: "In Academy",
    ready_for_evaluation: "Ready for Evaluation",
    needs_improvement: "Needs Improvement",
    ready_for_active_teacher: "Ready",
    approved: "Completed",
    rejected: "Rejected",
    on_hold: "On Hold",
    training_simulation: "Academy simulation",
  };
  const raw = String(value || "assigned");
  return labels[raw] || raw.replace(/_/g, " ");
}

function statusClass(value: string) {
  const normalized = String(value || "").toLowerCase();
  if (["passed", "approved", "approved_for_active_teacher", "ready_for_active_teacher"].includes(normalized)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (["assessed", "ready", "ready_for_evaluation", "ready_for_final_evaluation"].includes(normalized)) {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  if (["needs_improvement", "rejected", "important"].includes(normalized)) {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

type LessonDisplayStatus = "Assigned" | "Scheduled" | "Completed" | "Assessed";

const lessonStatusBadge: Record<LessonDisplayStatus, string> = {
  Assigned: "bg-[#F4F6FA] text-[#7A8296]",
  Scheduled: "bg-[#EFF3FF] text-[#2F5DE0]",
  Completed: "bg-[#EAF6EF] text-[#1E7A5C]",
  Assessed: "bg-[#EAF6EF] text-[#1E7A5C]",
};

function lessonDisplayStatus(assignment: AcademyAssignment, report?: AcademyAssessment): LessonDisplayStatus {
  if (report) return "Assessed";
  const normalized = String(assignment.status || "").toLowerCase();
  if (["passed", "assessed"].includes(normalized)) return "Completed";
  if (String(assignment.session_datetime || "").trim()) return "Scheduled";
  return "Assigned";
}

const updateKindBadge: Record<string, string> = {
  announcement: "bg-[#FFF3E9] text-[#B8722E]",
  lesson: "bg-[#EFF3FF] text-[#2F5DE0]",
  schedule: "bg-[#F4F0FF] text-[#6E4CDB]",
  assessment: "bg-[#EAF6EF] text-[#1E7A5C]",
};

function updateBadgeClass(kind?: string, priority?: string) {
  return updateKindBadge[String(kind || "").toLowerCase()] || (priority === "important" ? "bg-[#FFF3E9] text-[#B8722E]" : "bg-[#F4F6FA] text-[#7A8296]");
}

function average(values: number[]) {
  const clean = values.filter((value) => Number.isFinite(value) && value > 0);
  return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : 0;
}

function CabinetSidebar({
  teacher,
  academy,
  tabs,
  activeTab,
  setActiveTab,
  csrfToken,
}: {
  teacher: TeacherInfo;
  academy: AcademyTeacher | null;
  tabs: Array<{ key: TabKey; label: string; icon: LucideIcon }>;
  activeTab: TabKey;
  setActiveTab: (tab: TabKey) => void;
  csrfToken?: string;
}) {
  return (
    <aside className="hidden min-h-screen w-60 shrink-0 flex-col bg-[#12203D] text-white shadow-2xl md:sticky md:top-0 md:flex">
      <div className="flex items-center gap-3 px-4 py-5">
        <div className="flex h-11 w-11 shrink-0 flex-col items-center justify-center rounded-2xl border border-white/10 bg-white/5 shadow-sm">
          <span className="text-sm font-black leading-none tracking-wide">MSI</span>
          <span className="mt-1 text-[8px] font-bold uppercase tracking-[0.2em] text-white/60">School</span>
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-black leading-5">Teacher Cabinet</p>
          <p className="truncate text-xs font-semibold text-white/55">{academy ? "Teacher Academy" : "Teaching Workspace"}</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-2" aria-label="Teacher cabinet desktop navigation">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`flex h-11 items-center gap-3 rounded-2xl px-3 text-left text-sm font-black transition-all ${
                isActive ? "bg-[#2F5DE0]/25 text-white shadow-sm" : "text-white/64 hover:bg-white/10 hover:text-white"
              }`}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className={`h-4 w-4 ${isActive ? "text-white" : "text-white/50"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#2F5DE0] text-sm font-black text-white">
            {teacherInitials(teacher.full_name)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-black leading-5">{teacher.full_name || "Teacher"}</p>
            <p className="truncate text-xs font-semibold text-white/55">
              {teacher.login}
              {academy ? " · Academy" : ""}
            </p>
          </div>
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={csrfToken || ""} />
            <button
              type="submit"
              className="flex h-9 w-9 items-center justify-center rounded-xl text-white/55 transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Log out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
}

function countAttendance(groups: GroupGradebook[]) {
  let present = 0;
  let total = 0;
  groups.forEach((group) => {
    group.enrollments.forEach((enrollment) => {
      Object.values(enrollment.attendance || {}).forEach((value) => {
        if (!value) return;
        total += 1;
        if (value === "present") present += 1;
      });
    });
  });
  return total ? Math.round((present / total) * 100) : 0;
}

function reportRows(reports: AcademyAssessment[]) {
  return reports
    .filter((report) => asNumber(report.weighted_overall_score) > 0)
    .map((report, index) => ({
      name: report.lesson_number || `Report ${index + 1}`,
      score: Number(asNumber(report.weighted_overall_score).toFixed(1)),
    }));
}

function workspaceCardIcon(label: string) {
  const normalized = label.toLowerCase();
  if (normalized.includes("resource")) return <BookOpen className="h-4 w-4" />;
  if (normalized.includes("attendance") || normalized.includes("homework")) return <Activity className="h-4 w-4" />;
  if (normalized.includes("group") || normalized.includes("student")) return <Users className="h-4 w-4" />;
  return <CheckCircle2 className="h-4 w-4" />;
}

function MetricCard({
  label,
  value,
  detail,
  icon,
  tone = "text-slate-900",
}: {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
  tone?: string;
}) {
  return (
    <div className="rounded-[0.875rem] border border-[#E4E7EC] bg-white p-3 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md motion-reduce:hover:translate-y-0 sm:p-3.5">
      <div className="flex items-start justify-between gap-2 sm:gap-3">
        <div className="min-w-0">
          <p className={`truncate text-xl font-black leading-7 text-[#12203D] ${tone}`}>{value}</p>
          <p className="mt-0.5 truncate text-[11px] font-bold text-[#7A8296]">{label}</p>
          <p className="mt-0.5 line-clamp-2 text-[11px] font-medium leading-4 text-[#9AA1B2]">{detail}</p>
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[#F4F6FA] text-[#2F5DE0]">
          {icon}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
  return (
    <div className="flex min-h-[14rem] flex-col items-center justify-center rounded-[0.875rem] border border-dashed border-[#E4E7EC] bg-white/70 px-6 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-[#F4F6FA] text-[#7A8296]">{icon}</div>
      <p className="text-sm font-black text-[#12203D]">{title}</p>
      <p className="mt-1 max-w-md text-sm text-[#7A8296]">{detail}</p>
    </div>
  );
}

function SectionHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="px-1">
      <h2 className="text-xl font-black text-[#12203D]">{title}</h2>
      <p className="mt-1 text-sm font-medium text-[#7A8296]">{subtitle}</p>
    </div>
  );
}

function ProgressDonut({ completed, target }: { completed: number; target: number }) {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const ratio = target > 0 ? Math.min(1, completed / target) : 0;
  return (
    <svg width="88" height="88" viewBox="0 0 88 88" className="shrink-0" role="img" aria-label={`${completed} of ${target} lessons completed`}>
      <circle cx="44" cy="44" r={radius} fill="none" stroke="#EEF1F6" strokeWidth="9" />
      <circle
        cx="44"
        cy="44"
        r={radius}
        fill="none"
        stroke="#2F5DE0"
        strokeWidth="9"
        strokeLinecap="round"
        strokeDasharray={`${circumference} ${circumference}`}
        strokeDashoffset={circumference * (1 - ratio)}
        transform="rotate(-90 44 44)"
      />
      <text x="44" y="41" textAnchor="middle" fontSize="18" fontWeight="700" fill="#12203D">
        {completed}/{target}
      </text>
      <text x="44" y="57" textAnchor="middle" fontSize="9" fill="#7A8296">
        lessons
      </text>
    </svg>
  );
}

function AcademyIdentityCard({
  teacher,
  academy,
}: {
  teacher: TeacherInfo;
  academy: AcademyTeacher | null;
}) {
  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-[#12203D] p-4 text-white shadow-sm sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-lg font-black">{teacher.full_name || "Teacher"}</p>
          <p className="mt-1 truncate text-sm font-semibold text-white/60">
            {teacher.login}
            {academy?.subject_program_name || academy?.subject ? ` · ${academy?.subject_program_name || academy?.subject}` : ""}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-[#2F5DE0]/28 px-2.5 py-1.5 text-[11px] font-black text-[#B9CBFF]">
          Academy · {statusLabel(academy?.academy_status || "in_training")}
        </span>
      </div>
    </section>
  );
}

function AcademyHeroCard({
  academy,
  assessedCount,
  targetLessons,
  progressPercent,
}: {
  academy: AcademyTeacher | null;
  assessedCount: number;
  targetLessons: number;
  progressPercent: number;
}) {
  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm sm:p-5">
      <div className="mb-3.5 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-black text-[#12203D]">Teacher Academy</p>
          <p className="mt-0.5 truncate text-xs font-semibold text-[#7A8296]">
            {academy?.subject_program_name || academy?.subject || "Curriculum"} Teacher Academy path
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-[#EFF3FF] px-2.5 py-1 text-[11px] font-black text-[#2F5DE0]">
          {progressPercent >= 100 ? "Completed" : "In progress"}
        </span>
      </div>
      <div className="flex items-center gap-5">
        <ProgressDonut completed={assessedCount} target={targetLessons} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[#5B6478]">
            {assessedCount} of {targetLessons} academy lessons completed
          </p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#EEF1F6]">
            <div className="h-full rounded-full bg-[#2F5DE0] transition-all duration-500" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      </div>
    </section>
  );
}

function nextScheduledLesson(lessons: AcademyAssignment[]) {
  if (!lessons.length) return null;
  const now = Date.now();
  const futureLessons = lessons
    .filter((lesson) => {
      const date = new Date(lesson.session_datetime || lesson.deadline_date || "");
      return !Number.isNaN(date.getTime()) && date.getTime() >= now;
    })
    .sort((first, second) => {
      const firstDate = new Date(first.session_datetime || first.deadline_date || "").getTime();
      const secondDate = new Date(second.session_datetime || second.deadline_date || "").getTime();
      return firstDate - secondDate;
    });
  return futureLessons[0] || lessons[0];
}

function NextLessonPreview({ lessons, onViewLessons }: { lessons: AcademyAssignment[]; onViewLessons: () => void }) {
  const lesson = nextScheduledLesson(lessons);
  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      <p className="text-[11px] font-black uppercase tracking-wide text-[#7A8296]">Next scheduled lesson</p>
      {lesson ? (
        <>
          <p className="mt-2 line-clamp-2 text-[15px] font-black leading-5 text-[#12203D]">
            {lesson.lesson_number || "Academy lesson"}
            {lesson.lesson_topic ? ` — ${lesson.lesson_topic}` : ""}
          </p>
          <p className="mt-1.5 text-sm font-medium text-[#5B6478]">
            {displayDate(lesson.session_datetime || lesson.deadline_date)}
            {lesson.assignment_type ? ` · ${statusLabel(lesson.assignment_type)}` : ""}
          </p>
          <p className="mt-1 truncate text-xs font-semibold text-[#7A8296]">
            Evaluator: {lesson.evaluator_name || "Not assigned"}
          </p>
          <button
            type="button"
            onClick={onViewLessons}
            className="mt-3 inline-flex h-9 items-center rounded-[0.5625rem] bg-[#F4F6FA] px-3.5 text-xs font-black text-[#12203D] transition-colors hover:bg-[#E4E7EC]"
          >
            View in Lessons
          </button>
        </>
      ) : (
        <p className="mt-2 rounded-xl border border-dashed border-[#E4E7EC] bg-[#F7F8FA] px-3 py-4 text-sm font-semibold text-[#7A8296]">
          No academy lesson is scheduled yet.
        </p>
      )}
    </section>
  );
}

function LatestFeedbackPreview({
  reports,
  onViewReport,
}: {
  reports: AcademyAssessment[];
  onViewReport: (report: AcademyAssessment) => void;
}) {
  const latest = reports.length ? reports[reports.length - 1] : null;
  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      <p className="text-[11px] font-black uppercase tracking-wide text-[#7A8296]">Latest feedback</p>
      {latest ? (
        <>
          <div className="mt-2 flex items-center justify-between gap-3">
            <p className="line-clamp-2 min-w-0 text-[15px] font-black leading-5 text-[#12203D]">
              {latest.lesson_number || "Assessed lesson"}
              {latest.lesson_topic ? ` — ${latest.lesson_topic}` : ""}
            </p>
            <p className="shrink-0 text-lg font-black text-[#2F5DE0]">
              {asNumber(latest.weighted_overall_score) ? asNumber(latest.weighted_overall_score).toFixed(1) : "-"}
            </p>
          </div>
          <p className="mt-1.5 line-clamp-2 text-sm font-medium leading-5 text-[#5B6478]">
            {latest.strengths || latest.final_recommendation || "Report details are available."}
          </p>
          <button
            type="button"
            onClick={() => onViewReport(latest)}
            className="mt-3 inline-flex h-9 items-center rounded-[0.5625rem] bg-[#F4F6FA] px-3.5 text-xs font-black text-[#12203D] transition-colors hover:bg-[#E4E7EC]"
          >
            View lesson report
          </button>
        </>
      ) : (
        <p className="mt-2 rounded-xl border border-dashed border-[#E4E7EC] bg-[#F7F8FA] px-3 py-4 text-sm font-semibold text-[#7A8296]">
          No assessment reports yet.
        </p>
      )}
    </section>
  );
}

function LatestUpdatePreview({ updates, onViewUpdates }: { updates: AcademyUpdate[]; onViewUpdates: () => void }) {
  const latest = updates[0];
  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      {latest ? (
        <>
          <div className="flex items-center justify-between gap-3">
            <span className={`rounded-full px-2 py-1 text-[10.5px] font-black uppercase ${updateBadgeClass(latest.kind, latest.priority)}`}>
              {latest.kind || latest.priority || "update"}
            </span>
            {latest.created_at ? <span className="text-[11px] font-semibold text-[#9AA1B2]">{displayDate(latest.created_at)}</span> : null}
          </div>
          <p className="mt-2 line-clamp-2 text-sm font-black leading-5 text-[#12203D]">{latest.title || "Academy update"}</p>
          <button type="button" onClick={onViewUpdates} className="mt-2 text-xs font-black text-[#2F5DE0]">
            View updates →
          </button>
        </>
      ) : (
        <>
          <p className="text-[11px] font-black uppercase tracking-wide text-[#7A8296]">Latest update</p>
          <p className="mt-2 rounded-xl border border-dashed border-[#E4E7EC] bg-[#F7F8FA] px-3 py-4 text-sm font-semibold text-[#7A8296]">
            No academy updates yet.
          </p>
        </>
      )}
    </section>
  );
}

function ScoreTrendSvg({ rows }: { rows: Array<{ name: string; score: number }> }) {
  const width = 300;
  const height = 140;
  const pad = 14;
  const dots = rows.map((row, index) => {
    const x = rows.length > 1 ? pad + index * ((width - pad * 2) / (rows.length - 1)) : width / 2;
    const y = height - pad - Math.min(1, Math.max(0, row.score / 10)) * (height - pad * 2);
    return { x: Math.round(x), y: Math.round(y) };
  });
  const points = dots.map((point) => `${point.x},${point.y}`).join(" ");
  return (
    <>
      <svg width="100%" height="140" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="overflow-visible">
        <line x1="0" y1="10" x2={width} y2="10" stroke="#F0F2F6" strokeWidth="1" />
        <line x1="0" y1="55" x2={width} y2="55" stroke="#F0F2F6" strokeWidth="1" />
        <line x1="0" y1="100" x2={width} y2="100" stroke="#F0F2F6" strokeWidth="1" />
        <polyline points={points} fill="none" stroke="#2F5DE0" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {dots.map((point, index) => (
          <circle key={`${point.x}-${index}`} cx={point.x} cy={point.y} r="4" fill="#2F5DE0" stroke="#fff" strokeWidth="1.5" />
        ))}
      </svg>
      <div className="flex justify-between px-1 pt-0.5">
        {rows.map((row, index) => (
          <span key={`${row.name}-${index}`} className="max-w-[4rem] truncate text-[10.5px] font-semibold text-[#9AA1B2]">
            {row.name}
          </span>
        ))}
      </div>
    </>
  );
}

function AcademyScoreSnapshot({ rows }: { rows: Array<{ name: string; score: number }> }) {
  if (!rows.length) return null;

  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      <p className="text-sm font-black text-[#12203D]">Assessment score trend</p>
      <p className="mt-0.5 text-[11.5px] font-semibold text-[#7A8296]">Score out of 10 across assessed lessons</p>
      <div className="mt-3">
        <ScoreTrendSvg rows={rows} />
      </div>
    </section>
  );
}

function rubricBreakdownRows(reports: AcademyAssessment[]) {
  const totals = new Map<string, { sum: number; count: number }>();
  reports.forEach((report) => {
    Object.entries(report.scores || {}).forEach(([key, value]) => {
      const score = asNumber(value);
      if (!(key in scoreLabels) || score <= 0) return;
      const bucket = totals.get(key) || { sum: 0, count: 0 };
      bucket.sum += score;
      bucket.count += 1;
      totals.set(key, bucket);
    });
  });
  return Object.entries(scoreLabels)
    .filter(([key]) => totals.has(key))
    .map(([key, label]) => {
      const bucket = totals.get(key)!;
      return { label, value: bucket.sum / bucket.count };
    });
}

function RubricBreakdownCard({ reports }: { reports: AcademyAssessment[] }) {
  const rows = useMemo(() => rubricBreakdownRows(reports), [reports]);
  if (!rows.length) return null;

  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      <p className="text-sm font-black text-[#12203D]">Rubric breakdown</p>
      <div className="mt-3 space-y-2.5">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="mb-1 flex items-center justify-between gap-2 text-xs font-semibold text-[#5B6478]">
              <span className="truncate">{row.label}</span>
              <span className="shrink-0 font-black text-[#12203D]">{row.value.toFixed(1)}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-[#EEF1F6]">
              <div className="h-full rounded-full bg-[#2F5DE0]" style={{ width: `${Math.min(100, row.value * 10)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function LessonReportSheet({
  report,
  assignment,
  onClose,
}: {
  report: AcademyAssessment;
  assignment: AcademyAssignment | null;
  onClose: () => void;
}) {
  const panelRef = useDismissibleLayer<HTMLDivElement>({ onDismiss: onClose });
  const score = asNumber(report.weighted_overall_score);
  const rubricRows = Object.entries(report.scores || {})
    .filter(([key, value]) => key in scoreLabels && asNumber(value) > 0)
    .map(([key, value]) => ({ label: scoreLabels[key], value: asNumber(value) }));
  const sequence = asNumber(assignment?.sequence_no);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-[#12203D]/45 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Lesson report"
    >
      <div
        ref={panelRef}
        className="flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-[1.25rem] bg-white pt-2.5 shadow-2xl animate-in slide-in-from-bottom-4 duration-200 motion-reduce:animate-none sm:max-w-lg sm:rounded-[1.25rem] sm:pt-4"
      >
        <div className="flex justify-center pb-2 sm:hidden">
          <div className="h-1 w-9 rounded-full bg-[#E4E7EC]" />
        </div>
        <div className="flex items-start justify-between gap-3 px-5 pb-3.5">
          <div className="min-w-0">
            <p className="text-[11px] font-black uppercase tracking-wide text-[#7A8296]">
              {sequence ? `Lesson ${sequence} report` : "Lesson report"}
            </p>
            <p className="mt-1 line-clamp-2 text-base font-black leading-5 text-[#12203D]">
              {report.lesson_number || "Academy lesson"}
              {report.lesson_topic ? ` — ${report.lesson_topic}` : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#F4F6FA] text-[#5B6478] transition-colors hover:bg-[#E4E7EC]"
            aria-label="Close report"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div
          className="min-h-0 flex-1 overflow-y-auto px-5 pb-6"
          style={{ paddingBottom: "max(1.5rem, var(--app-bottom-inset))" }}
        >
          <div className="flex items-center gap-4 rounded-[0.875rem] bg-[#F7F8FA] p-4">
            <p className="text-3xl font-black text-[#2F5DE0]">{score ? score.toFixed(1) : "-"}</p>
            <div>
              <p className="text-xs font-black text-[#12203D]">Overall score</p>
              <p className="mt-0.5 text-[11.5px] font-semibold text-[#7A8296]">
                {statusLabel(report.session_type || "training_simulation")} · {displayDate(report.assessment_datetime)}
              </p>
            </div>
          </div>

          {rubricRows.length ? (
            <>
              <p className="mb-2.5 mt-4 text-xs font-black text-[#12203D]">Rubric scores</p>
              <div className="space-y-2.5">
                {rubricRows.map((row) => (
                  <div key={row.label}>
                    <div className="mb-1 flex items-center justify-between gap-2 text-xs font-semibold text-[#5B6478]">
                      <span className="truncate">{row.label}</span>
                      <span className="shrink-0 font-black text-[#12203D]">{row.value.toFixed(1)}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-[#EEF1F6]">
                      <div className="h-full rounded-full bg-[#2F5DE0]" style={{ width: `${Math.min(100, row.value * 10)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : null}

          <div className="mt-4 rounded-xl bg-[#EAF6EF] px-4 py-3.5">
            <p className="text-xs font-black text-[#1E7A5C]">Strengths</p>
            <p className="mt-1 text-sm leading-6 text-[#3D5A4E]">{report.strengths || "Not recorded yet."}</p>
          </div>

          <div className="mt-2.5 rounded-xl bg-[#FFF3E9] px-4 py-3.5">
            <p className="text-xs font-black text-[#B8722E]">Areas for improvement</p>
            <p className="mt-1 text-sm leading-6 text-[#7A5C3D]">{report.areas_for_improvement || "Not recorded yet."}</p>
          </div>

          <div className="mt-4">
            <p className="text-xs font-black text-[#12203D]">Written report from Academic Department</p>
            <p className="mt-1 text-sm leading-6 text-[#5B6478]">{report.final_recommendation || "No written report yet."}</p>
          </div>

          <div className="mt-4 flex items-center justify-between gap-3 rounded-xl bg-[#F4F6FA] px-4 py-3.5">
            <span className="text-xs font-black text-[#12203D]">Final recommendation</span>
            <span className={`rounded-full border px-2.5 py-1 text-[11px] font-black uppercase ${statusClass(report.decision)}`}>
              {statusLabel(report.decision)}
            </span>
          </div>

          <p className="mt-3 text-xs font-semibold text-[#9AA1B2]">
            Assessed by {report.evaluator_name || "Academic Director"} · {displayDate(report.assessment_datetime)}
          </p>
        </div>
      </div>
    </div>
  );
}

function AcademyLessonsScreen({
  assignments,
  reports,
  onOpenReport,
}: {
  assignments: AcademyAssignment[];
  reports: AcademyAssessment[];
  onOpenReport: (report: AcademyAssessment, assignment: AcademyAssignment) => void;
}) {
  const reportByAssignment = new Map(reports.map((report) => [asNumber(report.lesson_assignment_id), report]));
  if (!assignments.length) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-5 w-5" />}
        title="No academy lessons assigned."
        detail="Academic Department will select lessons before the Teacher Academy sequence begins."
      />
    );
  }

  return (
    <section className="space-y-3">
      <SectionHeading title="Lessons" subtitle="Teacher Academy assigned lessons" />
      <div className="grid gap-2.5 lg:grid-cols-2">
        {assignments.map((assignment, index) => {
          const report = reportByAssignment.get(assignment.id);
          const score = asNumber(report?.weighted_overall_score);
          const status = lessonDisplayStatus(assignment, report);
          return (
            <article key={assignment.id} className="flex items-start gap-3 rounded-[0.875rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#F4F6FA] text-xs font-black text-[#7A8296]">
                {assignment.sequence_no || index + 1}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2.5">
                  <p className="line-clamp-2 min-w-0 text-sm font-black leading-5 text-[#12203D]">
                    {assignment.lesson_number || `Lesson ${index + 1}`}
                    {assignment.lesson_topic ? ` — ${assignment.lesson_topic}` : ""}
                  </p>
                  <span className={`shrink-0 rounded-full px-2 py-1 text-[10.5px] font-black ${lessonStatusBadge[status]}`}>
                    {status}
                  </span>
                </div>
                <p className="mt-1 text-xs font-semibold text-[#7A8296]">
                  {statusLabel(assignment.assignment_type || "full_practice_lesson")}
                  {String(assignment.session_datetime || "").trim() ? ` · ${displayDate(assignment.session_datetime)}` : ""}
                  {assignment.evaluator_name ? ` · ${assignment.evaluator_name}` : ""}
                </p>
                <div className="mt-2.5 flex items-center justify-between gap-2">
                  {score ? <p className="text-[13px] font-black text-[#2F5DE0]">Score: {score.toFixed(1)}</p> : <span />}
                  {report ? (
                    <button
                      type="button"
                      onClick={() => onOpenReport(report, assignment)}
                      className="inline-flex h-8 items-center rounded-lg bg-[#F4F6FA] px-3 text-xs font-black text-[#12203D] transition-colors hover:bg-[#E4E7EC]"
                    >
                      View report
                    </button>
                  ) : null}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function AcademyProfileSummary({
  teacher,
  academy,
  summary,
  targetLessons,
}: {
  teacher: TeacherInfo;
  academy: AcademyTeacher | null;
  summary: AcademySummary;
  targetLessons: number;
}) {
  const averageScore = summary.average_score ?? academy?.progress?.average_score ?? null;
  const latestScore = summary.latest_score ?? academy?.progress?.latest_score ?? null;
  const rows: Array<[string, string]> = [
    ["Teacher code", teacher.login || academy?.login || "Not created yet"],
    ["Subject", summary.subject || academy?.subject_program_name || academy?.subject || "Subject not set"],
    ["Department / HOD", academy?.department_head_name || "Not assigned"],
    ["Academy status", statusLabel(summary.status || academy?.academy_status || "in_training")],
    ["Start date", displayDateOnly(summary.training_start_date || academy?.academy_start_date || "")],
    ["Expected completion", displayDateOnly(summary.training_end_date || academy?.training_end_date || "")],
    ["Assigned lessons", targetLessons ? String(targetLessons) : "Not assigned"],
  ];

  return (
    <div className="grid gap-3 md:grid-cols-[1.4fr_1fr] md:items-start">
      <div className="overflow-hidden rounded-[0.875rem] border border-[#E4E7EC] bg-white shadow-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3 border-b border-[#EEF1F6] px-4 py-3 last:border-b-0">
            <span className="text-xs font-semibold text-[#7A8296]">{label}</span>
            <span className="truncate text-[13px] font-black text-[#12203D]">{value}</span>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        <div className="rounded-[0.875rem] border border-[#E4E7EC] bg-white p-3.5 shadow-sm">
          <p className="text-xl font-black text-[#12203D]">
            {averageScore === null || averageScore === undefined ? "-" : asNumber(averageScore).toFixed(1)}
          </p>
          <p className="mt-0.5 text-[11.5px] font-semibold text-[#7A8296]">Average score</p>
        </div>
        <div className="rounded-[0.875rem] border border-[#E4E7EC] bg-white p-3.5 shadow-sm">
          <p className="text-xl font-black text-[#12203D]">
            {latestScore === null || latestScore === undefined ? "-" : asNumber(latestScore).toFixed(1)}
          </p>
          <p className="mt-0.5 text-[11.5px] font-semibold text-[#7A8296]">Latest score</p>
        </div>
        <div className="col-span-2 rounded-[0.875rem] border border-[#E4E7EC] bg-[#EFF3FF] px-3.5 py-3 text-xs font-semibold leading-5 text-[#2F5DE0]">
          {summary.score_summary || "No assessments yet."}
        </div>
      </div>
    </div>
  );
}

function AcademyUpdates({ updates }: { updates: AcademyUpdate[] }) {
  if (!updates.length) {
    return (
      <EmptyState
        icon={<Bell className="h-5 w-5" />}
        title="No academy updates yet"
        detail="Announcements from Academic Department and HR Manager will appear here."
      />
    );
  }

  return (
    <section className="space-y-3">
      <SectionHeading title="Updates" subtitle="Academy announcements and news" />
      <div className="grid gap-2.5 md:grid-cols-2">
        {updates.map((item) => (
          <article key={String(item.id)} className="rounded-[0.875rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <span className={`rounded-full px-2 py-1 text-[10.5px] font-black uppercase ${updateBadgeClass(item.kind, item.priority)}`}>
                {item.kind || item.priority || "update"}
              </span>
              {item.created_at ? <span className="text-[11px] font-semibold text-[#9AA1B2]">{displayDate(item.created_at)}</span> : null}
            </div>
            <p className="mt-2 text-sm font-black leading-5 text-[#12203D]">{item.title || "Teacher Academy update"}</p>
            {item.body ? <p className="mt-1 line-clamp-3 text-sm leading-6 text-[#5B6478]">{item.body}</p> : null}
            <p className="mt-2 text-[11px] font-bold text-[#9AA1B2]">{item.source || "Academic Department"}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Timetable({ lessons }: { lessons: AcademyAssignment[] }) {
  if (!lessons.length) {
    return (
      <EmptyState
        icon={<CalendarDays className="h-5 w-5" />}
        title="No Teacher Academy sessions scheduled"
        detail="When the Academic Director schedules academy lessons, the teacher will see them here."
      />
    );
  }
  return (
    <section className="space-y-3">
      <SectionHeading title="Timetable" subtitle="Scheduled academy sessions" />
      <div className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
        {lessons.map((lesson) => (
          <div key={lesson.id} className="rounded-[0.875rem] border border-[#E4E7EC] bg-white p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md motion-reduce:hover:translate-y-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[11px] font-black uppercase tracking-wide text-[#2F5DE0]">{displayDateOnly(lesson.session_datetime)}</p>
                <h3 className="mt-1.5 text-base font-black text-[#12203D]">{lesson.lesson_number || "Academy lesson"}</h3>
                <p className="mt-1 line-clamp-2 text-sm leading-5 text-[#7A8296]">{lesson.lesson_topic || "Curriculum lesson"}</p>
              </div>
              <span className={`shrink-0 rounded-full px-2 py-1 text-[10.5px] font-black ${lessonStatusBadge[lessonDisplayStatus(lesson)]}`}>
                {lessonDisplayStatus(lesson)}
              </span>
            </div>
            <div className="mt-3.5 grid gap-2 rounded-xl bg-[#F7F8FA] p-3 text-xs text-[#5B6478] sm:grid-cols-2">
              <div>
                <p className="font-bold">Start time</p>
                <p className="mt-1">{displayTimeOnly(lesson.start_time || lesson.session_datetime)}</p>
              </div>
              <div>
                <p className="font-bold">End time</p>
                <p className="mt-1">{displayTimeOnly(lesson.end_time)}</p>
              </div>
              <div className="sm:col-span-2">
                <p className="font-bold">Evaluator / Academic Director</p>
                <p className="mt-1">{lesson.evaluator_name || "Academic Director"}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------- Active teacher cabinet ------------------------- */

type FlatLesson = {
  key: string;
  group: GroupGradebook["group"];
  lesson: Lesson;
  parsedDate: number | null;
  attendanceMarked: boolean;
  homeworkChecked: boolean;
};

function flattenGroupLessons(groups: GroupGradebook[]): FlatLesson[] {
  const rows: FlatLesson[] = [];
  groups.forEach((group) => {
    group.lessons.forEach((lesson) => {
      const parsed = Date.parse(lesson.date || "");
      const attendanceMarked = group.enrollments.some((enrollment) => Boolean(enrollment.attendance?.[lesson.lessonNumber]));
      const homeworkChecked = group.enrollments.some((enrollment) => enrollment.homework?.[lesson.lessonNumber] != null);
      rows.push({
        key: `${group.group.id}-${lesson.id}`,
        group: group.group,
        lesson,
        parsedDate: Number.isNaN(parsed) ? null : parsed,
        attendanceMarked,
        homeworkChecked,
      });
    });
  });
  return rows;
}

function startOfToday() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now.getTime();
}

function ActiveNextLessonCard({ flatLessons, onViewTimetable }: { flatLessons: FlatLesson[]; onViewTimetable: () => void }) {
  const today = startOfToday();
  const dated = flatLessons.filter((row) => row.parsedDate !== null);
  const upcoming = dated
    .filter((row) => (row.parsedDate as number) >= today)
    .sort((first, second) => (first.parsedDate as number) - (second.parsedDate as number))[0];
  const latest = dated.sort((first, second) => (second.parsedDate as number) - (first.parsedDate as number))[0];
  const next = upcoming || latest || flatLessons[flatLessons.length - 1] || null;

  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      <p className="text-[11px] font-black uppercase tracking-wide text-[#7A8296]">
        {upcoming ? "Next lesson" : "Latest lesson"}
      </p>
      {next ? (
        <>
          <p className="mt-2 line-clamp-2 text-[15px] font-black leading-5 text-[#12203D]">
            {next.lesson.lessonNumber ? `${next.lesson.lessonNumber} — ` : ""}
            {next.lesson.topic || "Lesson"}
          </p>
          <p className="mt-1.5 text-sm font-medium text-[#5B6478]">
            {next.group.name} · {next.group.subjectName}
          </p>
          <p className="mt-1 text-xs font-semibold text-[#7A8296]">{displayDateOnly(next.lesson.date)}</p>
          <button
            type="button"
            onClick={onViewTimetable}
            className="mt-3 inline-flex h-9 items-center rounded-[0.5625rem] bg-[#F4F6FA] px-3.5 text-xs font-black text-[#12203D] transition-colors hover:bg-[#E4E7EC]"
          >
            View timetable
          </button>
        </>
      ) : (
        <p className="mt-2 rounded-xl border border-dashed border-[#E4E7EC] bg-[#F7F8FA] px-3 py-4 text-sm font-semibold text-[#7A8296]">
          Not scheduled
        </p>
      )}
    </section>
  );
}

function groupHomeworkRate(group: GroupGradebook) {
  const students = group.enrollments.length;
  const lessons = group.lessons.length;
  if (!students || !lessons) return null;
  let checked = 0;
  group.enrollments.forEach((enrollment) => {
    group.lessons.forEach((lesson) => {
      if (enrollment.homework?.[lesson.lessonNumber] != null) checked += 1;
    });
  });
  return Math.round((checked / (students * lessons)) * 100);
}

function GroupPerformanceCards({ groups }: { groups: GroupGradebook[] }) {
  if (!groups.length) {
    return (
      <EmptyState
        icon={<Users className="h-5 w-5" />}
        title="No active group assigned"
        detail="Groups appear here after the Academic Department assigns them."
      />
    );
  }
  return (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {groups.map((group) => {
        const attendanceRate = countAttendance([group]);
        const avg = average(group.enrollments.map((enrollment) => enrollment.averageGrade));
        const homeworkRate = groupHomeworkRate(group);
        const currentLesson = group.lessons[group.lessons.length - 1];
        const lowAttendance = attendanceRate > 0 && attendanceRate < 70;
        return (
          <article key={group.group.id} className="rounded-[0.875rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-black text-[#12203D]">{group.group.name}</p>
                <p className="mt-0.5 truncate text-xs font-semibold text-[#7A8296]">{group.group.subjectName}</p>
              </div>
              {lowAttendance ? (
                <span className="shrink-0 rounded-full bg-[#FFF3E9] px-2 py-1 text-[10.5px] font-black text-[#B8722E]">Low attendance</span>
              ) : (
                <span className="shrink-0 rounded-full bg-[#F4F6FA] px-2 py-1 text-[10.5px] font-black text-[#7A8296]">
                  {group.enrollments.length} students
                </span>
              )}
            </div>
            <p className="mt-2 truncate text-xs font-semibold text-[#7A8296]">
              Current lesson: {currentLesson ? `${currentLesson.lessonNumber} — ${currentLesson.topic}` : "Not scheduled"}
            </p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-xl bg-[#F7F8FA] px-2 py-2">
                <p className="text-sm font-black text-[#12203D]">{attendanceRate ? `${attendanceRate}%` : "-"}</p>
                <p className="mt-0.5 text-[10px] font-bold text-[#9AA1B2]">Attendance</p>
              </div>
              <div className="rounded-xl bg-[#F7F8FA] px-2 py-2">
                <p className="text-sm font-black text-[#12203D]">{avg ? avg.toFixed(1) : "-"}</p>
                <p className="mt-0.5 text-[10px] font-bold text-[#9AA1B2]">AAP</p>
              </div>
              <div className="rounded-xl bg-[#F7F8FA] px-2 py-2">
                <p className="text-sm font-black text-[#12203D]">{homeworkRate === null ? "-" : `${homeworkRate}%`}</p>
                <p className="mt-0.5 text-[10px] font-bold text-[#9AA1B2]">Homework</p>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function PendingActionsCard({ flatLessons }: { flatLessons: FlatLesson[] }) {
  const recentByGroup = new Map<number, FlatLesson[]>();
  flatLessons.forEach((row) => {
    const list = recentByGroup.get(row.group.id) || [];
    list.push(row);
    recentByGroup.set(row.group.id, list);
  });
  const actions: Array<{ key: string; label: string; detail: string }> = [];
  recentByGroup.forEach((rows) => {
    rows
      .slice(-2)
      .forEach((row) => {
        if (!row.attendanceMarked) {
          actions.push({
            key: `att-${row.key}`,
            label: "Mark attendance",
            detail: `${row.group.name} · ${row.lesson.lessonNumber || row.lesson.topic}`,
          });
        }
        if (!row.homeworkChecked) {
          actions.push({
            key: `hw-${row.key}`,
            label: "Check homework",
            detail: `${row.group.name} · ${row.lesson.lessonNumber || row.lesson.topic}`,
          });
        }
      });
  });

  return (
    <section className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-black text-[#12203D]">Pending actions</p>
        {actions.length ? (
          <span className="rounded-full bg-[#FFF3E9] px-2 py-1 text-[10.5px] font-black text-[#B8722E]">{actions.length}</span>
        ) : null}
      </div>
      {actions.length ? (
        <div className="mt-3 space-y-2">
          {actions.slice(0, 5).map((action) => (
            <div key={action.key} className="flex items-center justify-between gap-3 rounded-xl bg-[#F7F8FA] px-3 py-2.5">
              <div className="min-w-0">
                <p className="text-xs font-black text-[#12203D]">{action.label}</p>
                <p className="mt-0.5 truncate text-[11px] font-semibold text-[#7A8296]">{action.detail}</p>
              </div>
              <ClipboardList className="h-4 w-4 shrink-0 text-[#2F5DE0]" />
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 rounded-xl border border-dashed border-[#E4E7EC] bg-[#F7F8FA] px-3 py-4 text-sm font-semibold text-[#7A8296]">
          All caught up. No pending actions.
        </p>
      )}
    </section>
  );
}

function ActiveReportsScreen({ groups, flatLessons }: { groups: GroupGradebook[]; flatLessons: FlatLesson[] }) {
  if (!groups.length) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-5 w-5" />}
        title="No lesson reports yet"
        detail="Lesson activity appears here once groups and lessons are assigned."
      />
    );
  }
  const rows = [...flatLessons].sort((first, second) => (second.parsedDate ?? 0) - (first.parsedDate ?? 0));
  return (
    <section className="space-y-3">
      <SectionHeading title="Reports" subtitle="Attendance and homework status per lesson" />
      <div className="grid gap-2.5 lg:grid-cols-2">
        {rows.map((row) => {
          const submitted = row.attendanceMarked && row.homeworkChecked;
          const draft = row.attendanceMarked || row.homeworkChecked;
          const badge = submitted
            ? { label: "Submitted", className: "bg-[#EAF6EF] text-[#1E7A5C]" }
            : draft
              ? { label: "Draft", className: "bg-[#EFF3FF] text-[#2F5DE0]" }
              : { label: "Pending", className: "bg-[#F4F6FA] text-[#7A8296]" };
          return (
            <article key={row.key} className="rounded-[0.875rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-2.5">
                <p className="line-clamp-2 min-w-0 text-sm font-black leading-5 text-[#12203D]">
                  {row.lesson.lessonNumber ? `${row.lesson.lessonNumber} — ` : ""}
                  {row.lesson.topic || "Lesson"}
                </p>
                <span className={`shrink-0 rounded-full px-2 py-1 text-[10.5px] font-black ${badge.className}`}>{badge.label}</span>
              </div>
              <p className="mt-1 text-xs font-semibold text-[#7A8296]">
                {row.group.name} · {displayDateOnly(row.lesson.date)}
              </p>
              <div className="mt-2.5 flex flex-wrap gap-2 text-[11px] font-bold">
                <span className={`rounded-full px-2 py-1 ${row.attendanceMarked ? "bg-[#EAF6EF] text-[#1E7A5C]" : "bg-[#F4F6FA] text-[#9AA1B2]"}`}>
                  Attendance {row.attendanceMarked ? "✓" : "—"}
                </span>
                <span className={`rounded-full px-2 py-1 ${row.homeworkChecked ? "bg-[#EAF6EF] text-[#1E7A5C]" : "bg-[#F4F6FA] text-[#9AA1B2]"}`}>
                  Homework {row.homeworkChecked ? "✓" : "—"}
                </span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ActiveTimetableScreen({ flatLessons }: { flatLessons: FlatLesson[] }) {
  if (!flatLessons.length) {
    return (
      <EmptyState
        icon={<CalendarDays className="h-5 w-5" />}
        title="No timetable yet"
        detail="Scheduled lessons appear here once the group schedule is recorded."
      />
    );
  }
  const today = startOfToday();
  const tomorrow = today + 24 * 60 * 60 * 1000;
  const dated = flatLessons.filter((row) => row.parsedDate !== null);
  const todayRows = dated.filter((row) => (row.parsedDate as number) >= today && (row.parsedDate as number) < tomorrow);
  const upcomingRows = dated
    .filter((row) => (row.parsedDate as number) >= tomorrow)
    .sort((first, second) => (first.parsedDate as number) - (second.parsedDate as number))
    .slice(0, 12);
  const recentRows = dated
    .filter((row) => (row.parsedDate as number) < today)
    .sort((first, second) => (second.parsedDate as number) - (first.parsedDate as number))
    .slice(0, 8);
  const undatedRows = flatLessons.filter((row) => row.parsedDate === null).slice(0, 8);

  const sections: Array<{ title: string; rows: FlatLesson[] }> = [
    { title: "Today", rows: todayRows },
    { title: "Upcoming", rows: upcomingRows },
    { title: "Recent", rows: recentRows.length ? recentRows : undatedRows },
  ].filter((section) => section.rows.length);

  return (
    <section className="space-y-4">
      <SectionHeading title="Timetable" subtitle="Lessons grouped by date, today first" />
      {sections.length ? (
        sections.map((section) => (
          <div key={section.title} className="space-y-2">
            <p className="px-1 text-[11px] font-black uppercase tracking-wide text-[#7A8296]">{section.title}</p>
            {section.rows.map((row) => (
              <article key={`${section.title}-${row.key}`} className="flex items-center gap-3 rounded-[0.875rem] border border-[#E4E7EC] bg-white p-3.5 shadow-sm">
                <div className="flex h-10 w-14 shrink-0 flex-col items-center justify-center rounded-xl bg-[#F4F6FA] text-[#2F5DE0]">
                  <span className="text-[10px] font-black uppercase">{displayDateOnly(row.lesson.date).split(" ")[1] || ""}</span>
                  <span className="text-sm font-black">{displayDateOnly(row.lesson.date).split(" ")[0] || "-"}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-black text-[#12203D]">
                    {row.lesson.lessonNumber ? `${row.lesson.lessonNumber} — ` : ""}
                    {row.lesson.topic || "Lesson"}
                  </p>
                  <p className="mt-0.5 truncate text-xs font-semibold text-[#7A8296]">
                    {row.group.name} · {row.group.subjectName}
                  </p>
                </div>
              </article>
            ))}
          </div>
        ))
      ) : (
        <p className="rounded-xl border border-dashed border-[#E4E7EC] bg-white/70 px-3 py-6 text-center text-sm font-semibold text-[#7A8296]">
          Lesson dates are not recorded yet.
        </p>
      )}
    </section>
  );
}

function ActiveProfileInfo({ teacher, groups }: { teacher: TeacherInfo; groups: GroupGradebook[] }) {
  const groupNames = groups.map((group) => group.group.name).filter(Boolean);
  const rows: Array<[string, string]> = [
    ["Teacher code", teacher.login || "-"],
    ["Role", "Active Teacher"],
    ["Category", teacher.category || "Not set"],
    ["Semester stage", teacher.semester_stage || "Not set"],
    ["Groups", groupNames.length ? groupNames.join(", ") : teacher.assigned_group || "Not assigned"],
    ["Performance score", asNumber(teacher.performance_score) ? asNumber(teacher.performance_score).toFixed(1) : "-"],
  ];
  return (
    <div className="overflow-hidden rounded-[0.875rem] border border-[#E4E7EC] bg-white shadow-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between gap-3 border-b border-[#EEF1F6] px-4 py-3 last:border-b-0">
          <span className="shrink-0 text-xs font-semibold text-[#7A8296]">{label}</span>
          <span className="truncate text-[13px] font-black text-[#12203D]">{value}</span>
        </div>
      ))}
    </div>
  );
}

function CompactGradebook({ groups }: { groups: GroupGradebook[] }) {
  if (!groups.length) {
    return (
      <EmptyState
        icon={<Users className="h-5 w-5" />}
        title="No active group assigned"
        detail="Academy teachers will see academy lessons first. Active groups appear here after promotion and assignment."
      />
    );
  }
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {groups.map((group) => (
        <div key={group.group.id} className="overflow-hidden rounded-[0.875rem] border border-[#E4E7EC] bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-[#EEF1F6] px-4 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-black text-[#12203D]">{group.group.name}</p>
              <p className="truncate text-xs text-[#7A8296]">{group.group.subjectName}</p>
            </div>
            <span className="rounded-full bg-[#F4F6FA] px-2.5 py-1 text-[11px] font-black text-[#7A8296]">
              {group.enrollments.length} students
            </span>
          </div>
          <div className="miniapp-table-scroll max-h-80">
            <table className="w-full min-w-[32rem] text-left text-xs">
              <thead className="sticky top-0 bg-[#F7F8FA] text-[10px] uppercase tracking-wide text-[#7A8296]">
                <tr>
                  <th className="px-4 py-2">Student</th>
                  <th className="px-3 py-2 text-center">AAP</th>
                  <th className="px-3 py-2 text-center">Lessons</th>
                  <th className="px-3 py-2 text-center">Exams</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EEF1F6]">
                {group.enrollments.map((enrollment) => (
                  <tr key={enrollment.enrollmentId} className="hover:bg-[#F7F8FA]">
                    <td className="px-4 py-2.5 font-bold text-[#12203D]">{enrollment.fullName}</td>
                    <td className="px-3 py-2.5 text-center font-black text-[#2F5DE0]">
                      {enrollment.averageGrade > 0 ? enrollment.averageGrade.toFixed(0) : "-"}
                    </td>
                    <td className="px-3 py-2.5 text-center font-semibold text-[#7A8296]">{group.lessons.length}</td>
                    <td className="px-3 py-2.5 text-center font-semibold text-[#7A8296]">
                      {Object.keys(enrollment.exams || {}).length}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

function ActiveChartsSection({ groups }: { groups: GroupGradebook[] }) {
  const { ref, visible } = useLazyVisible({ rootMargin: "160px" });
  const hasData = groups.some((group) => group.enrollments.length && group.lessons.length);
  if (!hasData) return null;
  return (
    <div ref={ref} className="min-h-[10rem]">
      {visible ? (
        <Suspense
          fallback={
            <div className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 text-sm font-semibold text-[#9AA1B2] shadow-sm">
              Loading charts...
            </div>
          }
        >
          <ActiveTeacherCharts groups={groups} />
        </Suspense>
      ) : null}
    </div>
  );
}

export default function TeacherHome(props: TeacherPageProps) {
  const teacher = props.teacher;
  const groups = Array.isArray(props.groups) ? props.groups : [];
  const academy = props.academy || null;
  const academySummary = props.academySummary || {};
  const academyUpdates = Array.isArray(props.academyUpdates) ? props.academyUpdates : [];
  const journey = Array.isArray(props.journey) ? props.journey : [];
  const reports = Array.isArray(props.lessonReports) ? props.lessonReports : [];
  const trainingTimetable = Array.isArray(props.trainingTimetable) ? props.trainingTimetable : [];
  const [activeTab, setActiveTab] = useState<TabKey>("home");
  const [openReport, setOpenReport] = useState<{ report: AcademyAssessment; assignment: AcademyAssignment | null } | null>(null);

  const progress = academy?.progress || null;
  const assignedCount = asNumber(academySummary.assigned_count ?? progress?.assigned_count) || journey.length;
  // The progress target always equals the number of assigned lessons chosen by
  // the Academic Director (never a fixed 12-lesson pack).
  const targetLessons = asNumber(academySummary.target_lessons) || asNumber(progress?.target_lessons) || assignedCount;
  const assessedCount = asNumber(academySummary.assessed_count ?? academySummary.completed_count ?? progress?.assessed_count);
  const remainingCount = Math.max(asNumber(academySummary.remaining_count) || assignedCount - assessedCount, 0);
  const academyProgressPercent = asNumber(academySummary.progress_percent) || (targetLessons ? Math.min(100, Math.round((assessedCount / targetLessons) * 100)) : 0);
  const reportChartRows = useMemo(() => reportRows(reports), [reports]);
  const flatLessons = useMemo(() => flattenGroupLessons(groups), [groups]);
  const totalStudents = groups.reduce((sum, group) => sum + group.enrollments.length, 0);
  const groupAverage = average(groups.flatMap((group) => group.enrollments.map((enrollment) => enrollment.averageGrade)));
  const attendanceRate = countAttendance(groups);
  const pendingReports = flatLessons.filter((row) => !row.attendanceMarked || !row.homeworkChecked).length;
  const isTraining = Boolean(academy);
  const cabinetMode = isTraining ? "academy" : "active";
  const visibleTabs = isTraining ? academyTabs : activeTeacherTabs;
  const mobileTabs = isTraining ? teacherMobileTabs : activeTeacherMobileTabs;
  const workspaceCards = Array.isArray(props.workspaceCards) ? props.workspaceCards : [];
  const activeFallbackCards: WorkspaceCard[] = [
    { label: "Groups", value: String(groups.length || "-"), detail: "active teaching groups" },
    { label: "Students", value: String(totalStudents || "-"), detail: "in assigned groups" },
    {
      label: "Reports Pending",
      value: String(pendingReports),
      detail: "attendance or homework to record",
      tone: pendingReports ? "text-amber-600" : "text-emerald-600",
    },
    {
      label: "Avg Attendance",
      value: attendanceRate ? `${attendanceRate}%` : "-",
      detail: groupAverage ? `class AAP ${groupAverage.toFixed(1)}` : "recorded attendance",
      tone: "text-emerald-600",
    },
  ];
  const academyFallbackCards: WorkspaceCard[] = [
    { label: "Assigned Lessons", value: String(assignedCount || "-"), detail: "academy lesson sequence" },
    { label: "Completed/Assessed", value: String(assessedCount || "0"), detail: "reports received", tone: "text-emerald-600" },
    { label: "Remaining Lessons", value: String(remainingCount), detail: `${academyProgressPercent}% complete`, tone: "text-blue-600" },
    {
      label: "Average Score",
      value:
        academySummary.average_score !== null && academySummary.average_score !== undefined
          ? asNumber(academySummary.average_score).toFixed(1)
          : progress?.average_score
            ? progress.average_score.toFixed(1)
            : "-",
      detail: "academy assessment average",
    },
  ];
  const summaryCards = isTraining ? (workspaceCards.length ? workspaceCards : academyFallbackCards) : activeFallbackCards;

  const handleOpenReport = (report: AcademyAssessment, assignment?: AcademyAssignment | null) => {
    const matched = assignment || journey.find((item) => item.id === asNumber(report.lesson_assignment_id)) || null;
    setOpenReport({ report, assignment: matched });
  };

  return (
    <div className="app-min-height bg-[#F0F2F6] text-[#12203D] md:flex">
      {openReport ? (
        <LessonReportSheet report={openReport.report} assignment={openReport.assignment} onClose={() => setOpenReport(null)} />
      ) : null}

      <CabinetSidebar
        teacher={teacher}
        academy={academy}
        tabs={visibleTabs}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        csrfToken={props.csrfToken}
      />

      <div className="min-w-0 flex-1">
      <header
        className="z-40 border-b border-[#E4E7EC] bg-white/90 shadow-sm backdrop-blur-xl md:hidden"
        style={{ paddingTop: "var(--app-top-inset)" }}
      >
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#12203D] text-[10px] font-black text-white shadow-sm">
              MSI
            </div>
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-black">Teacher Cabinet</p>
              <p className="truncate text-xs font-semibold text-[#7A8296]">
                {teacher.full_name || "Teacher"} · {teacher.login}
              </p>
            </div>
          </div>
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#2F5DE0] text-xs font-black text-white">
            {teacherInitials(teacher.full_name)}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl space-y-3 px-3 py-3 pb-[calc(var(--app-bottom-inset)+6.5rem)] sm:space-y-4 sm:px-5 sm:py-5 md:pb-6 lg:px-7">
        {isTraining ? null : (
          <section className="rounded-[1rem] border border-[#E4E7EC] bg-[#12203D] p-4 text-white shadow-sm sm:p-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-lg font-black">{teacher.full_name || "Teacher"}</p>
                <p className="mt-1 truncate text-sm font-semibold text-white/60">
                  {teacher.login}
                  {teacher.category ? ` · ${teacher.category}` : ""}
                  {teacher.assigned_group ? ` · ${teacher.assigned_group}` : ""}
                </p>
              </div>
              <span className="shrink-0 rounded-full bg-emerald-400/20 px-2.5 py-1.5 text-[11px] font-black text-emerald-200">
                Active Teacher
              </span>
            </div>
          </section>
        )}

        {activeTab === "home" ? (
          <section className="space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-300 sm:space-y-4">
            {isTraining ? (
              <>
                <AcademyIdentityCard teacher={teacher} academy={academy} />
                <div className="grid gap-3 lg:grid-cols-2 lg:items-stretch">
                  <AcademyHeroCard
                    academy={academy}
                    assessedCount={assessedCount}
                    targetLessons={targetLessons}
                    progressPercent={academyProgressPercent}
                  />
                  <div className="grid grid-cols-2 gap-2 sm:gap-3">
                    {summaryCards.map((card) => (
                      <MetricCard
                        key={`${card.label}-${card.value}`}
                        label={card.label}
                        value={card.value}
                        detail={card.detail}
                        icon={workspaceCardIcon(card.label)}
                        tone={card.tone}
                      />
                    ))}
                  </div>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <NextLessonPreview
                    lessons={trainingTimetable.length ? trainingTimetable : journey}
                    onViewLessons={() => setActiveTab("reports")}
                  />
                  <LatestFeedbackPreview reports={reports} onViewReport={(report) => handleOpenReport(report)} />
                </div>
                <LatestUpdatePreview updates={academyUpdates} onViewUpdates={() => setActiveTab("updates")} />
                <div className="grid gap-3 lg:grid-cols-2">
                  <AcademyScoreSnapshot rows={reportChartRows} />
                  <RubricBreakdownCard reports={reports} />
                </div>
              </>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-4">
                  {summaryCards.map((card) => (
                    <MetricCard
                      key={`${card.label}-${card.value}`}
                      label={card.label}
                      value={card.value}
                      detail={card.detail}
                      icon={workspaceCardIcon(card.label)}
                      tone={card.tone}
                    />
                  ))}
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <ActiveNextLessonCard flatLessons={flatLessons} onViewTimetable={() => setActiveTab("timetable")} />
                  <PendingActionsCard flatLessons={flatLessons} />
                </div>
                <div className="space-y-2">
                  <p className="px-1 text-[11px] font-black uppercase tracking-wide text-[#7A8296]">Group performance</p>
                  <GroupPerformanceCards groups={groups} />
                </div>
                <ActiveChartsSection groups={groups} />
                <div className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm">
                  <div className="mb-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-black text-[#12203D]">My Groups</p>
                      <p className="text-xs text-[#7A8296]">Current teaching assignments</p>
                    </div>
                    <GraduationCap className="h-4 w-4 text-[#2F5DE0]" />
                  </div>
                  <CompactGradebook groups={groups} />
                </div>
              </>
            )}
          </section>
        ) : null}

        {activeTab === "reports" ? (
          <section className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            {isTraining ? (
              <AcademyLessonsScreen
                assignments={journey}
                reports={reports}
                onOpenReport={(report, assignment) => handleOpenReport(report, assignment)}
              />
            ) : (
              <ActiveReportsScreen groups={groups} flatLessons={flatLessons} />
            )}
          </section>
        ) : null}

        {activeTab === "timetable" ? (
          <section className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            {isTraining ? <Timetable lessons={trainingTimetable} /> : <ActiveTimetableScreen flatLessons={flatLessons} />}
          </section>
        ) : null}

        {activeTab === "profile" ? (
          <section className="space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-300 sm:space-y-4">
            <SectionHeading title="Profile" subtitle={isTraining ? "Academy identity and account" : "Teacher identity and account"} />
            <div className="flex items-center gap-3.5 rounded-[1rem] border border-[#E4E7EC] bg-[#12203D] p-4 text-white shadow-sm sm:p-5">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#2F5DE0] text-base font-black text-white">
                {teacherInitials(teacher.full_name)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-base font-black">{teacher.full_name || "Teacher"}</p>
                <p className="truncate text-xs font-semibold text-white/60">
                  {teacher.login}
                  {academy?.subject ? ` · ${academy.subject}` : teacher.assigned_group ? ` · ${teacher.assigned_group}` : ""}
                </p>
                <span className="mt-1.5 inline-flex rounded-full bg-[#2F5DE0]/28 px-2 py-0.5 text-[10.5px] font-black text-[#B9CBFF]">
                  {isTraining ? `Academy · ${statusLabel(academy?.academy_status || "in_training")}` : "Active Teacher"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab("timetable")}
                className={`${isTraining ? "hidden sm:inline-flex" : "hidden"} h-9 shrink-0 items-center gap-2 rounded-xl bg-white/10 px-3 text-xs font-black text-white transition-colors hover:bg-white/15`}
              >
                <CalendarDays className="h-4 w-4" />
                Timetable
              </button>
            </div>
            {isTraining ? (
              <AcademyProfileSummary teacher={teacher} academy={academy} summary={academySummary} targetLessons={targetLessons} />
            ) : (
              <ActiveProfileInfo teacher={teacher} groups={groups} />
            )}
            {isTraining ? <AcademyScoreSnapshot rows={reportChartRows} /> : null}
            <form action={routes.logout} method="post">
              <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
              <button
                type="submit"
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#F1D9D3] bg-white px-4 py-3 text-sm font-black text-[#C0402C] shadow-sm transition-colors hover:bg-[#FDF6F4]"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </button>
            </form>
          </section>
        ) : null}

        {activeTab === "career" ? (
          <section className="grid gap-3 lg:grid-cols-[0.8fr_1.2fr] animate-in fade-in slide-in-from-bottom-2 duration-300 sm:gap-4">
            <div className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm sm:p-5">
              <p className="text-sm font-black text-[#12203D]">Career Position</p>
              <div className="mt-4 space-y-3">
                <MetricCard label="Status" value={isTraining ? statusLabel(academy?.academy_status || "in_training") : "Active"} detail="current stage" icon={<CheckCircle2 className="h-4 w-4" />} />
                <MetricCard label="Stage" value={teacher.semester_stage || "-"} detail="semester progression" icon={<TrendingUp className="h-4 w-4" />} />
                <MetricCard label="Score" value={asNumber(teacher.performance_score).toFixed(1)} detail="profile performance" icon={<Star className="h-4 w-4" />} tone="text-[#2F5DE0]" />
              </div>
            </div>
            <div className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm sm:p-5">
              <p className="text-sm font-black text-[#12203D]">Growth Path</p>
              <div className="mt-5 space-y-4">
                {["Academy lessons", "Assessment reports", "Promotion review", "Active teacher"].map((label, index) => {
                  const completed =
                    !isTraining ||
                    (index === 0 && assignedCount > 0) ||
                    (index === 1 && assessedCount > 0) ||
                    (index === 2 && String(academy?.academy_status || "").includes("ready")) ||
                    (index === 3 && String(academy?.academy_status || "") === "approved");
                  return (
                    <div key={label} className="flex gap-3">
                      <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black ${completed ? "bg-[#2F5DE0] text-white" : "bg-[#F4F6FA] text-[#9AA1B2]"}`}>
                        {index + 1}
                      </div>
                      <div>
                        <p className="text-sm font-black text-[#12203D]">{label}</p>
                        <p className="text-xs text-[#7A8296]">{completed ? "In progress or completed" : "Waiting for previous step"}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        ) : null}

        {activeTab === "updates" ? (
          <section className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            {isTraining ? (
              <AcademyUpdates updates={academyUpdates} />
            ) : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {[
                  ["Teacher Academy", "Follow the assigned lesson sequence and prepare using the guidance notes."],
                  ["Lesson Reports", "Scores and remarks appear after each Academic Director assessment."],
                  ["Timetable", "Scheduled Teacher Academy sessions are controlled by the Academic Director."],
                ].map(([title, detail]) => (
                  <div key={title} className="rounded-[1rem] border border-[#E4E7EC] bg-white p-4 shadow-sm sm:p-5">
                    <Bell className="h-4 w-4 text-[#2F5DE0]" />
                    <p className="mt-3 text-sm font-black text-[#12203D]">{title}</p>
                    <p className="mt-1 text-sm leading-6 text-[#7A8296]">{detail}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        ) : null}
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-40 border-t border-[#E4E7EC] bg-white/95 px-2 pt-2 shadow-[0_-10px_30px_rgba(18,32,61,0.10)] backdrop-blur-xl md:hidden"
        style={{ paddingBottom: "max(0.5rem, var(--app-bottom-inset))" }}
        aria-label="Teacher mobile navigation"
      >
        <div className="mx-auto grid max-w-md grid-cols-4 gap-1">
          {mobileTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = bottomNavActiveKey(activeTab, cabinetMode) === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`flex min-h-[3.25rem] flex-col items-center justify-center gap-1 rounded-2xl px-2 text-[11px] font-black transition-colors ${
                  isActive ? "text-[#2F5DE0]" : "text-[#9AA1B2] hover:bg-[#F4F6FA] hover:text-[#12203D]"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="h-[1.15rem] w-[1.15rem]" />
                <span className="truncate">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
      </div>
    </div>
  );
}
