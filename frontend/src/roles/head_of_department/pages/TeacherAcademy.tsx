import { Suspense, lazy, useMemo, useState } from "react";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { HeadOfDepartmentPageShell } from "@/roles/common/components/AcademicDirectorShell";
import { asString } from "@/roles/admin/shared";

const TeacherAcademyPanel = lazy(() =>
  import("@/roles/admin/panels/teachers/TeacherAcademyPanel").then((module) => ({
    default: module.TeacherAcademyPanel,
  })),
);

type HeadOfDepartmentAcademyProps = {
  authLogin?: string;
  authRole?: string;
  csrfToken?: string;
  adminMode?: string;
  adminSchool?: string;
  adminTeachers?: Array<Record<string, unknown>>;
  adminTeacherAcademy?: Array<Record<string, unknown>>;
  adminGroupOptions?: Array<Record<string, unknown>>;
  adminAcademicSubjects?: Array<Record<string, unknown>>;
  adminAcademicCurriculumPrograms?: Array<Record<string, unknown>>;
  adminAcademicCurriculumItems?: Array<Record<string, unknown>>;
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
    Array.isArray(props.adminTeachers) ? props.adminTeachers : [],
  );
  const [academyTeachers, setAcademyTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.adminTeacherAcademy) ? props.adminTeacherAcademy : [],
  );
  const { toast, showToast } = useFloatingToast();

  const panelState = useMemo(
    () => ({
      adminMode: "head_of_department",
      currentSchool: props.adminSchool || "all",
      teachers,
      setTeachers,
      academyTeachers,
      setAcademyTeachers,
      filteredGroupOptions: normalizeGroupOptions(
        Array.isArray(props.adminGroupOptions) ? props.adminGroupOptions : [],
      ),
      props: {
        ...props,
        adminMode: "head_of_department",
        authRole: props.authRole || "head_of_department",
        adminTeachers: teachers,
        adminTeacherAcademy: academyTeachers,
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
      <header className="rounded-xl border border-border bg-surface p-4 shadow-card">
        <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          Head of Department
        </p>
        <h1 className="mt-1 break-words text-2xl font-black text-foreground">Teacher Academy</h1>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
          Schedule lessons, review assessments, and support academy teachers within your subject scope.
        </p>
      </header>

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
          allowTeacherPreview={false}
        />
      </Suspense>

      <FloatingToast toast={toast} />
    </HeadOfDepartmentPageShell>
  );
}
