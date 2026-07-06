import { Suspense, lazy, useMemo, useState } from "react";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { PageHeader } from "@/shared/ui/PageHeader";
import { AcademicDirectorPageShell } from "@/roles/common/components/AcademicDirectorShell";
import { asString } from "@/roles/admin/shared";

const TeacherAcademyPanel = lazy(() =>
  import("@/roles/admin/panels/teachers/TeacherAcademyPanel").then((module) => ({
    default: module.TeacherAcademyPanel,
  })),
);

type AcademicDirectorAcademyProps = {
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

export default function AcademicDirectorTeacherAcademyPage(props: AcademicDirectorAcademyProps) {
  const [teachers, setTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.adminTeachers) ? props.adminTeachers : [],
  );
  const [academyTeachers, setAcademyTeachers] = useState<Array<Record<string, unknown>>>(
    Array.isArray(props.adminTeacherAcademy) ? props.adminTeacherAcademy : [],
  );
  const { toast, showToast, clearToast } = useFloatingToast();

  const panelState = useMemo(
    () => ({
      adminMode: props.adminMode || "academic_director",
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
        adminMode: props.adminMode || "academic_director",
        authRole: props.authRole || "academic_director",
        adminTeachers: teachers,
        adminTeacherAcademy: academyTeachers,
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
          allowTeacherPreview={false}
        />
      </Suspense>

      <FloatingToast toast={toast} onClose={clearToast} />
    </AcademicDirectorPageShell>
  );
}
