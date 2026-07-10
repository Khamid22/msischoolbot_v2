import { Suspense, lazy, useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  BookOpen,
  BookMarked,
  CalendarDays,
  CreditCard,
  GraduationCap,
  LayoutDashboard,
  Layers,
  KeyRound,
  LogOut,
  Phone,
  Megaphone,
  Menu,
  MessageSquare,
  School,
  TrendingUp,
  Trophy,
  User,
  UserPlus,
  UserRound,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { FormAlert } from "@/shared/ui/PortalCard";
import { withEmbedMode } from "@/shared/ui/AdminEmbedLayout";
import { routes } from "@/shared/lib/routes";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import {
  AdminMode,
  AdminPageProps,
  adminModeProfiles,
  asNumber,
  asString,
  groupTabsBySection,
  tabs,
} from "@/roles/admin/shared";
import { useAdminState } from "@/roles/admin/hooks/useAdminState";

const OverviewPanel = lazy(() => import("@/roles/admin/panels/OverviewPanel"));
const StudentsPanel = lazy(() => import("@/roles/admin/panels/StudentsPanel"));
const ParentsPanel = lazy(() => import("@/roles/admin/panels/ParentsPanel"));
const TeachersPanel = lazy(() => import("@/roles/admin/panels/TeachersPanel"));
const AcademicPanel = lazy(() => import("@/roles/admin/panels/AcademicPanel"));
const AnnouncementsPanel = lazy(() => import("@/roles/admin/panels/AnnouncementsPanel"));
const ResourcesPanel = lazy(() => import("@/roles/admin/panels/ResourcesPanel"));
const ChatPanel = lazy(() => import("@/roles/admin/panels/ChatPanel"));
const PaymentsPanel = lazy(() => import("@/roles/admin/panels/PaymentsPanel"));
const ComplaintsPanel = lazy(() => import("@/roles/admin/panels/ComplaintsPanel"));
const CareerGrowthPanel = lazy(() => import("@/roles/admin/panels/CareerGrowthPanel"));
const OfficeHoursPanel = lazy(() => import("@/roles/admin/panels/OfficeHoursPanel"));

// Role-mode panel maps. Each maps a tab key → a role-specific component; tabs not
// present fall back to the default admin panel below. Components live under
// roles/admin/modes/<role>/ and currently reuse the shared panels internally.
import { ceoPanels } from "@/roles/admin/modes/ceo";
import { supportPanels } from "@/roles/admin/modes/support";
import { hrPanels } from "@/roles/admin/modes/hr";
import type { ComponentType } from "react";

const modePanelsByAdminMode: Record<string, Record<string, ComponentType<{ state: any }>>> = {
  ceo: ceoPanels,
  customer_support: supportPanels,
  hr_manager: hrPanels,
};

type StudentActionTab =
  | "student_dashboard"
  | "student_profile"
  | "student_resources"
  | "student_chat"
  | "student_rating"
  | "student_aap"
  | "student_ar"
  | "student_office_hours";

const studentActionConfig: Record<
  StudentActionTab,
  {
    title: string;
    subtitle: string;
    icon: LucideIcon;
    href: (studentId: number, school: string) => string;
    accent: string;
  }
> = {
  student_dashboard: {
    title: "Academic Dashboard",
    subtitle: "Performance, attendance, progress, and subject summary.",
    icon: LayoutDashboard,
    href: (studentId, school) => routes.adminStudentDashboard(studentId, school),
    accent: "bg-slate-50 text-slate-700 border-slate-100",
  },
  student_profile: {
    title: "Profile",
    subtitle: "Student details and account profile.",
    icon: User,
    href: (studentId, school) => routes.adminStudentProfile(studentId) + `?school=${encodeURIComponent(school || "all")}`,
    accent: "bg-sky-50 text-sky-700 border-sky-100",
  },
  student_resources: {
    title: "Resources",
    subtitle: "Learning materials for the student.",
    icon: BookOpen,
    href: (studentId, school) => routes.adminStudentDashboardTarget(studentId, "resources", school),
    accent: "bg-emerald-50 text-emerald-700 border-emerald-100",
  },
  student_chat: {
    title: "Chat",
    subtitle: "Student communication room.",
    icon: MessageSquare,
    href: (studentId, school) => routes.adminStudentDashboardTarget(studentId, "chat", school),
    accent: "bg-violet-50 text-violet-700 border-violet-100",
  },
  student_rating: {
    title: "Rating",
    subtitle: "Class rating board and standing.",
    icon: Trophy,
    href: (studentId, school) => routes.adminStudentDashboardTarget(studentId, "rating", school),
    accent: "bg-amber-50 text-amber-700 border-amber-100",
  },
  student_aap: {
    title: "AAP",
    subtitle: "Academic achievement progress lessons.",
    icon: GraduationCap,
    href: (studentId, school) => routes.adminStudentDashboardTarget(studentId, "aap", school),
    accent: "bg-blue-50 text-blue-700 border-blue-100",
  },
  student_ar: {
    title: "AR",
    subtitle: "Attendance record lessons.",
    icon: Activity,
    href: (studentId, school) => routes.adminStudentDashboardTarget(studentId, "ar", school),
    accent: "bg-rose-50 text-rose-700 border-rose-100",
  },
  student_office_hours: {
    title: "Office Hours",
    subtitle: "Book and manage teacher office-hour sessions.",
    icon: CalendarDays,
    href: (studentId, school) => routes.adminStudentDashboardTarget(studentId, "office-hours", school),
    accent: "bg-indigo-50 text-indigo-700 border-indigo-100",
  },
};

function StudentActionPanel({ state, tab }: { state: any; tab: StudentActionTab }) {
  const config = studentActionConfig[tab];
  const Icon = config.icon;
  const students = Array.isArray(state.filteredStudents)
    ? (state.filteredStudents as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminStudents)
      ? (state.props.adminStudents as Array<Record<string, unknown>>)
      : [];
  const currentSchool = asString(state.currentSchool) || "all";
  const requestedStudentId = asNumber(state.activeStudentRowId);
  const student =
    students.find((row) => asNumber(row.id) === requestedStudentId) ||
    students[0];
  const studentId = asNumber(student?.id);
  const frameUrl = studentId ? withEmbedMode(config.href(studentId, currentSchool)) : "";
  const scrollableFrameTabs = new Set<StudentActionTab>([
    "student_dashboard",
    "student_profile",
    "student_resources",
    "student_chat",
    "student_rating",
    "student_aap",
    "student_ar",
    "student_office_hours",
  ]);
  const usesInternalFrameScroll = scrollableFrameTabs.has(tab);
  const [frameHeight, setFrameHeight] = useState(tab === "student_chat" ? 720 : 420);
  const frameResizeObserverRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    return () => {
      frameResizeObserverRef.current?.disconnect();
      frameResizeObserverRef.current = null;
    };
  }, [frameUrl]);

  function resizeFrame(frame: HTMLIFrameElement | null) {
    if (usesInternalFrameScroll) return;
    const doc = frame?.contentDocument;
    if (!doc) return;
    const rootChild = doc.getElementById("root")?.firstElementChild as HTMLElement | null;
    const measuredHeight = rootChild
      ? rootChild.getBoundingClientRect().height
      : Math.max(doc.documentElement.scrollHeight, doc.body?.scrollHeight || 0);
    const minimumHeight = tab === "student_chat" ? 640 : 0;
    const nextHeight = Math.max(minimumHeight, Math.ceil(measuredHeight) + 2);
    setFrameHeight(nextHeight);
  }

  function watchFrameResize(frame: HTMLIFrameElement | null) {
    frameResizeObserverRef.current?.disconnect();
    frameResizeObserverRef.current = null;
    if (usesInternalFrameScroll || typeof ResizeObserver === "undefined") return;

    const doc = frame?.contentDocument;
    if (!doc) return;

    const root = doc.getElementById("root");
    const target = root || doc.body || doc.documentElement;
    const observer = new ResizeObserver(() => resizeFrame(frame));
    observer.observe(target);
    if (doc.body && doc.body !== target) observer.observe(doc.body);
    frameResizeObserverRef.current = observer;
  }

  if (!student || !studentId) {
    return (
      <ChartCard
        title={config.title}
        subtitle={config.subtitle}
        icon={<Icon className="h-4 w-4 text-info" />}
      >
        <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-10 text-center">
          <p className="text-sm font-bold">No student dashboard is available yet.</p>
        </div>
      </ChartCard>
    );
  }

  return (
    <iframe
      key={frameUrl}
      src={frameUrl}
      title={`${config.title} - ${asString(student.full_name) || "Student"}`}
      className="block w-full bg-background"
      style={{ height: usesInternalFrameScroll ? "calc(var(--tg-app-height) - 1.5rem)" : `${frameHeight}px` }}
      scrolling={usesInternalFrameScroll ? "auto" : "no"}
      onLoad={(event) => {
        const frame = event.currentTarget;
        resizeFrame(frame);
        watchFrameResize(frame);
        window.setTimeout(() => resizeFrame(frame), 250);
        window.setTimeout(() => resizeFrame(frame), 1000);
        window.setTimeout(() => resizeFrame(frame), 2000);
      }}
    />
  );
}

