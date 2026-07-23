import {
  Ban,
  BookOpenCheck,
  BriefcaseBusiness,
  GraduationCap,
  ListChecks,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import type { HrAnalyticsDashboard } from "@/features/recruitment/model";

type TotalMetric = {
  key: keyof HrAnalyticsDashboard["total_overview"];
  label: string;
  icon: LucideIcon;
  className: string;
  iconClassName: string;
};

const totalMetrics: TotalMetric[] = [
  {
    key: "applications_received",
    label: "Application Received",
    icon: UsersRound,
    className: "border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/55",
    iconClassName: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  },
  {
    key: "rejected",
    label: "Rejected",
    icon: Ban,
    className: "border-rose-200 bg-rose-50/70 dark:border-rose-800 dark:bg-rose-950/25",
    iconClassName: "bg-rose-100 text-rose-700 dark:bg-rose-900/60 dark:text-rose-200",
  },
  {
    key: "processed",
    label: "Processed",
    icon: ListChecks,
    className: "border-blue-200 bg-blue-50/70 dark:border-blue-800 dark:bg-blue-950/25",
    iconClassName: "bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-200",
  },
  {
    key: "job_interviews",
    label: "Job Interview",
    icon: BriefcaseBusiness,
    className: "border-emerald-200 bg-emerald-50/70 dark:border-emerald-800 dark:bg-emerald-950/25",
    iconClassName: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-200",
  },
  {
    key: "tests_and_demos",
    label: "Test & Demo",
    icon: BookOpenCheck,
    className: "border-orange-200 bg-orange-50/70 dark:border-orange-800 dark:bg-orange-950/25",
    iconClassName: "bg-orange-100 text-orange-700 dark:bg-orange-900/60 dark:text-orange-200",
  },
  {
    key: "teacher_academy",
    label: "Teacher Academy",
    icon: GraduationCap,
    className: "border-amber-200 bg-amber-50/70 dark:border-amber-800 dark:bg-amber-950/25",
    iconClassName: "bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-200",
  },
];

function formatCount(value: number) {
  return new Intl.NumberFormat("en").format(Number(value) || 0);
}

export function RecruitmentTotalOverview({
  totals,
}: {
  totals: HrAnalyticsDashboard["total_overview"];
}) {
  return (
    <section
      className="rounded-xl border border-border bg-card p-3 shadow-sm sm:p-4"
      aria-labelledby="recruitment-total-overview-title"
    >
      <header>
        <h2
          id="recruitment-total-overview-title"
          className="text-sm font-bold text-foreground"
        >
          Total Overview
        </h2>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          All-time distinct candidate totals. Month selection applies only to
          the pipeline overview below.
        </p>
      </header>
      <dl className="mt-3 grid grid-cols-1 gap-2 min-[430px]:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
        {totalMetrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.key}
              className={`min-w-0 rounded-lg border p-3 ${metric.className}`}
            >
              <dt className="flex min-h-9 items-center gap-2 text-[0.6875rem] font-bold uppercase leading-4 tracking-wide text-muted-foreground">
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${metric.iconClassName}`}
                  aria-hidden="true"
                >
                  <Icon className="h-4 w-4" />
                </span>
                <span>{metric.label}</span>
              </dt>
              <dd className="mt-2 text-2xl font-bold text-foreground tabular-nums">
                {formatCount(totals[metric.key])}
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
