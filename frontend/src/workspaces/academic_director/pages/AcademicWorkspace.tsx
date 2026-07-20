import { Suspense, lazy, useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { AcademicDirectorPageShell, type AcademicDirectorNavKey } from "@/workspaces/academic_shared/AcademicDirectorShell";
import type { AcademicPanelKind } from "@/shared/lib/workspace";
import { PageHeader } from "@/shared/ui/PageHeader";
import { routes } from "@/shared/lib/routes";

const AcademicPanel = lazy(() => import("@/features/academics/AcademicPanel"));

type AcademicWorkspaceKind = "groups" | "subjects" | "timetable";

type AcademicWorkspaceProps = {
  authLogin?: string;
  authRole?: string;
  csrfToken?: string;
  workspace?: AcademicWorkspaceKind;
  warning?: string;
  managementMode?: string;
  managementSchool?: string;
  academicManagementSchools?: Array<Record<string, unknown>>;
  academicManagementSubjects?: Array<Record<string, unknown>>;
  academicManagementGroups?: Array<Record<string, unknown>>;
  academicManagementEnrollments?: Array<Record<string, unknown>>;
  academicManagementLessons?: Array<Record<string, unknown>>;
  academicManagementSchedules?: Array<Record<string, unknown>>;
  academicManagementSessions?: Array<Record<string, unknown>>;
  academicManagementCurriculumPrograms?: Array<Record<string, unknown>>;
  academicManagementCurriculumItems?: Array<Record<string, unknown>>;
  academicManagementEnrollmentSummary?: Record<string, unknown>;
  academicManagementContextMode?: "summary" | "full";
};

const workspaceMeta: Record<AcademicWorkspaceKind, { active: AcademicDirectorNavKey; kind: AcademicPanelKind; title: string; subtitle: string }> = {
  groups: {
    active: "groups",
    kind: "groups",
    title: "Groups",
    subtitle: "Manage academic groups, enrollment, gradebook records, and group progress.",
  },
  subjects: {
    active: "subjects",
    kind: "subjects",
    title: "Subjects",
    subtitle: "Review subject programs, schemes of work, lessons, and exams.",
  },
  timetable: {
    active: "timetable",
    kind: "schedule",
    title: "Academic Timetable",
    subtitle: "Schedule and review group lessons across the academic program.",
  },
};

const academicDirectorAcademicRoutes = {
  academicManagementSchoolCreateApi: routes.academicDirectorAcademicSchoolCreate,
  academicManagementGroupCreateApi: routes.academicDirectorAcademicGroupCreate,
  academicManagementContextApi: routes.academicDirectorAcademicContextApi,
  academicManagementGroupsApi: routes.academicDirectorAcademicGroupsApi,
  academicManagementProgramsApi: routes.academicDirectorAcademicProgramsApi,
  academicManagementProgramItemsApi: routes.academicDirectorAcademicProgramItemsApi,
  academicManagementTimetableApi: routes.academicDirectorAcademicTimetableApi,
  academicManagementGroupTimetableApi: routes.academicDirectorAcademicGroupTimetableApi,
  academicManagementCalendarClosuresApi: routes.academicDirectorAcademicCalendarClosuresApi,
  academicManagementCalendarClosurePreview: routes.academicDirectorAcademicCalendarClosurePreview,
  academicManagementCalendarClosureCreate: routes.academicDirectorAcademicCalendarClosureCreate,
  academicManagementCalendarClosureUnlock: routes.academicDirectorAcademicCalendarClosureUnlock,
  academicManagementGroupApi: routes.academicDirectorAcademicGroupApi,
  academicManagementGroupSummaryApi: routes.academicDirectorAcademicGroupSummaryApi,
  academicManagementScheduleCreate: routes.academicDirectorAcademicScheduleCreate,
  academicManagementGroupSchedule: routes.academicDirectorAcademicGroupSchedule,
  academicManagementGroupStudents: routes.academicDirectorAcademicGroupStudents,
  academicManagementGradebookApi: routes.academicDirectorAcademicGradebookApi,
  academicManagementGradebookTrendsApi: routes.academicDirectorAcademicGradebookTrendsApi,
  academicManagementAttendanceApi: routes.academicDirectorAcademicAttendanceApi,
  academicManagementHomeworkApi: routes.academicDirectorAcademicHomeworkApi,
  academicManagementExamApi: routes.academicDirectorAcademicExamApi,
  academicManagementLessonApi: routes.academicDirectorAcademicLessonApi,
  academicManagementLessonCancelApi: routes.academicDirectorAcademicLessonCancelApi,
  academicManagementLessonRecoverApi: routes.academicDirectorAcademicLessonRecoverApi,
  academicManagementEnrollmentStatusApi: routes.academicDirectorAcademicEnrollmentStatusApi,
  academicManagementEnrollmentGroupApi: routes.academicDirectorAcademicEnrollmentGroupApi,
};

export default function AcademicDirectorAcademicWorkspace(props: AcademicWorkspaceProps) {
  const workspace = props.workspace && workspaceMeta[props.workspace] ? props.workspace : "groups";
  const meta = workspaceMeta[workspace];
  const panelState = useMemo(
    () => ({
      managementMode: "academic_director",
      currentSchool: props.managementSchool || "all",
      academicRoutes: academicDirectorAcademicRoutes,
      props: {
        ...props,
        authRole: props.authRole || "academic_director",
        managementMode: "academic_director",
        managementSchool: props.managementSchool || "all",
      },
    }),
    [props],
  );

  return (
    <AcademicDirectorPageShell
      authLogin={props.authLogin}
      csrfToken={props.csrfToken}
      active={meta.active}
      sectionClassName="gap-4"
    >
      {workspace !== "groups" ? (
        <PageHeader
          title={meta.title}
          subtitle={meta.subtitle}
          badge={
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-black uppercase tracking-wide text-primary">
              Academic Director
            </span>
          }
        />
      ) : null}

      {props.warning ? (
        <section className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <p className="text-sm font-semibold leading-6">{props.warning}</p>
        </section>
      ) : null}

      <Suspense
        fallback={
          <section className="rounded-2xl border border-border bg-surface p-5 text-sm font-bold text-muted-foreground shadow-card">
            Loading {meta.title.toLowerCase()}...
          </section>
        }
      >
        <AcademicPanel state={panelState} kind={meta.kind} />
      </Suspense>
    </AcademicDirectorPageShell>
  );
}