function PanelFallback() {
  return (
    <div className="rounded-lg border border-foreground/10 bg-surface px-4 py-3 text-sm text-muted-foreground shadow-card">
      Loading panel...
    </div>
  );
}

function normalizeMatch(value: unknown) {
  return asString(value)
    .toLowerCase()
    .replace(/[^a-z0-9а-яё]+/gi, " ")
    .trim();
}

function rowsFrom(value: unknown) {
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}

type OverviewStatLine = {
  label: string;
  value: number;
};

type OverviewStatCard = {
  label: string;
  value: number;
  detail: string;
  breakdown: OverviewStatLine[];
};

function sumStatLines(rows: Array<Record<string, unknown>>, labelKey: string, valueKey: string): OverviewStatLine[] {
  const counts = new Map<string, number>();
  rows.forEach((row) => {
    const label = asString(row[labelKey]);
    if (!label) return;
    counts.set(label, (counts.get(label) || 0) + asNumber(row[valueKey]));
  });
  return Array.from(counts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => right.value - left.value);
}

function overviewStatCards(state: any): OverviewStatCard[] {
  const quickStats = state.quickStats || {};
  const subjectInfo = rowsFrom(state.subjectInfo);
  const teachers = rowsFrom(Array.isArray(state.teachers) ? state.teachers : state.props?.adminTeachers);
  const groups = rowsFrom(state.props?.adminAcademicGroups);

  const subjectByGroupName = new Map<string, string>();
  groups.forEach((group) => {
    const groupName = asString(group.name || group.group_name).toLowerCase();
    const subjectName = asString(group.subject_name);
    if (groupName && subjectName && !subjectByGroupName.has(groupName)) {
      subjectByGroupName.set(groupName, subjectName);
    }
  });
  const teacherCounts = new Map<string, number>();
  teachers.forEach((teacher) => {
    const subject = subjectByGroupName.get(asString(teacher.assigned_group).toLowerCase()) || "No subject yet";
    teacherCounts.set(subject, (teacherCounts.get(subject) || 0) + 1);
  });
  const teachersBySubject = Array.from(teacherCounts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => right.value - left.value);
  const studentsBySchool = rowsFrom(quickStats.school_counts)
    .map((row) => ({ label: asString(row.school_name), value: asNumber(row.count) }))
    .filter((line) => line.label);
  const studentsBySubject = rowsFrom(quickStats.subject_counts)
    .map((row) => ({ label: asString(row.subject_name || row.label), value: asNumber(row.count || row.value) }))
    .filter((line) => line.label);
  const groupsBySubject = rowsFrom(quickStats.group_counts)
    .map((row) => ({ label: asString(row.subject_name || row.label), value: asNumber(row.count || row.value) }))
    .filter((line) => line.label);
  const fallbackGroupsBySubject = sumStatLines(subjectInfo, "subject_name", "groups_count");
  const groupBreakdown = groupsBySubject.length ? groupsBySubject : fallbackGroupsBySubject;

  return [
    {
      label: "Students",
      value: asNumber(quickStats.total_students),
      detail: "enrolled students",
      breakdown: studentsBySubject.length ? studentsBySubject : sumStatLines(subjectInfo, "subject_name", "students_count"),
    },
    {
      label: "Teachers",
      value: asNumber(quickStats.total_teachers),
      detail: "active teachers",
      breakdown: teachersBySubject,
    },
    {
      label: "Schools",
      value: asNumber(quickStats.total_schools),
      detail: "students per school",
      breakdown: studentsBySchool,
    },
    {
      label: "Groups",
      value: asNumber(quickStats.total_groups) || groupBreakdown.reduce((sum, row) => sum + row.value, 0),
      detail: "groups per subject",
      breakdown: groupBreakdown,
    },
  ];
}

