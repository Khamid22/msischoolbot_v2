import { Suspense, lazy, useEffect, useState } from "react";
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
  LogOut,
  Phone,
  Megaphone,
  Menu,
  MessageSquare,
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
import {
  AdminMode,
  AdminPageProps,
  adminModeProfiles,
  adminModes,
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
const ParentPanel = lazy(() => import("@/roles/admin/panels/ParentPanel"));
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
  sales: supportPanels,
  hr: hrPanels,
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
    "student_resources",
    "student_rating",
    "student_aap",
    "student_ar",
    "student_office_hours",
  ]);
  const usesInternalFrameScroll = scrollableFrameTabs.has(tab);
  const [frameHeight, setFrameHeight] = useState(tab === "student_chat" ? 720 : 420);

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
        window.setTimeout(() => resizeFrame(frame), 250);
        window.setTimeout(() => resizeFrame(frame), 1000);
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

function activeTeacherRowsFor(state: any) {
  const teachers = rowsFrom(state.teachers?.length ? state.teachers : state.props?.adminTeachers);
  const selectedTeacherId = asNumber(state.teacherPreviewId);
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

function initialsForName(name: unknown) {
  const parts = asString(name).split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || "T"
  );
}

function teacherPreviewFallbackId(teachers: Array<Record<string, unknown>>, authLogin: unknown) {
  const login = normalizeMatch(authLogin);
  if (login) {
    const matchedTeacher = teachers.find((teacher) => {
      const name = normalizeMatch(teacher.full_name);
      return Boolean(name && (name === login || name.includes(login) || login.includes(name)));
    });
    const matchedTeacherId = asNumber(matchedTeacher?.id);
    if (matchedTeacherId) return matchedTeacherId;
  }
  return asNumber(teachers[0]?.id);
}

function resolveTeacherPreviewId(
  teachers: Array<Record<string, unknown>>,
  selectedTeacherId: number,
  authLogin: unknown,
) {
  if (!teachers.length) return 0;
  if (selectedTeacherId && teachers.some((teacher) => asNumber(teacher.id) === selectedTeacherId)) {
    return selectedTeacherId;
  }
  return teacherPreviewFallbackId(teachers, authLogin);
}

