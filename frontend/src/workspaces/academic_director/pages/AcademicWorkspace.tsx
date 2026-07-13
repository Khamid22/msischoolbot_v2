import { Suspense, lazy, useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { AcademicDirectorPageShell, type AcademicDirectorNavKey } from "@/features/academic_workspace/AcademicDirectorShell";
import type { AdminTab } from "@/features/managementTypes";
import { PageHeader } from "@/shared/ui/PageHeader";
import { routes } from "@/shared/lib/routes";

const AcademicPanel = lazy(() => import("@/features/management/AcademicPanel"));

type AcademicWorkspaceKind = "groups" | "subjects" | "timetable";

type AcademicWorkspaceProps = {
  authLogin?: string;
  authRole?: string;
  csrfToken?: string;
  workspace?: AcademicWorkspaceKind;
  warning?: string;
  adminMode?: string;
  adminSchool?: string;
  adminAcademicSchools?: Array<Record<string, unknown>>;
  adminAcademicSubjects?: Array<Record<string, unknown>>;
  adminAcademicGroups?: Array<Record<string, unknown>>;
  adminAcademicEnrollments?: Array<Record<string, unknown>>;
  adminAcademicLessons?: Array<Record<string, unknown>>;
  adminAcademicSchedules?: Array<Record<string, unknown>>;
  adminAcademicSessions?: Array<Record<string, unknown>>;
  adminAcademicCurriculumPrograms?: Array<Record<string, unknown>>;
  adminAcademicCurriculumItems?: Array<Record<string, unknown>>;
  adminAcademicEnrollmentSummary?: Record<string, unknown>;
  adminAcademicContextMode?: "summary" | "full";
};

const workspaceMeta: Record<AcademicWorkspaceKind, { active: AcademicDirectorNavKey; kind: AdminTab; title: string; subtitle: string }> = {
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
  adminAcademicSchoolCreateApi: routes.academicDirectorAcademicSchoolCreate,
  adminAcademicGroupCreateApi: routes.academicDirectorAcademicGroupCreate,
  adminAcademicContextApi: routes.academicDirectorAcademicContextApi,
  adminAcademicGroupsApi: routes.academicDirectorAcademicGroupsApi,
  adminAcademicProgramsApi: routes.academicDirectorAcademicProgramsApi,
  adminAcademicProgramItemsApi: routes.academicDirectorAcademicProgramItemsApi,
  adminAcademicTimetableApi: routes.academicDirectorAcademicTimetableApi,
  adminAcademicGroupApi: routes.academicDirectorAcademicGroupApi,
  adminAcademicGroupSummaryApi: routes.academicDirectorAcademicGroupSummaryApi,
  adminAcademicScheduleCreate: routes.academicDirectorAcademicScheduleCreate,
  adminAcademicGroupSchedule: routes.academicDirectorAcademicGroupSchedule,
  adminAcademicGroupStudents: routes.academicDirectorAcademicGroupStudents,
  adminAcademicGradebookApi: routes.academicDirectorAcademicGradebookApi,
  adminAcademicAttendanceApi: routes.academicDirectorAcademicAttendanceApi,
  adminAcademicHomeworkApi: routes.academicDirectorAcademicHomeworkApi,
  adminAcademicExamApi: routes.academicDirectorAcademicExamApi,
  adminAcademicLessonApi: routes.academicDirectorAcademicLessonApi,
  adminAcademicLessonCancelApi: routes.academicDirectorAcademicLessonCancelApi,
  adminAcademicLessonRecoverApi: routes.academicDirectorAcademicLessonRecoverApi,
  adminAcademicEnrollmentStatusApi: routes.academicDirectorAcademicEnrollmentStatusApi,
  adminAcademicEnrollmentGroupApi: routes.academicDirectorAcademicEnrollmentGroupApi,
};

export default function AcademicDirectorAcademicWorkspace(props: AcademicWorkspaceProps) {
  const workspace = props.workspace && workspaceMeta[props.workspace] ? props.workspace : "groups";
  const meta = workspaceMeta[workspace];
  const panelState = useMemo(
    () => ({
      adminMode: "academic_director",
      currentSchool: props.adminSchool || "all",
      academicRoutes: academicDirectorAcademicRoutes,
      props: {
        ...props,
        authRole: props.authRole || "academic_director",
        adminMode: "academic_director",
        adminSchool: props.adminSchool || "all",
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
      <PageHeader
        title={meta.title}
        subtitle={meta.subtitle}
        badge={
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-black uppercase tracking-wide text-primary">
            Academic Director
          </span>
        }
      />

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
