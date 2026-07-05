import { Fragment, useMemo, useState } from "react";
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
  LineChart as LineChartIcon,
  LogOut,
  Map as MapIcon,
  Star,
  TrendingUp,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { routes } from "@/shared/lib/routes";
import { bottomNavActiveKey, type TeacherTabKey } from "@/roles/teacher/teacherNav";

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

const scoreLabels: Record<string, string> = {
  teacher_guidance_compliance_score: "Teacher guidance compliance",
  timing_adherence_score: "Timing adherence",
  resource_familiarity_score: "Resource familiarity",
  english_fluency_score: "English fluency",
  confidence_delivery_score: "Confidence and delivery",
  engagement_technique_score: "Engagement technique",
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
  return String(value || "assigned").replace(/_/g, " ");
}

function statusClass(value: string) {
  const normalized = String(value || "").toLowerCase();
  if (["passed", "approved", "approved_for_active_teacher", "ready_for_active_teacher"].includes(normalized)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (["assessed", "ready", "ready_for_evaluation"].includes(normalized)) {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  if (["needs_improvement", "rejected"].includes(normalized)) {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

function average(values: number[]) {
  const clean = values.filter((value) => Number.isFinite(value) && value > 0);
  return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : 0;
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

function groupPerformanceRows(groups: GroupGradebook[]) {
  return groups.map((group) => ({
    name: group.group.name,
    students: group.enrollments.length,
    avg: Number(average(group.enrollments.map((enrollment) => enrollment.averageGrade)).toFixed(1)),
    lessons: group.lessons.length,
  }));
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
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md motion-reduce:hover:translate-y-0 sm:rounded-2xl sm:p-4">
      <div className="flex items-start justify-between gap-2 sm:gap-3">
        <div className="min-w-0">
          <p className="truncate text-[10px] font-bold uppercase leading-4 tracking-wide text-slate-500 sm:text-[11px]">{label}</p>
          <p className={`mt-1 truncate text-xl font-black leading-7 sm:mt-2 sm:text-2xl ${tone}`}>{value}</p>
          <p className="mt-0.5 line-clamp-2 text-[11px] font-medium leading-4 text-slate-500 sm:mt-1 sm:text-xs">{detail}</p>
        </div>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600 sm:h-9 sm:w-9">
          {icon}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
  return (
    <div className="flex min-h-[18rem] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white/70 px-6 text-center">
      <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">{icon}</div>
      <p className="text-sm font-black text-slate-900">{title}</p>
      <p className="mt-1 max-w-md text-sm text-slate-500">{detail}</p>
    </div>
  );
}

function Roadmap({ assignments, reports }: { assignments: AcademyAssignment[]; reports: AcademyAssessment[] }) {
  const reportByAssignment = new Map(reports.map((report) => [asNumber(report.lesson_assignment_id), report]));
  if (!assignments.length) {
    return (
      <EmptyState
        icon={<MapIcon className="h-5 w-5" />}
        title="No academy roadmap yet"
        detail="Once lessons are assigned by the Academic Director, they appear here in sequence."
      />
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {assignments.map((assignment, index) => {
        const report = reportByAssignment.get(assignment.id);
        const score = asNumber(report?.weighted_overall_score);
        return (
          <div
            key={assignment.id}
            className="group rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md motion-reduce:hover:translate-y-0"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-black text-blue-700">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-black text-slate-900">
                    {assignment.lesson_number || `Lesson ${index + 1}`}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs font-semibold leading-5 text-slate-500">
                    {assignment.lesson_topic || "Curriculum lesson"}
                  </p>
                </div>
              </div>
              <span className={`shrink-0 rounded-full border px-2 py-1 text-[10px] font-black uppercase ${statusClass(assignment.status)}`}>
                {score ? score.toFixed(1) : statusLabel(assignment.status)}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-bold text-slate-500">
              <span className="rounded-full bg-slate-100 px-2 py-1">{displayDate(assignment.session_datetime)}</span>
              {assignment.evaluator_name ? <span className="rounded-full bg-slate-100 px-2 py-1">{assignment.evaluator_name}</span> : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CompactGradebook({ groups }: { groups: GroupGradebook[] }) {
  if (!groups.length) {
    return (
      <EmptyState
        icon={<Users className="h-5 w-5" />}
        title="No active group assigned"
        detail="Training teachers will see academy lessons first. Active groups appear here after promotion and assignment."
      />
    );
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {groups.map((group) => (
        <div key={group.group.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-black text-slate-900">{group.group.name}</p>
              <p className="truncate text-xs text-slate-500">{group.group.subjectName}</p>
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-black text-slate-600">
              {group.enrollments.length} students
            </span>
          </div>
          <div className="miniapp-table-scroll max-h-80">
            <table className="w-full min-w-[32rem] text-left text-xs">
              <thead className="sticky top-0 bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Student</th>
                  <th className="px-3 py-2 text-center">AAP</th>
                  <th className="px-3 py-2 text-center">Lessons</th>
                  <th className="px-3 py-2 text-center">Exams</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {group.enrollments.map((enrollment) => (
                  <tr key={enrollment.enrollmentId} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 font-bold text-slate-900">{enrollment.fullName}</td>
                    <td className="px-3 py-2.5 text-center font-black text-blue-600">
                      {enrollment.averageGrade > 0 ? enrollment.averageGrade.toFixed(0) : "-"}
                    </td>
                    <td className="px-3 py-2.5 text-center font-semibold text-slate-500">{group.lessons.length}</td>
                    <td className="px-3 py-2.5 text-center font-semibold text-slate-500">
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

function ReportsTable({ reports }: { reports: AcademyAssessment[] }) {
  if (!reports.length) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-5 w-5" />}
        title="No lesson reports yet"
        detail="Assessment reports will appear here after the Academic Director evaluates training lessons."
      />
    );
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="miniapp-table-scroll max-h-[68dvh]">
        <table className="w-full min-w-[58rem] border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Lesson</th>
              <th className="px-3 py-3">Date</th>
              <th className="px-3 py-3">Evaluator</th>
              <th className="px-3 py-3">Scores</th>
              <th className="px-3 py-3 text-center">Overall</th>
              <th className="px-3 py-3">Decision</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {reports.map((report) => {
              const scorePairs = Object.entries(report.scores || {}).filter(([, value]) => asNumber(value) > 0);
              return (
                <Fragment key={report.id}>
                  <tr className="align-top transition-colors hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="font-black text-slate-900">{report.lesson_number || "Lesson"}</p>
                      <p className="mt-1 line-clamp-2 text-xs text-slate-500">{report.lesson_topic || "Training lesson"}</p>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 font-semibold text-slate-600">{displayDate(report.assessment_datetime)}</td>
                    <td className="px-3 py-3 font-semibold text-slate-600">{report.evaluator_name || "Academic Director"}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {scorePairs.map(([key, value]) => (
                          <span key={key} className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-black text-blue-700">
                            {scoreLabels[key] || key}: {asNumber(value).toFixed(1)}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-center text-base font-black text-slate-900">
                      {asNumber(report.weighted_overall_score).toFixed(1)}
                    </td>
                    <td className="px-3 py-3">
                      <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase ${statusClass(report.decision)}`}>
                        {statusLabel(report.decision)}
                      </span>
                    </td>
                  </tr>
                  <tr className="bg-slate-50/60">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="grid gap-3 md:grid-cols-3">
                        <div className="rounded-xl bg-white p-3">
                          <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">Written report from Academic Department</p>
                          <p className="mt-1 text-sm leading-6 text-slate-600">{report.final_recommendation || "No written report yet."}</p>
                        </div>
                        <div className="rounded-xl bg-white p-3">
                          <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">Strengths</p>
                          <p className="mt-1 text-sm leading-6 text-slate-600">{report.strengths || "Not recorded yet."}</p>
                        </div>
                        <div className="rounded-xl bg-white p-3">
                          <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">Areas for improvement</p>
                          <p className="mt-1 text-sm leading-6 text-slate-600">{report.areas_for_improvement || "Not recorded yet."}</p>
                        </div>
                      </div>
                      <div className="mt-3 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700">
                        Final recommendation: {report.final_recommendation || statusLabel(report.decision)}
                      </div>
                    </td>
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AcademyProfileSummary({
  academy,
  summary,
}: {
  academy: AcademyTeacher | null;
  summary: AcademySummary;
}) {
  const averageScore = summary.average_score ?? academy?.progress?.average_score ?? null;
  const latestScore = summary.latest_score ?? academy?.progress?.latest_score ?? null;
  const items = [
    ["Rank / Status", `${summary.rank || "Not ranked"} · ${statusLabel(summary.status || academy?.academy_status || "in_training")}`],
    ["Subject", summary.subject || academy?.subject_program_name || academy?.subject || "Subject not set"],
    ["Training Start Date", displayDateOnly(summary.training_start_date || academy?.academy_start_date || "")],
    ["Training End Date", displayDateOnly(summary.training_end_date || academy?.training_end_date || "")],
    ["Average Score", averageScore === null || averageScore === undefined ? "-" : `${asNumber(averageScore).toFixed(1)}/10`],
    ["Latest Score", latestScore === null || latestScore === undefined ? "-" : `${asNumber(latestScore).toFixed(1)}/10`],
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-black text-slate-900">Academy Profile</p>
          <p className="text-xs text-slate-500">Status, subject, dates, and score summary</p>
        </div>
        <GraduationCap className="h-4 w-4 text-blue-600" />
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {items.map(([label, value]) => (
          <div key={label} className="rounded-xl bg-slate-50 p-3">
            <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-1 text-sm font-black text-slate-900">{value}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700">
        Score summary: {summary.score_summary || "No assessments yet."}
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
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {updates.map((item) => (
        <article key={String(item.id)} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <Bell className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
            <span className={`rounded-full border px-2 py-1 text-[10px] font-black uppercase ${statusClass(item.priority || "info")}`}>
              {item.kind || item.priority || "update"}
            </span>
          </div>
          <p className="mt-3 text-sm font-black text-slate-900">{item.title || "Teacher Academy update"}</p>
          {item.body ? <p className="mt-1 text-sm leading-6 text-slate-500">{item.body}</p> : null}
          <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-bold text-slate-500">
            <span>{item.source || "Academic Department"}</span>
            {item.created_at ? <span>{displayDate(item.created_at)}</span> : null}
          </div>
        </article>
      ))}
    </div>
  );
}

function Timetable({ lessons }: { lessons: AcademyAssignment[] }) {
  if (!lessons.length) {
    return (
      <EmptyState
        icon={<CalendarDays className="h-5 w-5" />}
        title="No training sessions scheduled"
        detail="When the Academic Director schedules academy lessons, the teacher will see them here."
      />
    );
  }
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {lessons.map((lesson) => (
        <div key={lesson.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md motion-reduce:hover:translate-y-0">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-black uppercase tracking-wide text-blue-600">{displayDateOnly(lesson.session_datetime)}</p>
              <h3 className="mt-2 text-base font-black text-slate-900">{lesson.lesson_number || "Training lesson"}</h3>
              <p className="mt-1 line-clamp-2 text-sm leading-5 text-slate-500">{lesson.lesson_topic || "Curriculum lesson"}</p>
            </div>
            <span className={`shrink-0 rounded-full border px-2 py-1 text-[10px] font-black uppercase ${statusClass(lesson.status)}`}>
              {statusLabel(lesson.status)}
            </span>
          </div>
          <div className="mt-4 grid gap-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 sm:grid-cols-2">
            <div>
              <p className="font-bold">Start time</p>
              <p className="mt-1">{displayTimeOnly(lesson.start_time || lesson.session_datetime)}</p>
            </div>
            <div>
              <p className="font-bold">End time</p>
              <p className="mt-1">{displayTimeOnly(lesson.end_time)}</p>
            </div>
            <div>
              <p className="font-bold">Evaluator / Academic Director</p>
              <p className="mt-1">{lesson.evaluator_name || "Academic Director"}</p>
            </div>
            <div>
              <p className="font-bold">Status</p>
              <p className="mt-1">{statusLabel(lesson.status)}</p>
            </div>
          </div>
        </div>
      ))}
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

  const progress = academy?.progress || null;
  const targetLessons = asNumber(academySummary.target_lessons) || asNumber(progress?.target_lessons) || 12;
  const assessedCount = asNumber(academySummary.assessed_count ?? academySummary.completed_count ?? progress?.assessed_count);
  const assignedCount = asNumber(academySummary.assigned_count ?? progress?.assigned_count) || journey.length;
  const remainingCount = Math.max(asNumber(academySummary.remaining_count) || assignedCount - assessedCount, 0);
  const academyProgressPercent = asNumber(academySummary.progress_percent) || (targetLessons ? Math.min(100, Math.round((assessedCount / targetLessons) * 100)) : 0);
  const groupRows = useMemo(() => groupPerformanceRows(groups), [groups]);
  const reportChartRows = useMemo(() => reportRows(reports), [reports]);
  const totalStudents = groups.reduce((sum, group) => sum + group.enrollments.length, 0);
  const totalLessons = groups.reduce((sum, group) => sum + group.lessons.length, 0);
  const groupAverage = average(groups.flatMap((group) => group.enrollments.map((enrollment) => enrollment.averageGrade)));
  const attendanceRate = countAttendance(groups);
  const isTraining = Boolean(academy);
  const visibleTabs = isTraining ? academyTabs : activeTeacherTabs;
  const workspaceCards = Array.isArray(props.workspaceCards) ? props.workspaceCards : [];
  const fallbackCards: WorkspaceCard[] = [
    {
      label: isTraining ? "Assigned Lessons" : "Students",
      value: String(isTraining ? assignedCount || "-" : totalStudents || "-"),
      detail: isTraining ? "academy lesson sequence" : "active group roster",
    },
    {
      label: isTraining ? "Completed/Assessed" : "Lessons",
      value: String(isTraining ? assessedCount || "0" : totalLessons || "-"),
      detail: isTraining ? "reports received" : "recorded sessions",
      tone: "text-emerald-600",
    },
    {
      label: isTraining ? "Remaining Lessons" : "Class AAP",
      value: isTraining ? String(remainingCount) : groupAverage ? groupAverage.toFixed(1) : "-",
      detail: isTraining ? `${academyProgressPercent}% complete` : "student average",
      tone: "text-blue-600",
    },
    {
      label: isTraining ? "Average Score" : "Attendance",
      value: isTraining
        ? academySummary.average_score !== null && academySummary.average_score !== undefined
          ? asNumber(academySummary.average_score).toFixed(1)
          : progress?.average_score
            ? progress.average_score.toFixed(1)
            : "-"
        : attendanceRate
          ? `${attendanceRate}%`
          : "-",
      detail: isTraining ? "academy assessment average" : "recorded attendance",
      tone: isTraining ? "text-slate-900" : "text-emerald-600",
    },
  ];
  const summaryCards = workspaceCards.length ? workspaceCards : fallbackCards;

  return (
    <div className="app-min-height bg-slate-50 text-slate-900">
      <header
        className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 shadow-sm backdrop-blur-xl"
        style={{ paddingTop: "var(--app-top-inset)" }}
      >
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-600 font-black text-white shadow-sm">
              {(teacher.full_name || "T").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 leading-tight">
              <p className="truncate text-sm font-black">{teacher.full_name || "Teacher"}</p>
              <p className="truncate text-xs font-semibold text-slate-500">
                {teacher.login}
                {academy?.subject ? ` · ${academy.subject}` : teacher.assigned_group ? ` · ${teacher.assigned_group}` : ""}
              </p>
            </div>
            <span className={`hidden rounded-full border px-2.5 py-1 text-[10px] font-black uppercase sm:inline-flex ${isTraining ? "border-amber-200 bg-amber-50 text-amber-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
              {isTraining ? "Training teacher" : "Active teacher"}
            </span>
          </div>
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <button
              type="submit"
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-black text-slate-700 shadow-sm transition-all hover:bg-slate-50 active:scale-[0.98] motion-reduce:active:scale-100"
              aria-label="Log out"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Log out</span>
            </button>
          </form>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-3 px-3 py-3 pb-[calc(var(--app-bottom-inset)+6.5rem)] sm:space-y-4 sm:px-6 sm:py-4 sm:pb-4">
        <section className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300 sm:rounded-3xl sm:p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-black uppercase tracking-wide text-blue-600">Teacher Cabinet</p>
              <h1 className="mt-1 text-xl font-black text-slate-950 sm:text-2xl">
                {isTraining ? "Teacher Academy" : "Teaching Workspace"}
              </h1>
              <p className="mt-1 max-w-2xl text-sm font-medium text-slate-500">
                {isTraining
                  ? `${academy?.subject_program_name || academy?.subject || "Curriculum"} training path`
                  : "Groups, student progress, lesson activity, and teacher growth in one place."}
              </p>
            </div>
            {isTraining ? (
              <div className="min-w-[14rem] rounded-2xl bg-slate-50 p-3">
                <div className="flex items-center justify-between text-xs font-black text-slate-600">
                  <span>Academy progress</span>
                  <span>{assessedCount}/{targetLessons}</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-slate-200">
                  <div className="h-2 rounded-full bg-blue-600 transition-all duration-500" style={{ width: `${academyProgressPercent}%` }} />
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <nav className="flex gap-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-1 shadow-sm" aria-label="Teacher cabinet">
          {visibleTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`inline-flex h-10 shrink-0 items-center gap-2 rounded-xl px-3 text-xs font-black transition-all duration-200 active:scale-[0.98] motion-reduce:active:scale-100 ${
                  isActive ? "bg-blue-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {activeTab === "home" ? (
          <section className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
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

            {isTraining ? <AcademyProfileSummary academy={academy} summary={academySummary} /> : null}

            <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-black text-slate-900">Performance Snapshot</p>
                    <p className="text-xs text-slate-500">{isTraining ? "Assessment score trend" : "Group average by class"}</p>
                  </div>
                  <LineChartIcon className="h-4 w-4 text-blue-600" />
                </div>
                <div className="h-56">
                  {isTraining ? (
                    reportChartRows.length ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={reportChartRows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
                          <defs>
                            <linearGradient id="teacherScore" x1="0" x2="0" y1="0" y2="1">
                              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.28} />
                              <stop offset="95%" stopColor="#2563eb" stopOpacity={0.02} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
                          <YAxis domain={[0, 10]} hide />
                          <Tooltip />
                          <Area dataKey="score" type="monotone" stroke="#2563eb" strokeWidth={3} fill="url(#teacherScore)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <EmptyState icon={<LineChartIcon className="h-5 w-5" />} title="No scores yet" detail="The chart fills after the first assessment." />
                    )
                  ) : groupRows.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={groupRows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
                        <CartesianGrid stroke="#e2e8f0" strokeDasharray="4 4" vertical={false} />
                        <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
                        <YAxis domain={[0, 9]} hide />
                        <Tooltip />
                        <Bar dataKey="avg" fill="#2563eb" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyState icon={<LineChartIcon className="h-5 w-5" />} title="No group data yet" detail="Group performance appears after assignment." />
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-black text-slate-900">{isTraining ? "Roadmap" : "My Groups"}</p>
                    <p className="text-xs text-slate-500">{isTraining ? "Curriculum-guided training lessons" : "Current teaching assignments"}</p>
                  </div>
                  <GraduationCap className="h-4 w-4 text-blue-600" />
                </div>
                {isTraining ? <Roadmap assignments={journey} reports={reports} /> : <CompactGradebook groups={groups} />}
              </div>
            </div>
          </section>
        ) : null}

        {activeTab === "reports" ? (
          <section className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <ReportsTable reports={reports} />
          </section>
        ) : null}

        {activeTab === "timetable" ? (
          <section className="animate-in fade-in slide-in-from-bottom-2 duration-300">
            <Timetable lessons={trainingTimetable} />
          </section>
        ) : null}

        {activeTab === "profile" ? (
          <section className="space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-300 sm:space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-lg font-black text-white shadow-sm">
                  {(teacher.full_name || "T").slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-base font-black text-slate-900">{teacher.full_name || "Teacher"}</p>
                  <p className="truncate text-xs font-semibold text-slate-500">
                    {teacher.login}
                    {academy?.subject ? ` · ${academy.subject}` : teacher.assigned_group ? ` · ${teacher.assigned_group}` : ""}
                  </p>
                </div>
                <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-black uppercase ${isTraining ? "border-amber-200 bg-amber-50 text-amber-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
                  {isTraining ? "Training" : "Active"}
                </span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab("timetable")}
                  className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-black text-slate-700 shadow-sm transition-all hover:bg-slate-50 active:scale-[0.98] motion-reduce:active:scale-100"
                >
                  <CalendarDays className="h-4 w-4" />
                  Timetable
                </button>
                <form action={routes.logout} method="post">
                  <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
                  <button
                    type="submit"
                    className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-black text-slate-700 shadow-sm transition-all hover:bg-slate-50 active:scale-[0.98] motion-reduce:active:scale-100"
                  >
                    <LogOut className="h-4 w-4" />
                    Log out
                  </button>
                </form>
              </div>
            </div>
            {isTraining ? <AcademyProfileSummary academy={academy} summary={academySummary} /> : null}
          </section>
        ) : null}

        {activeTab === "career" || activeTab === "profile" ? (
          <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr] animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-black text-slate-900">{activeTab === "profile" ? "Teacher Profile" : "Career Position"}</p>
              <div className="mt-4 space-y-3">
                <MetricCard label="Status" value={isTraining ? statusLabel(academy?.academy_status || "in_training") : "Active"} detail="current stage" icon={<CheckCircle2 className="h-4 w-4" />} />
                <MetricCard label="Stage" value={teacher.semester_stage || "-"} detail="semester progression" icon={<TrendingUp className="h-4 w-4" />} />
                <MetricCard label="Score" value={asNumber(teacher.performance_score).toFixed(1)} detail="profile performance" icon={<Star className="h-4 w-4" />} tone="text-blue-600" />
              </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-black text-slate-900">Growth Path</p>
              <div className="mt-5 space-y-4">
                {["Training lessons", "Assessment reports", "Promotion review", "Active teacher"].map((label, index) => {
                  const completed =
                    !isTraining ||
                    (index === 0 && assignedCount > 0) ||
                    (index === 1 && assessedCount > 0) ||
                    (index === 2 && statusLabel(academy?.academy_status || "").includes("ready")) ||
                    (index === 3 && statusLabel(academy?.academy_status || "") === "approved");
                  return (
                    <div key={label} className="flex gap-3">
                      <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black ${completed ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-400"}`}>
                        {index + 1}
                      </div>
                      <div>
                        <p className="text-sm font-black text-slate-900">{label}</p>
                        <p className="text-xs text-slate-500">{completed ? "In progress or completed" : "Waiting for previous step"}</p>
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
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {[
                  ["Teacher Academy", "Follow the assigned lesson sequence and prepare using the guidance notes."],
                  ["Lesson Reports", "Scores and remarks appear after each Academic Director assessment."],
                  ["Timetable", "Scheduled training sessions are controlled by the Academic Director."],
                ].map(([title, detail]) => (
                  <div key={title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <Bell className="h-4 w-4 text-blue-600" />
                    <p className="mt-3 text-sm font-black text-slate-900">{title}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-500">{detail}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        ) : null}
      </main>

      <nav
        className="fixed inset-x-0 bottom-0 z-50 border-t border-slate-200 bg-white/95 px-2 pt-2 shadow-[0_-10px_30px_rgba(15,23,42,0.10)] backdrop-blur-xl sm:hidden"
        style={{ paddingBottom: "max(0.5rem, var(--app-bottom-inset))" }}
        aria-label="Teacher mobile navigation"
      >
        <div className="mx-auto grid max-w-md grid-cols-4 gap-1">
          {teacherMobileTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = bottomNavActiveKey(activeTab) === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`flex min-h-[3.25rem] flex-col items-center justify-center gap-1 rounded-2xl px-2 text-[11px] font-black transition-colors ${
                  isActive ? "bg-blue-600 text-white shadow-sm" : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="h-4 w-4" />
                <span className="truncate">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