function TeacherPreviewSelector({
  teachers,
  selectedTeacherId,
  onSelect,
}: {
  teachers: Array<Record<string, unknown>>;
  selectedTeacherId: number;
  onSelect: (teacherId: number) => void;
}) {
  if (!teachers.length) return null;

  return (
    <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
      {teachers.map((teacher) => {
        const teacherId = asNumber(teacher.id);
        const isSelected = teacherId === selectedTeacherId;
        const assignedGroup = asString(teacher.assigned_group) || "No group";
        return (
          <button
            key={teacherId || asString(teacher.full_name)}
            type="button"
            onClick={() => onSelect(teacherId)}
            className={`flex min-w-[15rem] items-center gap-3 rounded-lg border px-3 py-2.5 text-left shadow-card transition-colors ${
              isSelected
                ? "border-primary bg-primary text-primary-foreground"
                : "border-foreground/10 bg-surface text-foreground hover:bg-muted"
            }`}
          >
            <span
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                isSelected ? "bg-primary-foreground/15 text-primary-foreground" : "bg-muted text-foreground"
              }`}
            >
              {initialsForName(teacher.full_name)}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-bold">
                {asString(teacher.full_name) || "Teacher"}
              </span>
              <span className={`block truncate text-xs ${isSelected ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                {assignedGroup}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function scopeTeacherState(state: any) {
  if (asString(state.adminMode).toLowerCase() !== "teacher") {
    return state;
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
  if (
    adminMode === "parent" &&
    ["overview", "announcements", "payments", "contact"].includes(panelState.activeTab)
  ) {
    return <ParentPanel state={panelState} />;
  }

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
      <div className="border-b border-white/10 px-4 py-4">
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
        <label className="mt-3 block">
          <span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Workspace
          </span>
          <select
            value={state.adminMode}
            onChange={(event) => state.switchAdminMode(event.target.value)}
            className="h-9 w-full rounded-lg border border-white/12 bg-white px-2 text-xs font-bold text-slate-900 outline-none focus:border-white/30"
            aria-label="Workspace mode"
          >
            {adminModes.map((mode) => (
              <option key={mode} value={mode}>
                {adminModeProfiles[mode].label}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-[11px] leading-4 text-slate-400">
            {activeAdminProfile.description}
          </span>
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
        <nav className="space-y-4" aria-label="Admin navigation">
          {groupTabsBySection(state.visibleTabs as Array<{ key: string; label: string }>).map((section) => (
            <div key={section.label} className="space-y-1">
              <p className="px-2 pb-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">
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
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-semibold transition-all active:scale-[0.98] duration-150 motion-reduce:active:scale-100 ${
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
          <form action={routes.logout} method="post" className="shrink-0">
            <input type="hidden" name="csrf_token" value={csrfToken || ""} />
            <button
              type="submit"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 hover:text-white"
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
  const allTeacherRows = rowsFrom(props.adminTeachers);
  const [teacherPreviewId, setTeacherPreviewId] = useState(() => {
    try {
      const stored = Number(window.localStorage.getItem("msi_teacher_preview_id") || 0);
      return Number.isFinite(stored) && stored > 0 ? stored : 0;
    } catch {
      return 0;
    }
  });
  const isTeacherWorkspace = asString(state.adminMode).toLowerCase() === "teacher";
  const selectedTeacherPreviewId = isTeacherWorkspace
    ? resolveTeacherPreviewId(allTeacherRows, teacherPreviewId, props.authLogin)
    : 0;
  const panelState = isTeacherWorkspace
    ? { ...state, teacherPreviewId: selectedTeacherPreviewId }
    : state;

  function selectTeacherPreview(teacherId: number) {
    setTeacherPreviewId(teacherId);
    try {
      if (teacherId > 0) {
        window.localStorage.setItem("msi_teacher_preview_id", String(teacherId));
      } else {
        window.localStorage.removeItem("msi_teacher_preview_id");
      }
    } catch {
    }
  }

  const activeTabLabel =
    state.visibleTabs.find((tab: { key: string; label: string }) => tab.key === state.activeTab)?.label ||
    tabs.find((tab) => tab.key === state.activeTab)?.label ||
    "Overview";

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
    <div className="app-min-height bg-background">
      <AdminSidebar state={state} csrfToken={props.csrfToken} />

      <header
        className="fixed inset-x-0 top-0 z-50 border-b border-foreground/5 bg-surface/95 backdrop-blur lg:hidden"
        style={{ paddingTop: "var(--app-top-inset)" }}
      >
        <div className="flex h-14 w-full items-center gap-3 px-3 sm:px-4 md:px-6">
          <button
            type="button"
            onClick={() => state.setMobileNavOpen((current: boolean) => !current)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-foreground hover:bg-muted lg:hidden"
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

          <form action={routes.logout} method="post" className="ml-auto shrink-0">
            <input type="hidden" name="csrf_token" value={props.csrfToken || ""} />
            <button
              type="submit"
              className="flex h-9 w-9 items-center justify-center rounded-lg text-destructive hover:bg-muted"
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
        className="flex app-min-height w-full flex-col px-3 pb-[calc(var(--app-bottom-inset)+1rem)] pt-[calc(var(--app-top-inset)+4.5rem)] sm:px-4 md:px-6 lg:ml-64 lg:w-[calc(100%-16rem)] lg:pt-4"
      >
        {props.authError ? <FormAlert kind="error">{props.authError}</FormAlert> : null}
        {props.adminNotice ? <FormAlert kind="notice">{props.adminNotice}</FormAlert> : null}

        {isTeacherWorkspace ? (
          <TeacherPreviewSelector
            teachers={allTeacherRows}
            selectedTeacherId={selectedTeacherPreviewId}
            onSelect={selectTeacherPreview}
          />
        ) : null}

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

        <div className="flex min-h-0 flex-1 flex-col">
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
