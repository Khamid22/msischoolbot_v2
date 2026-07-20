import { Suspense, lazy, useMemo, useState } from "react";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { PageHeader } from "@/shared/ui/PageHeader";
import { AcademicDirectorPageShell } from "@/workspaces/academic_shared/AcademicDirectorShell";
import { asString } from "@/shared/lib/workspace";

const TeacherAcademyPanel = lazy(() =>
  import("@/features/teacher-academy/TeacherAcademyPanel").then((module) => ({
    default: module.TeacherAcademyPanel,
  })),
);

type AcademicDirectorAcademyProps = {
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

export default function AcademicDirectorTeacherAcademyPage(props: AcademicDirectorAcademyProps) {
  const [teachers, setTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.managementTeachers) ? props.managementTeachers : [],
  );
  const [academyTeachers, setAcademyTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.managementAcademyTeachers) ? props.managementAcademyTeachers : [],
  );
  const { toast, showToast, clearToast } = useFloatingToast();

  const panelState = useMemo(
    () => ({
      managementMode: props.managementMode || "academic_director",
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
        managementMode: props.managementMode || "academic_director",
        authRole: props.authRole || "academic_director",
        managementTeachers: teachers,
        managementAcademyTeachers: academyTeachers,
      },
    }),
    [academyTeachers, props, teachers],
  );

  return (
    <AcademicDirectorPageShell
      authLogin={props.authLogin}
      csrfToken={props.csrfToken}
      active="academy"
      sectionClassName="gap-4"
    >
      <PageHeader
        title="Teacher Academy"
        subtitle="Register academy teachers, schedule lessons, write assessments, and review teacher journeys."
        badge={
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-black uppercase tracking-wide text-primary">
            Academic Director
          </span>
        }
      />

      <Suspense
        fallback={
          <section className="rounded-2xl border border-border bg-surface p-5 text-sm font-bold text-muted-foreground shadow-card">
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
    </AcademicDirectorPageShell>
  );
}
