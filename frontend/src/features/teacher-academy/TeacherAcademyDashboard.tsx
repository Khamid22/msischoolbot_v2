import {
  CheckCircle2,
  GraduationCap,
  Plus,
  TrendingUp,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import { useRef, type KeyboardEvent } from "react";

import { MetricCard } from "@/shared/ui/MetricCard";
import type {
  TeacherAcademyMode,
  TeacherAcademyStats,
  TeacherAcademyView,
} from "@/features/teacher-academy/model";

type AcademyTab = {
  key: TeacherAcademyView;
  label: string;
  count: number;
  icon: LucideIcon;
};

interface TeacherAcademyDashboardProps {
  mode: TeacherAcademyMode;
  stats: TeacherAcademyStats;
  activeTeacherCount: number;
  view: TeacherAcademyView;
  onViewChange: (view: TeacherAcademyView) => void;
  onCreateHeadOfDepartment?: () => void;
  onCreateAcademyTeacher?: () => void;
}

const focusClasses =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-card";

export function TeacherAcademyDashboard({
  mode,
  stats,
  activeTeacherCount,
  view,
  onViewChange,
  onCreateHeadOfDepartment,
  onCreateAcademyTeacher,
}: TeacherAcademyDashboardProps) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const isDirector = mode === "academic_director";
  const tabs: AcademyTab[] = [
    {
      key: "teacher_academy",
      label: "Teacher Academy",
      count: stats.total,
      icon: GraduationCap,
    },
    ...(isDirector
      ? [{
          key: "active_teachers" as const,
          label: "Active Teachers",
          count: activeTeacherCount,
          icon: UsersRound,
        }]
      : []),
  ];

  const handleTabKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? tabs.length - 1
        : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    tabRefs.current[nextIndex]?.focus();
    onViewChange(tabs[nextIndex].key);
  };

  return (
    <>
      <header className="overflow-hidden rounded-xl border border-border/80 bg-card shadow-card">
        <div className="relative p-4">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -right-16 -top-20 h-52 w-52 rounded-full bg-primary/5 blur-3xl"
          />
          <div className="relative flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 max-w-4xl">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="font-display text-xl font-black leading-tight tracking-tight text-foreground sm:text-2xl">
                  Teacher Academy
                </h1>
                <span className="inline-flex min-h-6 items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-[0.625rem] font-black uppercase tracking-wide text-primary">
                  <GraduationCap className="h-3.5 w-3.5" aria-hidden="true" />
                  {isDirector ? "Academic Director" : "Head of Departments"}
                </span>
              </div>
              <p className="mt-1 max-w-3xl text-sm leading-5 text-muted-foreground">
                {isDirector
                  ? "Register academy teachers, schedule lessons, write assessments, and review teacher journeys from one command center."
                  : "Schedule lessons, review assessments, and support academy teachers within your assigned subject scope."}
              </p>
            </div>

            {isDirector ? (
              <div className="grid w-full grid-cols-1 gap-1.5 sm:grid-cols-2 lg:w-auto lg:shrink-0">
                <button
                  type="button"
                  onClick={onCreateHeadOfDepartment}
                  className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-[0.8125rem] font-semibold text-foreground shadow-sm hover:bg-muted lg:min-h-9 ${focusClasses}`}
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  New HOD
                </button>
                <button
                  type="button"
                  onClick={onCreateAcademyTeacher}
                  className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-3 py-1.5 text-[0.8125rem] font-semibold text-primary-foreground shadow-card hover:bg-primary/90 lg:min-h-9 ${focusClasses}`}
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  New Academy Teacher
                </button>
              </div>
            ) : null}
          </div>

          <div className="relative mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
            <MetricCard
              label="In Academy"
              value={stats.total}
              detail="active academy paths"
              icon={<UsersRound className="h-4 w-4" />}
              density="compact"
              className="bg-background/80"
            />
            <MetricCard
              label="Ready"
              value={stats.ready}
              detail="promotion review"
              icon={<CheckCircle2 className="h-4 w-4" />}
              tone="success"
              density="compact"
            />
            <MetricCard
              label="Avg Score"
              value={stats.weightedAverage === null ? "—" : stats.weightedAverage.toFixed(2)}
              detail="assessment-weighted"
              icon={<TrendingUp className="h-4 w-4" />}
              tone="info"
              density="compact"
            />
          </div>
        </div>
      </header>

      {tabs.length > 1 ? <nav
        role="tablist"
        aria-label="Teacher Academy views"
        className="no-scrollbar flex max-w-full gap-1 overflow-x-auto rounded-xl border border-border bg-card p-1 shadow-sm"
      >
        {tabs.map((tab, index) => {
          const Icon = tab.icon;
          const active = tab.key === view;
          return (
            <button
              key={tab.key}
              ref={(node) => {
                tabRefs.current[index] = node;
              }}
              id={`academy-tab-${tab.key}`}
              type="button"
              role="tab"
              aria-selected={active}
              aria-controls={`academy-panel-${tab.key}`}
              tabIndex={active ? 0 : -1}
              onClick={() => onViewChange(tab.key)}
              onKeyDown={(event) => handleTabKeyDown(event, index)}
              className={`inline-flex min-h-11 min-w-[9rem] flex-1 items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-[0.8125rem] font-semibold transition-colors duration-150 motion-reduce:transition-none lg:min-h-9 ${focusClasses} ${
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{tab.label}</span>
              <span
                className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[0.625rem] tabular-nums ${
                  active ? "bg-primary-foreground/15" : "bg-muted text-muted-foreground"
                }`}
              >
                {tab.count}
              </span>
            </button>
          );
        })}
      </nav> : null}
    </>
  );
}
