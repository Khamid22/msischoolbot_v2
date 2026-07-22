import { Suspense, lazy, useMemo, useState } from "react";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { PageHeader } from "@/shared/ui/PageHeader";
import { HeadOfDepartmentPageShell } from "@/workspaces/academic_shared/AcademicDirectorShell";
import { asString } from "@/shared/lib/workspace";

const TeacherAcademyPanel = lazy(() =>
  import("@/features/teacher-academy/TeacherAcademyPanel").then((module) => ({
    default: module.TeacherAcademyPanel,
  })),
);

type HeadOfDepartmentAcademyProps = {
  authLogin?: string;
  authRole?: string;
  csrfToken?: string;
  managementMode?: string;
  managementSchool?: string;
  managementTeachers?: Array<Record<string, unknown>>;
  managementAcademyTeachers?: Array<Record<string, unknown>>;
  managementGroupOptions?: Array<Record<string, unknown>>;
  academicManagementSubjects?: Array<Record<string, unknown>>;
  academicManagementCurriculumPrograms?: Array<Record<string, unknown>>;
  academicManagementCurriculumItems?: Array<Record<string, unknown>>;
};

function normalizeGroupOptions(groups: Array<Record<string, unknown>>) {
  return groups
    .map((group) => ({
      name: asString(group.name || group.group_name || group.label),
    }))
    .filter((group) => group.name);
}

export default function HeadOfDepartmentTeacherAcademyPage(props: HeadOfDepartmentAcademyProps) {
  const [teachers, setTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.managementTeachers) ? props.managementTeachers : [],
  );
  const [academyTeachers, setAcademyTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.managementAcademyTeachers) ? props.managementAcademyTeachers : [],
  );
  const { toast, showToast, clearToast } = useFloatingToast();

  const panelState = useMemo(
    () => ({
      managementMode: "head_of_department",
      currentSchool: props.managementSchool || "all",
      teachers,
      setTeachers,
      academyTeachers,
      setAcademyTeachers,
      filteredGroupOptions: normalizeGroupOptions(
        Array.isArray(props.managementGroupOptions) ? props.managementGroupOptions : [],
      ),
      props: {
        ...props,
        managementMode: "head_of_department",
        authRole: props.authRole || "head_of_department",
        managementTeachers: teachers,
        managementAcademyTeachers: academyTeachers,
      },
    }),
    [academyTeachers, props, teachers],
  );

  return (
    <HeadOfDepartmentPageShell
      authLogin={props.authLogin}
      csrfToken={props.csrfToken}
      active="academy"
      sectionClassName="gap-4"
    >
      <PageHeader
        title="Teacher Academy"
        subtitle="Schedule lessons, review assessments, and support academy teachers within your subject scope."
        badge={
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[0.6875rem] font-black uppercase tracking-wide text-primary">
            Head of Departments
          </span>
        }
      />

      <Suspense
        fallback={
          <section className="rounded-xl border border-border bg-surface p-5 text-sm font-bold text-muted-foreground shadow-card">
            Loading Teacher Academy...
          </section>
        }
      >
        <TeacherAcademyPanel
          state={panelState}
          academyTeachers={academyTeachers}
          onAcademyChange={setAcademyTeachers}
          onTeachersChange={setTeachers}
          showToast={showToast}
        />
      </Suspense>

      <FloatingToast toast={toast} onClose={clearToast} />
    </HeadOfDepartmentPageShell>
  );
}
