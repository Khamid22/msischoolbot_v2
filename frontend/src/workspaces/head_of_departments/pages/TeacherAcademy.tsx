import { Suspense, lazy, useState } from "react";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { HeadOfDepartmentPageShell } from "@/workspaces/academic_shared/AcademicDirectorShell";
import { asString } from "@/shared/lib/workspace";
import type {
  AcademyOptionRow,
  AcademyTeacher,
  ActiveTeacher,
} from "@/features/teacher-academy/model";

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
  managementTeachers?: ActiveTeacher[];
  managementAcademyTeachers?: AcademyTeacher[];
  managementGroupOptions?: AcademyOptionRow[];
  academicManagementSubjects?: AcademyOptionRow[];
  academicManagementCurriculumPrograms?: AcademyOptionRow[];
  academicManagementCurriculumItems?: AcademyOptionRow[];
};

function normalizeGroupOptions(groups: AcademyOptionRow[]) {
  return groups
    .map((group) => ({
      name: asString(group.name || group.group_name || group.label),
    }))
    .filter((group) => group.name);
}

export default function HeadOfDepartmentTeacherAcademyPage(props: HeadOfDepartmentAcademyProps) {
  const [teachers, setTeachers] = useState<ActiveTeacher[]>(
    Array.isArray(props.managementTeachers) ? props.managementTeachers : [],
  );
  const [academyTeachers, setAcademyTeachers] = useState<AcademyTeacher[]>(
    Array.isArray(props.managementAcademyTeachers) ? props.managementAcademyTeachers : [],
  );
  const { toast, showToast, clearToast } = useFloatingToast();

  return (
    <HeadOfDepartmentPageShell
      authLogin={props.authLogin}
      csrfToken={props.csrfToken}
      active="academy"
      sectionClassName="gap-2"
      maxWidthClass="max-w-[100rem]"
    >
      <Suspense
        fallback={
          <section className="rounded-xl border border-border bg-surface p-3 text-sm font-semibold text-muted-foreground shadow-card">
            Loading Teacher Academy...
          </section>
        }
      >
        <TeacherAcademyPanel
          mode="head_of_department"
          authRole={props.authRole || "head_of_department"}
          csrfToken={props.csrfToken}
          teachers={teachers}
          academyTeachers={academyTeachers}
          groupOptions={normalizeGroupOptions(Array.isArray(props.managementGroupOptions) ? props.managementGroupOptions : [])}
          subjects={Array.isArray(props.academicManagementSubjects) ? props.academicManagementSubjects : []}
          curriculumPrograms={Array.isArray(props.academicManagementCurriculumPrograms) ? props.academicManagementCurriculumPrograms : []}
          curriculumItems={Array.isArray(props.academicManagementCurriculumItems) ? props.academicManagementCurriculumItems : []}
          onAcademyChange={setAcademyTeachers}
          onTeachersChange={setTeachers}
          showToast={showToast}
        />
      </Suspense>

      <FloatingToast toast={toast} onClose={clearToast} />
    </HeadOfDepartmentPageShell>
  );
}
