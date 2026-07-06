import { Suspense, lazy, useMemo, useState } from "react";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import {
  AcademicDirectorMobileNav,
  AcademicDirectorSidebar,
} from "@/roles/common/components/AcademicDirectorShell";
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
  const { toast, showToast } = useFloatingToast();

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
    <div className="min-h-[var(--tg-viewport-height)] bg-background text-foreground">
      <AcademicDirectorSidebar authLogin={props.authLogin} csrfToken={props.csrfToken} active="academy" />

      <main className="min-h-[var(--tg-viewport-height)] px-3 pb-[calc(var(--app-bottom-inset)+5.75rem)] pt-4 sm:px-5 lg:ml-64 lg:px-6 lg:pb-6">
        <section className="mx-auto flex max-w-7xl flex-col gap-4">
          <header className="rounded-2xl border border-border bg-surface p-4 shadow-card">
            <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
              Academic Director
            </p>
            <h1 className="mt-1 text-2xl font-black text-foreground">Teacher Academy</h1>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
              Register academy teachers, schedule lessons, write assessments, and review teacher journeys.
            </p>
          </header>

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
        </section>
      </main>

      <AcademicDirectorMobileNav active="academy" />
      <FloatingToast toast={toast} />
    </div>
  );
}