function overviewStatIcon(label: string) {
  if (label === "Students") return <Users className="h-4 w-4" />;
  if (label === "Teachers") return <GraduationCap className="h-4 w-4" />;
  if (label === "Schools") return <School className="h-4 w-4" />;
  return <BookOpen className="h-4 w-4" />;
}

function OverviewStatCards({ state }: { state: any }) {
  const cards = overviewStatCards(state);
  return (
    <div className="mb-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="group relative rounded-lg border border-foreground/8 bg-surface p-3 shadow-card">
          <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
            {overviewStatIcon(card.label)}
            <span className="min-w-0 break-words">{card.label}</span>
          </div>
          <p className="mt-2 text-xl font-black leading-none text-foreground">{card.value.toLocaleString()}</p>
          <p className="mt-1 text-xs text-muted-foreground">{card.detail}</p>
          {card.breakdown.length ? (
            <div className="pointer-events-none absolute left-2 right-2 top-[calc(100%-0.25rem)] z-40 rounded-lg border border-foreground/10 bg-surface/85 p-2.5 opacity-0 shadow-card-hover backdrop-blur-md transition-opacity duration-200 ease-out group-hover:opacity-100">
              {card.breakdown.map((line) => (
                <div key={line.label} className="flex items-center justify-between gap-3 py-0.5 text-xs">
                  <span className="min-w-0 truncate text-muted-foreground">{line.label}</span>
                  <span className="shrink-0 font-bold tabular-nums text-foreground">{line.value.toLocaleString()}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function activeTeacherRowsFor(state: any) {
  const teachers = rowsFrom(Array.isArray(state.teachers) ? state.teachers : state.props?.adminTeachers);
  const selectedKey = asString(state.teacherPreviewKey);
  const selectedTeacherId = selectedKey.startsWith("active:")
    ? asNumber(selectedKey.replace("active:", ""))
    : asNumber(state.teacherPreviewId);
  if (selectedTeacherId > 0) {
    return teachers.filter((teacher) => asNumber(teacher.id) === selectedTeacherId);
  }

  const login = normalizeMatch(state.props?.authLogin);
  if (!login) return [];
  return teachers.filter((teacher) => {
    const name = normalizeMatch(teacher.full_name);
    return Boolean(name && (name === login || name.includes(login) || login.includes(name)));
  });
}

function academyTeacherPreviewFor(state: any) {
  const selectedKey = asString(state.teacherPreviewKey);
  if (!selectedKey.startsWith("academy:")) return null;
  const academyTeacherId = asNumber(selectedKey.replace("academy:", ""));
  if (!academyTeacherId) return null;
  const teachers = rowsFrom(Array.isArray(state.academyTeachers) ? state.academyTeachers : state.props?.adminTeacherAcademy);
  return teachers.find((teacher) => asNumber(teacher.id) === academyTeacherId) || null;
}

function emptyTeacherScopedState(state: any) {
  const props = { ...(state.props || {}) };
  props.adminTeachers = [];
  props.adminStudents = [];
  props.adminAcademicGroups = [];
  props.adminAcademicEnrollments = [];
  props.adminAcademicSchedules = [];
  props.adminAcademicSessions = [];
  props.adminAcademicLessons = [];

  return {
    ...state,
    props,
    teachers: [],
    filteredStudents: [],
    teacherScopeMissing: true,
  };
}

function previewKeyFor(row: Record<string, unknown>, fallbackKind = "active") {
  const explicitKey = asString(row.__previewKey);
  if (explicitKey) return explicitKey;
  const kind = asString(row.__previewKind) || fallbackKind;
  return `${kind}:${asNumber(row.id)}`;
}

function teacherPreviewRows(
  activeTeachers: Array<Record<string, unknown>>,
  academyTeachers: Array<Record<string, unknown>>,
) {
  return [
    ...activeTeachers.map((teacher) => ({
      ...teacher,
      __previewKey: `active:${asNumber(teacher.id)}`,
      __previewKind: "active",
    })),
    ...academyTeachers
      .filter((teacher) => !["approved", "rejected"].includes(asString(teacher.academy_status)))
      .map((teacher) => ({
        ...teacher,
        __previewKey: `academy:${asNumber(teacher.id)}`,
        __previewKind: "academy",
      })),
  ];
}

function teacherPreviewFallbackKey(
  teachers: Array<Record<string, unknown>>,
  authLogin: unknown,
) {
  if (!teachers.length) return "";
  const login = normalizeMatch(authLogin);
  if (login) {
    const matchedTeacher = teachers.find((teacher) => {
      const name = normalizeMatch(teacher.full_name);
      return Boolean(name && (name === login || name.includes(login) || login.includes(name)));
    });
    const matchedKey = matchedTeacher ? previewKeyFor(matchedTeacher) : "";
    if (matchedKey) return matchedKey;
  }
  return previewKeyFor(teachers[0]);
}

function resolveTeacherPreviewKey(
  teachers: Array<Record<string, unknown>>,
  selectedTeacherKey: string,
  authLogin: unknown,
) {
  if (!teachers.length) return "";
  if (selectedTeacherKey && teachers.some((teacher) => previewKeyFor(teacher) === selectedTeacherKey)) {
    return selectedTeacherKey;
  }
  const migratedId = asNumber(selectedTeacherKey);
  if (migratedId && teachers.some((teacher) => previewKeyFor(teacher) === `active:${migratedId}`)) {
    return `active:${migratedId}`;
  }
  return teacherPreviewFallbackKey(teachers, authLogin);
}

function TeacherPreviewSelector({
  teachers,
  selectedTeacherKey,
  onSelect,
}: {
  teachers: Array<Record<string, unknown>>;
  selectedTeacherKey: string;
  onSelect: (teacherKey: string) => void;
}) {
  if (!teachers.length) return null;
  const selectedTeacher = teachers.find((teacher) => previewKeyFor(teacher) === selectedTeacherKey) || teachers[0];
  const selectedLogin = asString(selectedTeacher?.login);
  const selectedKind = asString(selectedTeacher?.__previewKind);
  const selectedStatus = selectedKind === "academy" ? "Academy teacher" : "Active teacher";

  return (
    <div className="mb-3 rounded-xl border border-foreground/8 bg-surface px-3 py-2 shadow-card animate-in fade-in slide-in-from-top-1 duration-200 motion-reduce:animate-none">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-[10rem] flex-1">
          <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">Teacher preview</p>
          <p className="truncate text-sm font-black text-foreground">{asString(selectedTeacher?.full_name) || "Teacher"}</p>
        </div>
        <select
          value={selectedTeacherKey}
          onChange={(event) => onSelect(event.target.value)}
          className="h-10 min-w-[13rem] rounded-lg border border-foreground/10 bg-background px-3 text-xs font-bold text-foreground outline-none transition focus:border-primary/50 focus:ring-2 focus:ring-primary/15"
          aria-label="Preview teacher account"
        >
          {teachers.map((teacher) => {
            const teacherKey = previewKeyFor(teacher);
            const kind = asString(teacher.__previewKind);
            const isAcademy = kind === "academy";
            const assignedGroup = isAcademy
              ? asString(teacher.subject) || "Teacher Academy"
              : asString(teacher.assigned_group) || "No group";
            return (
              <option key={teacherKey || asString(teacher.full_name)} value={teacherKey}>
                {asString(teacher.full_name) || "Teacher"} - {assignedGroup}
              </option>
            );
          })}
        </select>
        <span className={`inline-flex h-10 items-center rounded-lg px-3 text-[11px] font-black uppercase tracking-wide ${
          selectedKind === "academy" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
        }`}>
          {selectedStatus}
        </span>
        <div className="grid min-w-[13rem] grid-cols-2 overflow-hidden rounded-lg border border-foreground/8 bg-background text-[11px]">
          <div className="border-r border-foreground/8 px-3 py-1.5">
            <p className="font-black uppercase tracking-wide text-muted-foreground">Login</p>
            <p className="mt-0.5 truncate font-mono font-black text-foreground">{selectedLogin || "No account"}</p>
          </div>
          <div className="px-3 py-1.5">
            <p className="font-black uppercase tracking-wide text-muted-foreground">Default password</p>
            <p className="mt-0.5 truncate font-mono font-black text-foreground">{selectedLogin || "No account"}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function scopeTeacherState(state: any) {
  if (asString(state.adminMode).toLowerCase() !== "teacher") {
    return state;
  }
  const academyPreview = academyTeacherPreviewFor(state);
  if (academyPreview) {
    const props = { ...(state.props || {}) };
    props.adminTeachers = [];
    props.adminStudents = [];
    props.adminAcademicGroups = [];
    props.adminAcademicEnrollments = [];
    props.adminAcademicSchedules = [];
    props.adminAcademicSessions = [];
    props.adminAcademicLessons = [];
    return {
      ...state,
      props,
      teachers: [],
      filteredStudents: [],
      academyTeacherPreview: academyPreview,
    };
  }
  const teacherRows = activeTeacherRowsFor(state);
  if (!teacherRows.length) {
    return emptyTeacherScopedState(state);
  }

  const teacherIds = new Set(teacherRows.map((teacher) => asNumber(teacher.id)).filter(Boolean));
  const teacherNames = new Set(teacherRows.map((teacher) => normalizeMatch(teacher.full_name)).filter(Boolean));
  const groupNames = new Set(teacherRows.map((teacher) => normalizeMatch(teacher.assigned_group)).filter(Boolean));
  const props = { ...(state.props || {}) };
  const allGroups = rowsFrom(props.adminAcademicGroups);
  const allEnrollments = rowsFrom(props.adminAcademicEnrollments);
  const allSchedules = rowsFrom(props.adminAcademicSchedules);
  const allSessions = rowsFrom(props.adminAcademicSessions);
  const allLessons = rowsFrom(props.adminAcademicLessons);

  const matchesTeacher = (row: Record<string, unknown>) => {
    const teacherId = asNumber(row.teacher_id);
    const teacherName = normalizeMatch(row.teacher_name);
    return Boolean((teacherId && teacherIds.has(teacherId)) || (teacherName && teacherNames.has(teacherName)));
  };
  const matchesGroup = (row: Record<string, unknown>) => {
    const groupName = normalizeMatch(row.group_name || row.name || row.assigned_group);
    return Boolean(groupName && groupNames.has(groupName));
  };
  const filterByTeacherOrGroup = (rows: Array<Record<string, unknown>>) =>
    rows.filter((row) => matchesTeacher(row) || matchesGroup(row));
  const filterByGroup = (rows: Array<Record<string, unknown>>) => rows.filter(matchesGroup);

  [...allSchedules, ...allSessions].forEach((row) => {
    if (!matchesTeacher(row)) return;
    const groupName = normalizeMatch(row.group_name || row.name || row.assigned_group);
    if (groupName) groupNames.add(groupName);
  });

  const scopedEnrollments = groupNames.size ? filterByGroup(allEnrollments) : [];
  const enrollmentStudentIds = new Set(
    scopedEnrollments.map((enrollment) => asNumber(enrollment.public_dashboard_id)).filter(Boolean),
  );
  const enrollmentNames = new Set(
    scopedEnrollments.map((enrollment) => normalizeMatch(enrollment.full_name)).filter(Boolean),
  );
  const matchesStudent = (student: Record<string, unknown>) => {
    const studentId = asNumber(student.id);
    const studentName = normalizeMatch(student.full_name);
    const teacherName = normalizeMatch(student.teacher_name);
    return Boolean(
      (teacherName && teacherNames.has(teacherName)) ||
      (studentId && enrollmentStudentIds.has(studentId)) ||
      (studentName && enrollmentNames.has(studentName)),
    );
  };
  const scopedStudents = rowsFrom(state.filteredStudents).filter((student) => {
    return matchesStudent(student);
  });
  const scopedAdminStudents = rowsFrom(props.adminStudents).filter((student) => {
    return matchesStudent(student);
  });

  props.adminTeachers = teacherRows;
  props.adminStudents = scopedAdminStudents;
  props.adminAcademicEnrollments = scopedEnrollments;
  props.adminAcademicGroups = groupNames.size
    ? filterByGroup(allGroups)
    : [];
  props.adminAcademicSchedules = teacherIds.size || teacherNames.size || groupNames.size
    ? filterByTeacherOrGroup(allSchedules)
    : [];
  props.adminAcademicSessions = teacherIds.size || teacherNames.size || groupNames.size
    ? filterByTeacherOrGroup(allSessions)
    : [];
  props.adminAcademicLessons = groupNames.size
    ? filterByGroup(allLessons)
    : [];

  return {
    ...state,
    props,
    teachers: teacherRows,
    filteredStudents: scopedStudents,
  };
}

function ActivePanel({ state }: { state: any }) {
  const panelState = scopeTeacherState(state);
  const adminMode = asString(panelState.adminMode).toLowerCase();

  // Role modes (CEO / Customer Support / HR) render their own components for the
  // tabs they specialize. Anything not overridden falls through to the default
  // admin panels below, so Admin / Owner behavior is unchanged.
  const ModeComponent = modePanelsByAdminMode[adminMode]?.[panelState.activeTab];
  if (ModeComponent) {
    return <ModeComponent state={panelState} />;
  }

  switch (panelState.activeTab) {
    case "overview":
      return <OverviewPanel state={panelState} />;
    case "students":
      return <StudentsPanel state={panelState} />;
    case "parents":
      return <ParentsPanel state={panelState} />;
    case "teachers":
      return <TeachersPanel state={panelState} />;
    case "subjects":
      return <AcademicPanel state={panelState} kind="subjects" />;
    case "groups":
      return <AcademicPanel state={panelState} kind="groups" />;
    case "schedule":
      return <AcademicPanel state={panelState} kind="schedule" />;
    case "curriculum":
      return <AcademicPanel state={panelState} kind="subjects" />;
    case "gradebook":
      return <AcademicPanel state={panelState} kind="groups" />;
    case "office_hours":
      return <OfficeHoursPanel state={panelState} />;
    case "announcements":
      return <AnnouncementsPanel state={panelState} />;
    case "resources":
      return <ResourcesPanel state={panelState} />;
    case "payments":
      return <PaymentsPanel state={panelState} />;
    case "complaints":
      return <ComplaintsPanel state={panelState} />;
    case "career_growth":
      return <CareerGrowthPanel state={panelState} />;
    case "chat":
      return <ChatPanel state={panelState} />;
    case "student_dashboard":
    case "student_profile":
    case "student_resources":
    case "student_chat":
    case "student_rating":
    case "student_aap":
    case "student_ar":
    case "student_office_hours":
      return <StudentActionPanel state={panelState} tab={panelState.activeTab} />;
    default:
      return <OverviewPanel state={panelState} />;
  }
}

function isStudentActionTab(tab: string) {
  return tab.startsWith("student_");
}

const tabIcons: Record<string, LucideIcon> = {
  overview: LayoutDashboard,
  students: Users,
  parents: UserRound,
  teachers: GraduationCap,
  subjects: BookMarked,
  groups: Layers,
  schedule: CalendarDays,
  announcements: Megaphone,
  resources: BookOpen,
  payments: CreditCard,
  complaints: AlertCircle,
  career_growth: TrendingUp,
  candidates: UserPlus,
  contact: Phone,
  chat: MessageSquare,
  student_dashboard: LayoutDashboard,
  student_profile: User,
  student_resources: BookOpen,
  student_chat: MessageSquare,
  student_rating: Trophy,
  student_aap: GraduationCap,
  student_ar: Activity,
  student_office_hours: CalendarDays,
  curriculum: BookMarked,
  gradebook: Layers,
  office_hours: CalendarDays,
};

function AdminSidebar({
  state,
  csrfToken,
  compact = false,
  onClose,
}: {
  state: any;
  csrfToken?: string;
  compact?: boolean;
  onClose?: () => void;
}) {
  const activeAdminMode: AdminMode =
    state.adminMode && adminModeProfiles[state.adminMode as AdminMode]
      ? (state.adminMode as AdminMode)
      : "admin";
  const activeAdminProfile = adminModeProfiles[activeAdminMode];

  return (
    <aside
      className={
        compact
          ? "flex h-full flex-col bg-sidebar text-sidebar-foreground"
          : "fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:flex"
      }
    >
      <div className="border-b border-white/10 px-3 py-3">
        <div className="flex items-start gap-2">
          <button
            type="button"
            onClick={() => state.switchAdminTab("overview")}
            className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg text-left"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/12 font-bold text-white ring-1 ring-white/10">
              M
            </div>
            <div className="min-w-0 leading-tight">
              <span className="block truncate text-sm font-semibold text-white">MSI School</span>
              <span className="block truncate text-xs text-slate-300">Admin Console</span>
            </div>
          </button>
          {compact ? (
            <button
              type="button"
              onClick={onClose}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-300 hover:bg-white/10 hover:text-white"
              aria-label="Close navigation"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-3">
        <nav className="space-y-3" aria-label="Admin navigation">
          {groupTabsBySection(state.visibleTabs as Array<{ key: string; label: string }>).map((section) => (
            <div key={section.label} className="space-y-1">
              <p className="px-2.5 pb-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {section.label}
              </p>
              {section.tabs.map((tab) => {
                const Icon = tabIcons[tab.key] || LayoutDashboard;
                const isActive = state.activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => state.switchAdminTab(tab.key)}
                    aria-current={isActive ? "page" : undefined}
                    className={`flex min-h-11 w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-semibold transition-all active:scale-[0.98] duration-150 motion-reduce:active:scale-100 ${
                      isActive
                        ? "bg-sidebar-primary text-sidebar-primary-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-900">
            KA
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-sm font-medium text-white">Khamid A.</span>
            <span className="block truncate text-xs text-slate-400">
              {activeAdminProfile.label} mode
            </span>
          </div>
          <a
            href={routes.accountSecurity}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
            aria-label="Account security"
            title="Account security"
          >
            <KeyRound className="h-4 w-4" />
          </a>
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={csrfToken || ""} />
            <button
              type="submit"
              className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
              aria-label="Exit"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </aside>
  );
}

export default function AdminPage(props: AdminPageProps) {
  const state = useAdminState(props);
  useDismissibleLayer({
    enabled: Boolean(state.editingResource),
    onDismiss: () => {
      state.setEditingResource(null);
      state.setEditError("");
    },
    dismissOnOutsidePointer: false,
  });
  useDismissibleLayer({
    enabled: Boolean(state.mobileNavOpen),
    onDismiss: () => state.setMobileNavOpen(false),
    dismissOnOutsidePointer: false,
  });
  const allTeacherRows = rowsFrom(Array.isArray(state.teachers) ? state.teachers : state.props.adminTeachers);
  const allAcademyTeacherRows = rowsFrom(Array.isArray(state.academyTeachers) ? state.academyTeachers : state.props.adminTeacherAcademy);
  const allTeacherPreviewRows = teacherPreviewRows(allTeacherRows, allAcademyTeacherRows);
  const [teacherPreviewKey, setTeacherPreviewKey] = useState(() => {
    try {
      const storedKey = asString(window.localStorage.getItem("msi_teacher_preview_key"));
      if (storedKey) return storedKey;
      const storedId = Number(window.localStorage.getItem("msi_teacher_preview_id") || 0);
      return Number.isFinite(storedId) && storedId > 0 ? `active:${storedId}` : "";
    } catch {
      return "";
    }
  });
  const isTeacherWorkspace = asString(state.adminMode).toLowerCase() === "teacher";
  const selectedTeacherPreviewKey = isTeacherWorkspace
    ? resolveTeacherPreviewKey(allTeacherPreviewRows, teacherPreviewKey, props.authLogin)
    : "";
  const panelState = {
    ...state,
    teacherPreviewKey: isTeacherWorkspace ? selectedTeacherPreviewKey : teacherPreviewKey,
    selectTeacherPreview,
  };

  function selectTeacherPreview(nextTeacherKey: string) {
    setTeacherPreviewKey(nextTeacherKey);
    try {
      if (nextTeacherKey) {
        window.localStorage.setItem("msi_teacher_preview_key", nextTeacherKey);
        window.localStorage.removeItem("msi_teacher_preview_id");
      } else {
        window.localStorage.removeItem("msi_teacher_preview_key");
        window.localStorage.removeItem("msi_teacher_preview_id");
      }
    } catch {
    }
  }

  const activeTabLabel =
    state.visibleTabs.find((tab: { key: string; label: string }) => tab.key === state.activeTab)?.label ||
    tabs.find((tab) => tab.key === state.activeTab)?.label ||
    "Overview";
  const showOverviewStatCards =
    state.activeTab === "overview" &&
    ["admin", "ceo"].includes(asString(state.adminMode).toLowerCase());

  useEffect(() => {
    if (!state.mobileNavOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        state.setMobileNavOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [state.mobileNavOpen, state.setMobileNavOpen]);

  return (
    <div className="app-min-height bg-background lg:app-height lg:overflow-hidden">
      <AdminSidebar state={state} csrfToken={props.csrfToken} />

      <header
        className="fixed inset-x-0 top-0 z-50 border-b border-foreground/5 bg-surface/95 backdrop-blur lg:hidden"
        style={{ paddingTop: "var(--app-top-inset)" }}
      >
        <div className="flex h-14 w-full items-center gap-3 px-3 sm:px-4 md:px-6">
          <button
            type="button"
            onClick={() => state.setMobileNavOpen((current: boolean) => !current)}
            className="flex h-11 w-11 items-center justify-center rounded-lg text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 lg:hidden"
            aria-label={state.mobileNavOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={state.mobileNavOpen}
            aria-controls="admin-mobile-nav"
          >
            {state.mobileNavOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>

          <div className="min-w-0 flex-1 lg:hidden">
            <p className="truncate text-sm font-bold text-foreground">{activeTabLabel}</p>
            <p className="truncate text-[11px] text-muted-foreground">Admin Console</p>
          </div>

          <a
            href={routes.accountSecurity}
            className="ml-auto flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            aria-label="Account security"
          >
            <KeyRound className="h-4 w-4" />
          </a>
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <button
              type="submit"
              className="flex h-11 w-11 items-center justify-center rounded-lg text-destructive hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/35"
              aria-label="Exit"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </form>
        </div>
      </header>

      {state.mobileNavOpen ? (
        <div
          id="admin-mobile-nav"
          className="fixed inset-0 z-[60] bg-foreground/45 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Admin navigation"
        >
          <button
            type="button"
            className="absolute inset-0 h-full w-full cursor-default"
            onClick={() => state.setMobileNavOpen(false)}
            aria-label="Close navigation"
          />
          <div
            className="relative h-full w-[min(20rem,86vw)] max-w-full shadow-card-hover animate-in slide-in-from-left duration-200 motion-reduce:animate-none"
            style={{
              paddingTop: "var(--app-top-inset)",
              paddingBottom: "var(--app-bottom-inset)",
              paddingLeft: "var(--app-left-inset)",
            }}
          >
            <AdminSidebar
              state={state}
              csrfToken={props.csrfToken}
              compact
              onClose={() => state.setMobileNavOpen(false)}
            />
          </div>
        </div>
      ) : null}

      <main
        className="flex app-min-height w-full flex-col px-2.5 pb-[calc(var(--app-bottom-inset)+0.75rem)] pt-[calc(var(--app-top-inset)+4rem)] sm:px-3 md:px-4 lg:ml-64 lg:app-height lg:w-[calc(100%-16rem)] lg:min-h-0 lg:overflow-hidden lg:pt-3"
      >
        {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}
        {props.adminNotice ? <FormAlert kind="notice">{props.adminNotice}</FormAlert> : null}

        {isTeacherWorkspace ? (
          <TeacherPreviewSelector
            teachers={allTeacherPreviewRows}
            selectedTeacherKey={selectedTeacherPreviewKey}
            onSelect={selectTeacherPreview}
          />
        ) : null}

        {showOverviewStatCards ? <OverviewStatCards state={state} /> : null}

        {state.resourceUploadState.active && state.activeTab !== "resources" ? (
          <div className="mb-4 rounded-lg border border-foreground/10 bg-surface px-4 py-3 shadow-card">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className={`text-xs font-semibold uppercase tracking-wide ${state.resourceUploadState.error ? "text-destructive" : "text-muted-foreground"}`}>
                  {state.resourceUploadState.message}
                </p>
              </div>
              <button
                type="button"
                onClick={() => state.switchAdminTab("resources")}
                className="shrink-0 rounded-lg bg-muted px-3 py-1.5 text-[11px] font-bold text-foreground hover:bg-foreground/10"
              >
                Open Upload
              </button>
            </div>
            <div
              className="overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(state.resourceUploadState.percent)}
            >
              <div
                className={`h-2 rounded-full transition-[width] duration-200 ${state.resourceUploadState.error ? "bg-destructive" : "bg-primary"}`}
                style={{
                  width: `${Math.max(0, Math.min(100, state.resourceUploadState.percent))}%`,
                }}
              />
            </div>
          </div>
        ) : null}

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <Suspense fallback={<PanelFallback />}>
            <ActivePanel state={panelState} />
          </Suspense>
        </div>
      </main>

      {state.editingResource ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
          onClick={() => {
            state.setEditingResource(null);
            state.setEditError("");
          }}
        >
          <div
            className="flex max-h-[88dvh] w-full max-w-md flex-col overflow-hidden rounded-2xl bg-surface shadow-card-hover"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex shrink-0 items-center justify-between border-b border-foreground/5 px-5 py-3">
              <h3 className="text-sm font-bold">Edit Resource</h3>
              <button
                type="button"
                onClick={() => {
                  state.setEditingResource(null);
                  state.setEditError("");
                }}
                className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="space-y-3 px-5 py-4">
                {state.editError ? (
                  <p className="text-xs font-semibold text-destructive">{state.editError}</p>
                ) : null}

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Title</span>
                  <input
                    type="text"
                    value={state.editingResource.title}
                    onChange={(e) =>
                      state.setEditingResource((prev: any) =>
                        prev ? { ...prev, title: e.target.value } : null
                      )
                    }
                    maxLength={180}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</span>
                  <textarea
                    value={state.editingResource.description}
                    onChange={(e) =>
                      state.setEditingResource((prev: any) =>
                        prev ? { ...prev, description: e.target.value } : null
                      )
                    }
                    rows={3}
                    maxLength={2000}
                    className="w-full resize-none rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30"
                  />
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">Resource Type</span>
                  <select
                    value={String(state.editingResource.resourceTypeId)}
                    onChange={(e) =>
                      state.setEditingResource((prev: any) =>
                        prev ? { ...prev, resourceTypeId: Number(e.target.value) } : null
                      )
                    }
                    disabled={state.editSaving}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none focus:border-foreground/30 disabled:opacity-50"
                  >
                    {state.activeResourceTypes.map((typeRow: Record<string, unknown>) => (
                      <option key={asNumber(typeRow.id)} value={asNumber(typeRow.id)}>
                        {asString(typeRow.name)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {state.editingResource.resourceFileKind === "video" ? "Swap Video" : "Replace File"}
                    <span className="ml-1 font-normal normal-case text-muted-foreground/60">
                      (optional — leave empty to keep current)
                    </span>
                  </span>
                  <input
                    ref={state.editResourceFileRef}
                    type="file"
                    name="resource_file"
                    accept={
                      state.editingResource.resourceFileKind === "video"
                        ? "video/mp4,video/quicktime,video/x-m4v"
                        : undefined
                    }
                    disabled={state.editSaving}
                    className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                  />
                </label>

                {state.editingResource.resourceFileKind === "video" ? (
                  <label className="block">
                    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      {state.editingResource.thumbnailUrl ? "Swap Thumbnail" : "Add Thumbnail"}
                      <span className="ml-1 font-normal normal-case text-muted-foreground/60">
                        (optional)
                      </span>
                    </span>
                    {state.editingResource.thumbnailUrl ? (
                      <img
                        src={state.editingResource.thumbnailUrl}
                        alt="Current thumbnail"
                        className="mb-2 h-20 w-auto rounded-lg object-cover"
                      />
                    ) : null}
                    <input
                      ref={state.editThumbnailFileRef}
                      type="file"
                      name="thumbnail_file"
                      accept="image/jpeg,image/png,image/webp"
                      disabled={state.editSaving}
                      className="w-full rounded-xl border-2 border-foreground/10 bg-background px-4 py-2.5 text-sm outline-none disabled:opacity-50"
                    />
                  </label>
                ) : null}
              </div>
            </div>

            <div className="flex shrink-0 gap-2 border-t border-foreground/5 px-5 py-3">
              <button
                type="button"
                disabled={state.editSaving}
                onClick={state.saveEditResource}
                className="rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-50"
              >
                {state.editSaving ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => {
                  state.setEditingResource(null);
                  state.setEditError("");
                }}
                className="rounded-xl bg-muted px-5 py-2.5 text-sm font-bold text-muted-foreground hover:bg-foreground/10"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
