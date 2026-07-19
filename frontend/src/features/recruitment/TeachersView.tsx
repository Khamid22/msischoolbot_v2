import { GraduationCap, UserCheck } from "lucide-react";
import { useMemo, useState } from "react";

import {
  TeacherAcademyRoster,
  type TeacherRosterKind,
  useCanonicalTeacherRosterTotals,
} from "@/features/teacher-academy/TeacherAcademyRoster";
import { replaceUrlParams } from "@/features/recruitment/ui";
import type { FloatingToastTone } from "@/shared/ui/FloatingToast";

type TeachersViewProps = {
  basePath: string;
  onAnnouncement: (message: string, tone?: FloatingToastTone) => void;
};

function initialTeacherTab(): TeacherRosterKind {
  if (typeof window === "undefined") return "teacher_academy";
  return new URLSearchParams(window.location.search).get("teacher_tab") === "active_teacher"
    ? "active_teacher"
    : "teacher_academy";
}

export function TeachersView({ basePath, onAnnouncement }: TeachersViewProps) {
  const [stage, setStage] = useState<TeacherRosterKind>(initialTeacherTab);
  const totals = useCanonicalTeacherRosterTotals();
  const tabs = useMemo(() => [
    {
      key: "teacher_academy" as const,
      label: "Teacher Academy",
      count: totals.teacher_academy,
      icon: GraduationCap,
    },
    {
      key: "active_teacher" as const,
      label: "Active Teachers",
      count: totals.active_teacher,
      icon: UserCheck,
    },
  ], [totals.active_teacher, totals.teacher_academy]);

  const selectTab = (next: TeacherRosterKind) => {
    setStage(next);
    replaceUrlParams({
      teacher_tab: next === "active_teacher" ? next : null,
      teacher_page: null,
    });
  };

  const teacherTabs = (
    <div className="flex items-end" role="tablist" aria-label="Teacher roster type">
        {tabs.map((tab, index) => {
          const active = stage === tab.key;
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => selectTab(tab.key)}
              className={`relative inline-flex min-h-11 items-center gap-2 px-4 py-2 text-sm font-semibold transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transition-none sm:min-w-44 ${
                active
                  ? "z-10 bg-amber-500 text-amber-950"
                  : "bg-muted/80 text-muted-foreground hover:bg-muted hover:text-foreground"
              } ${index === 0 ? "rounded-tl-lg" : ""}`}
              style={{
                clipPath: index === 0
                  ? "polygon(0 0, calc(100% - 20px) 0, 100% 100%, 0 100%)"
                  : "polygon(0 0, calc(100% - 20px) 0, 100% 100%, 20px 100%)",
                marginLeft: index ? "-10px" : 0,
                paddingLeft: index ? "30px" : undefined,
                paddingRight: "30px",
              }}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{tab.label}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${
                active ? "bg-white/55" : "bg-background"
              }`}>
                {tab.count}
              </span>
            </button>
          );
        })}
    </div>
  );

  return (
    <section aria-label="Teachers">
      <TeacherAcademyRoster
        key={stage}
        kind={stage}
        basePath={basePath}
        onAnnouncement={onAnnouncement}
        toolbarLeading={teacherTabs}
      />
    </section>
  );
}
