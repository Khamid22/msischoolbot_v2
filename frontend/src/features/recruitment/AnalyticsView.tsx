import {
  Ban,
  BookOpenCheck,
  BriefcaseBusiness,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleArrowRight,
  Filter,
  GraduationCap,
  RotateCcw,
  UserMinus,
  UsersRound,
  XCircle,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type ReactNode } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { recruitmentRequest } from "@/features/recruitment/api";
import {
  type HrAnalyticsDashboard,
  type RecruitmentOptions,
  type RecruitmentRole,
} from "@/features/recruitment/model";
import {
  PageState,
  fieldClass,
  queryError,
  replaceUrlParams,
  secondaryButtonClass,
} from "@/features/recruitment/ui";
import { Drawer } from "@/shared/ui/Drawer";

type Filters = {
  period: "custom";
  date_from: string;
  date_to: string;
  source: string;
  subsource: string;
  position: string;
  subject_id: string;
  responsible_account_id: string;
};

type Options = {
  sources: Array<{ id: number; label: string }>;
  subsources: Array<{ id: number; parent_id: number; label: string }>;
  positions: string[];
  position_options: Array<{ id: number; label: string }>;
  subjects: Array<{ id: number; name: string }>;
  responsible_people: Array<{ id: number; name: string }>;
};

type OutcomeTab = "rejected" | "candidate_withdrew";
type TurnoverPoint = HrAnalyticsDashboard["turnover"]["monthly"][number];

const api = "/api/v1/hr/analytics";
const filterKeys = [
  "period",
  "date_from",
  "date_to",
  "source",
  "subsource",
  "position",
  "subject_id",
  "responsible_account_id",
] as const;
const chartColor = "hsl(var(--primary))";
const reasonColors = [
  "#4F6BED",
  "#F59E0B",
  "#10B981",
  "#8B5CF6",
  "#F43F5E",
  "#06B6D4",
  "#84CC16",
  "#F97316",
];

function tashkentDateKey() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tashkent",
  }).format(new Date());
}

function monthBounds(month: string, today = tashkentDateKey()) {
  const [year, monthNumber] = month.split("-").map(Number);
  const lastDay = new Date(Date.UTC(year, monthNumber, 0))
    .toISOString()
    .slice(0, 10);
  return {
    from: `${month}-01`,
    to: month === today.slice(0, 7) ? today : lastDay,
  };
}

function shiftMonth(month: string, direction: -1 | 1) {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(Date.UTC(year, monthNumber - 1 + direction, 1))
    .toISOString()
    .slice(0, 7);
}

function monthLabel(month: string) {
  return new Intl.DateTimeFormat("en", {
    month: "long",
    year: "numeric",
    timeZone: "Asia/Tashkent",
  }).format(new Date(`${month}-01T12:00:00+05:00`));
}

function shortMonthLabel(value: string) {
  const key = value.length === 7 ? `${value}-01` : value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    year: "2-digit",
    timeZone: "Asia/Tashkent",
  }).format(new Date(`${key}T12:00:00+05:00`));
}

function initialFilters(_role: RecruitmentRole): Filters {
  const params = new URLSearchParams(window.location.search);
  const requestedMonth = (params.get("date_from") || "").slice(0, 7);
  const currentMonth = tashkentDateKey().slice(0, 7);
  const month =
    /^\d{4}-\d{2}$/.test(requestedMonth) &&
    requestedMonth <= currentMonth
      ? requestedMonth
      : currentMonth;
  const bounds = monthBounds(month);
  return Object.fromEntries(
    filterKeys.map((key) => [
      key,
      key === "period"
        ? "custom"
        : key === "date_from"
          ? bounds.from
          : key === "date_to"
            ? bounds.to
            : params.get(key) || "",
    ]),
  ) as Filters;
}

function initialOutcomeTab(): OutcomeTab {
  return new URLSearchParams(window.location.search).get("analytics_outcome") ===
    "candidate_withdrew"
    ? "candidate_withdrew"
    : "rejected";
}

function numberValue(value: unknown, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${new Intl.NumberFormat("en").format(Number(value))}${suffix}`;
}

function Panel({
  title,
  description,
  className = "",
  action,
  children,
}: {
  title: string;
  description?: string;
  className?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section
      className={`min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm ${className}`}
    >
      <header className="flex min-h-[4.25rem] flex-wrap items-center justify-between gap-2 border-b border-border/70 px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-foreground">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
              {description}
            </p>
          ) : null}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-3" aria-label="Loading HR analytics">
      <div className="h-16 animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none" />
      <div className="h-20 animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none" />
      <div className="grid gap-3 xl:grid-cols-12">
        <div className="h-[23rem] animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none xl:col-span-7" />
        <div className="h-[23rem] animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none xl:col-span-5" />
      </div>
      <div className="h-64 animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none" />
    </div>
  );
}

function FilterDrawer({
  open,
  filters,
  options,
  onClose,
  onApply,
}: {
  open: boolean;
  filters: Filters;
  options?: Options;
  onClose: () => void;
  onApply: (filters: Filters) => void;
}) {
  const [draft, setDraft] = useState(filters);
  const update = (key: keyof Filters, value: string) => {
    setDraft((current) => ({
      ...current,
      [key]: value,
      ...(key === "source" ? { subsource: "" } : {}),
    }));
  };
  const relevantSubsources =
    options?.subsources.filter(
      (item) => String(item.parent_id) === draft.source,
    ) || [];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Analytics filters"
      description="Filter every recruitment metric using the same canonical candidate data."
      footer={
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className={secondaryButtonClass}
            onClick={() => {
              const cleared = {
                ...draft,
                source: "",
                subsource: "",
                position: "",
                subject_id: "",
                responsible_account_id: "",
              };
              setDraft(cleared);
            }}
          >
            Clear
          </button>
          <button
            type="button"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            onClick={() => onApply(draft)}
          >
            <Check className="h-4 w-4" />
            Apply
          </button>
        </div>
      }
    >
      <div className="grid gap-4">
        <label className="text-xs font-semibold">
          Source
          <select
            autoFocus
            value={draft.source}
            onChange={(event) => update("source", event.target.value)}
            className={`${fieldClass} mt-1`}
          >
            <option value="">All sources</option>
            {options?.sources.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold">
          Subsource
          <select
            value={draft.subsource}
            onChange={(event) => update("subsource", event.target.value)}
            disabled={!draft.source}
            className={`${fieldClass} mt-1 disabled:cursor-not-allowed disabled:opacity-60`}
          >
            <option value="">All subsources</option>
            {relevantSubsources.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold">
          Position
          <select
            value={draft.position}
            onChange={(event) => update("position", event.target.value)}
            className={`${fieldClass} mt-1`}
          >
            <option value="">All positions</option>
            {options?.position_options.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold">
          Subject
          <select
            value={draft.subject_id}
            onChange={(event) => update("subject_id", event.target.value)}
            className={`${fieldClass} mt-1`}
          >
            <option value="">All subjects</option>
            {options?.subjects.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold">
          Handled by
          <select
            value={draft.responsible_account_id}
            onChange={(event) =>
              update("responsible_account_id", event.target.value)
            }
            className={`${fieldClass} mt-1`}
          >
            <option value="">All responsible people</option>
            {options?.responsible_people.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>
    </Drawer>
  );
}

function TurnoverTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: TurnoverPoint }>;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-lg">
      <p className="font-bold">{shortMonthLabel(point.bucket)}</p>
      <dl className="mt-1.5 grid grid-cols-[auto_auto] gap-x-4 gap-y-1">
        <dt className="text-muted-foreground">Turnover rate</dt>
        <dd className="text-right font-bold tabular-nums">
          {numberValue(point.turnover_rate, "%")}
        </dd>
        <dt className="text-muted-foreground">Departures</dt>
        <dd className="text-right font-semibold tabular-nums">
          {numberValue(point.departures)}
        </dd>
        <dt className="text-muted-foreground">Average headcount</dt>
        <dd className="text-right font-semibold tabular-nums">
          {numberValue(point.average_headcount)}
        </dd>
      </dl>
    </div>
  );
}

function OutcomeDistribution({
  breakdown,
}: {
  breakdown: HrAnalyticsDashboard["outcome_reason_breakdown"][OutcomeTab];
}) {
  if (!breakdown.total) {
    return (
      <div className="flex min-h-44 items-center justify-center p-4">
        <p className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-muted-foreground">
          No outcomes were recorded for this month and filter selection.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex items-center gap-3">
        <div className="shrink-0">
          <p className="text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground">
            Total
          </p>
          <p className="text-3xl font-bold tabular-nums">
            {numberValue(breakdown.total)}
          </p>
        </div>
        <div
          className="flex h-4 min-w-0 flex-1 overflow-hidden rounded-full border border-border bg-muted"
          aria-hidden="true"
        >
          {breakdown.items.map((item, index) => (
            <span
              key={item.value}
              className="h-full first:rounded-l-full last:rounded-r-full"
              style={{
                width: `${item.percentage}%`,
                backgroundColor: reasonColors[index % reasonColors.length],
              }}
            />
          ))}
        </div>
      </div>
      <ul
        className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3"
        aria-label="Outcome reason distribution"
      >
        {breakdown.items.map((item, index) => (
          <li
            key={item.value}
            className="flex min-h-14 items-center justify-between gap-3 rounded-lg border border-border/70 bg-muted/20 px-3 py-2"
          >
            <span className="flex min-w-0 items-center gap-2">
              <span
                className="h-3 w-3 shrink-0 rounded-sm"
                style={{
                  backgroundColor: reasonColors[index % reasonColors.length],
                }}
                aria-hidden="true"
              />
              <span className="min-w-0 break-words text-xs font-semibold">
                {item.label}
              </span>
            </span>
            <span className="shrink-0 text-right">
              <strong className="block text-sm tabular-nums">
                {numberValue(item.candidates)}
              </strong>
              <span className="text-[0.625rem] font-semibold text-muted-foreground tabular-nums">
                {numberValue(item.percentage, "%")}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AnalyticsView({
  role = "hr_manager",
}: {
  basePath: string;
  role?: RecruitmentRole;
  recruitmentOptions?: RecruitmentOptions;
}) {
  const [filters, setFilters] = useState(() => initialFilters(role));
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [outcomeTab, setOutcomeTab] =
    useState<OutcomeTab>(initialOutcomeTab);
  const tashkentToday = useMemo(() => tashkentDateKey(), []);
  const selectedMonth = filters.date_from.slice(0, 7);
  const currentMonth = tashkentToday.slice(0, 7);
  const selectedPeriod = monthLabel(selectedMonth);

  const options = useQuery({
    queryKey: ["hr-analytics", "options"],
    queryFn: () => recruitmentRequest<Options>(`${api}/options`),
  });
  const params = useMemo(() => {
    const value = new URLSearchParams();
    Object.entries(filters).forEach(([key, entry]) => {
      if (entry) value.set(key, entry);
    });
    return value;
  }, [filters]);
  const dashboard = useQuery({
    queryKey: ["hr-analytics", "dashboard", params.toString()],
    queryFn: () =>
      recruitmentRequest<HrAnalyticsDashboard>(
        `${api}/dashboard?${params}`,
      ),
  });

  const replaceFilters = (next: Filters) => {
    setFilters(next);
    replaceUrlParams(next);
  };
  const selectMonth = (month: string) => {
    if (!/^\d{4}-\d{2}$/.test(month) || month > currentMonth) return;
    const bounds = monthBounds(month, tashkentToday);
    replaceFilters({
      ...filters,
      period: "custom",
      date_from: bounds.from,
      date_to: bounds.to,
    });
  };
  const clearFilters = () => {
    replaceFilters({
      ...filters,
      source: "",
      subsource: "",
      position: "",
      subject_id: "",
      responsible_account_id: "",
    });
  };
  const selectOutcome = (next: OutcomeTab) => {
    setOutcomeTab(next);
    replaceUrlParams({
      analytics_outcome:
        next === "candidate_withdrew" ? "candidate_withdrew" : null,
    });
  };
  const activeFilterCount = [
    "source",
    "subsource",
    "position",
    "subject_id",
    "responsible_account_id",
  ].filter((key) => Boolean(filters[key as keyof Filters])).length;

  if (dashboard.isLoading) return <AnalyticsSkeleton />;
  if (dashboard.error || !dashboard.data) {
    return (
      <PageState tone="error">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>{queryError(dashboard.error)}</span>
          <button
            type="button"
            className={secondaryButtonClass}
            onClick={() => void dashboard.refetch()}
          >
            <RotateCcw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </PageState>
    );
  }

  const data = dashboard.data;
  const filterNames: Array<[keyof Filters, string]> = [
    ["source", "Source"],
    ["subsource", "Subsource"],
    ["position", "Position"],
    ["subject_id", "Subject"],
    ["responsible_account_id", "Handled by"],
  ];
  const optionLabel = (key: keyof Filters, value: string) => {
    if (key === "source")
      return (
        options.data?.sources.find((item) => String(item.id) === value)
          ?.label || value
      );
    if (key === "subsource")
      return (
        options.data?.subsources.find((item) => String(item.id) === value)
          ?.label || value
      );
    if (key === "position")
      return (
        options.data?.position_options.find(
          (item) => String(item.id) === value,
        )?.label || value
      );
    if (key === "subject_id")
      return (
        options.data?.subjects.find((item) => String(item.id) === value)
          ?.name || value
      );
    if (key === "responsible_account_id")
      return (
        options.data?.responsible_people.find(
          (item) => String(item.id) === value,
        )?.name || value
      );
    return value;
  };

  const monthlyStages = [
    {
      key: "application_received",
      label: "Application Received",
      value: data.monthly_stage_totals.application_received,
      icon: UsersRound,
      className:
        "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-50",
    },
    {
      key: "rejected",
      label: "Rejected",
      value: data.monthly_stage_totals.rejected,
      icon: Ban,
      className: "bg-rose-500 text-white",
    },
    {
      key: "in_process",
      label: "In Process",
      value: data.monthly_stage_totals.in_process,
      icon: CircleArrowRight,
      className: "bg-blue-600 text-white",
    },
    {
      key: "job_interview",
      label: "Job Interview",
      value: data.monthly_stage_totals.job_interview,
      icon: BriefcaseBusiness,
      className: "bg-emerald-600 text-white",
    },
    {
      key: "test_and_demo",
      label: "Test & Demo",
      value: data.monthly_stage_totals.test_and_demo,
      icon: BookOpenCheck,
      className: "bg-orange-500 text-orange-950",
    },
    {
      key: "teacher_academy",
      label: "Teacher Academy",
      value: data.monthly_stage_totals.teacher_academy,
      icon: GraduationCap,
      className: "bg-amber-400 text-amber-950",
    },
  ] as const;

  const journeyCounts = new Map(
    data.journey.map((item) => [item.stage, item.candidates]),
  );
  const funnelDefinitions = [
    {
      key: "new_candidate",
      label: "New Applications",
      value:
        journeyCounts.get("new_candidate") ??
        data.monthly_stage_totals.application_received,
    },
    {
      key: "responded",
      label: "Shortlisted",
      value: journeyCounts.get("responded") || 0,
    },
    {
      key: "job_interview",
      label: "Job Interview",
      value: journeyCounts.get("job_interview") || 0,
    },
    {
      key: "test_and_demo",
      label: "Test & Demo",
      value: journeyCounts.get("test_and_demo") || 0,
    },
    {
      key: "under_review",
      label: "Final Decision",
      value: journeyCounts.get("under_review") || 0,
    },
  ];
  const funnel = funnelDefinitions.map((item, index) => {
    const previous = index ? funnelDefinitions[index - 1].value : null;
    return {
      ...item,
      conversion:
        previous && previous > 0
          ? Math.round((item.value / previous) * 1000) / 10
          : null,
    };
  });
  const turnoverMaximum = Math.max(
    10,
    Math.ceil(
      Math.max(0, ...data.turnover.monthly.map((item) => item.turnover_rate)) /
        5,
    ) * 5,
  );
  const turnoverRange =
    data.turnover.from && data.turnover.to
      ? `${shortMonthLabel(data.turnover.from)}–${shortMonthLabel(data.turnover.to)}`
      : "Trailing 12 months";
  const activeBreakdown = data.outcome_reason_breakdown[outcomeTab];

  return (
    <div className="min-w-0 space-y-3">
      <section className="rounded-xl border border-border bg-card p-2 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div
            className="inline-flex min-h-11 items-center overflow-hidden rounded-lg border border-border"
            role="group"
            aria-label="Analytics month"
          >
            <button
              type="button"
              className="flex h-11 w-11 items-center justify-center text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35 motion-reduce:transition-none"
              onClick={() => selectMonth(shiftMonth(selectedMonth, -1))}
              aria-label="Previous month"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <label className="relative flex h-11 min-w-40 cursor-pointer items-center justify-center border-x border-border px-4 text-xs font-semibold">
              <span>{selectedPeriod}</span>
              <span className="sr-only">Select month and year</span>
              <input
                type="month"
                value={selectedMonth}
                max={currentMonth}
                onChange={(event) => selectMonth(event.target.value)}
                className="absolute inset-0 cursor-pointer opacity-0"
                aria-label="Select analytics month and year"
              />
            </label>
            <button
              type="button"
              disabled={selectedMonth >= currentMonth}
              className="flex h-11 w-11 items-center justify-center text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35 disabled:cursor-not-allowed disabled:opacity-35 motion-reduce:transition-none"
              onClick={() => selectMonth(shiftMonth(selectedMonth, 1))}
              aria-label="Next month"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <button
            type="button"
            className={`${secondaryButtonClass} relative !min-h-11 !px-3 !text-xs`}
            onClick={() => setFiltersOpen(true)}
          >
            <Filter className="h-4 w-4" />
            Filters
            {activeFilterCount ? (
              <span className="rounded-full bg-primary px-1.5 py-0.5 text-[0.625rem] text-primary-foreground">
                {activeFilterCount}
              </span>
            ) : null}
          </button>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 border-t border-border/70 pt-2">
          <p className="mr-auto text-xs font-semibold text-foreground">
            Monthly activity · {selectedPeriod}
          </p>
          {filterNames
            .filter(([key]) => filters[key])
            .map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() =>
                  replaceFilters({
                    ...filters,
                    [key]: "",
                    ...(key === "source" ? { subsource: "" } : {}),
                  })
                }
                className="inline-flex min-h-9 items-center rounded-full border border-border bg-muted/50 px-2.5 text-[0.6875rem] font-semibold transition-colors hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 motion-reduce:transition-none"
              >
                {label}: {optionLabel(key, filters[key])}
                <XCircle className="ml-1.5 h-3.5 w-3.5" />
              </button>
            ))}
          {activeFilterCount ? (
            <button
              type="button"
              onClick={clearFilters}
              className="min-h-9 px-2 text-[0.6875rem] font-semibold text-primary hover:underline"
            >
              Clear all
            </button>
          ) : null}
        </div>
      </section>

      <section
        className="overflow-x-auto rounded-xl border border-border bg-card px-2 pt-2 shadow-sm"
        aria-label={`Monthly recruitment totals for ${selectedPeriod}`}
      >
        <ol className="flex min-w-[68rem] items-end">
          {monthlyStages.map((stage, index) => {
            const Icon = stage.icon;
            return (
              <li
                key={stage.key}
                className={`relative flex min-h-[4.5rem] min-w-44 flex-1 items-center gap-2 px-4 py-2.5 ${stage.className} ${
                  index === 0 ? "rounded-tl-lg" : ""
                }`}
                style={{
                  clipPath:
                    index === 0
                      ? "polygon(0 0, calc(100% - 1.25rem) 0, 100% 100%, 0 100%)"
                      : "polygon(0 0, calc(100% - 1.25rem) 0, 100% 100%, 1.25rem 100%)",
                  marginLeft: index ? "-0.625rem" : 0,
                  paddingLeft: index ? "1.875rem" : undefined,
                  paddingRight: "1.875rem",
                  zIndex: monthlyStages.length - index,
                }}
              >
                <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                <span className="min-w-0 flex-1 text-xs font-bold uppercase leading-4 tracking-wide">
                  {stage.label}
                </span>
                <span className="rounded-full bg-white/70 px-2.5 py-1 text-sm font-bold text-slate-950 tabular-nums">
                  {numberValue(stage.value)}
                </span>
              </li>
            );
          })}
        </ol>
      </section>

      <div className="grid gap-3 xl:grid-cols-12">
        <Panel
          title="Employees Turnover"
          description={`Recruited Active Teachers · ${turnoverRange}`}
          className="xl:col-span-7"
        >
          <div className="h-[20rem] min-w-0 px-2 pb-2 pt-4 sm:px-4">
            <p className="sr-only">
              Monthly turnover rate for recruited Active Teachers. Tooltips
              include departures and average headcount.
            </p>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={data.turnover.monthly}
                margin={{ top: 8, right: 14, left: -10, bottom: 4 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="hsl(var(--border))"
                />
                <XAxis
                  dataKey="bucket"
                  tickFormatter={(value) => shortMonthLabel(String(value))}
                  tick={{
                    fontSize: 10,
                    fill: "hsl(var(--muted-foreground))",
                  }}
                  axisLine={false}
                  tickLine={false}
                  minTickGap={16}
                />
                <YAxis
                  domain={[0, turnoverMaximum]}
                  tickFormatter={(value) => `${value}%`}
                  tick={{
                    fontSize: 10,
                    fill: "hsl(var(--muted-foreground))",
                  }}
                  axisLine={false}
                  tickLine={false}
                  width={42}
                />
                <Tooltip
                  content={<TurnoverTooltip />}
                  cursor={{ stroke: "hsl(var(--border))" }}
                />
                <Line
                  type="monotone"
                  dataKey="turnover_rate"
                  name="Turnover rate"
                  stroke={chartColor}
                  strokeWidth={3}
                  dot={false}
                  activeDot={{ r: 5 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel
          title="Funnel Overview"
          description={`Application cohort · ${selectedPeriod}`}
          className="xl:col-span-5"
        >
          <div className="overflow-x-auto p-4">
            <ol
              className="flex min-h-[18rem] min-w-[46rem] items-center"
              aria-label="Recruitment funnel"
            >
              {funnel.map((stage, index) => (
                <li
                  key={stage.key}
                  className="contents"
                  aria-label={`${stage.label}: ${stage.value}${
                    stage.conversion === null
                      ? ""
                      : `, ${stage.conversion}% from prior stage`
                  }`}
                >
                  <div
                    className="flex min-h-40 min-w-0 flex-1 flex-col items-center justify-center border-y border-primary/20 bg-primary/10 px-2 text-center first:rounded-l-xl last:rounded-r-xl"
                    style={{
                      clipPath:
                        index === 0
                          ? "polygon(0 8%, 100% 0, 100% 100%, 0 92%)"
                          : index === funnel.length - 1
                            ? "polygon(0 0, 100% 15%, 100% 85%, 0 100%)"
                            : "polygon(0 0, 100% 6%, 100% 94%, 0 100%)",
                    }}
                  >
                    <span className="text-[0.6875rem] font-bold uppercase leading-4 tracking-wide text-muted-foreground">
                      {stage.label}
                    </span>
                    <strong className="mt-2 text-3xl font-bold text-primary tabular-nums">
                      {numberValue(stage.value)}
                    </strong>
                    <span className="mt-2 min-h-5 rounded-full bg-background/80 px-2 py-1 text-[0.625rem] font-semibold text-muted-foreground">
                      {stage.conversion === null
                        ? "Entry stage"
                        : `${numberValue(stage.conversion, "%")} from prior`}
                    </span>
                  </div>
                  {index < funnel.length - 1 ? (
                    <ChevronRight
                      className="-mx-1 h-6 w-6 shrink-0 text-primary"
                      aria-hidden="true"
                    />
                  ) : null}
                </li>
              ))}
            </ol>
          </div>
        </Panel>
      </div>

      <Panel
        title="Candidate Outcomes"
        description={`Reasons recorded during ${selectedPeriod}`}
        action={
          <div
            role="tablist"
            aria-label="Candidate outcome type"
            className="inline-flex rounded-lg border border-border bg-muted/45 p-1"
          >
            <button
              id="analytics-outcome-tab-rejected"
              type="button"
              role="tab"
              aria-selected={outcomeTab === "rejected"}
              aria-controls="analytics-outcome-panel"
              tabIndex={outcomeTab === "rejected" ? 0 : -1}
              onClick={() => selectOutcome("rejected")}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight" || event.key === "ArrowLeft")
                  selectOutcome("candidate_withdrew");
              }}
              className={`min-h-9 rounded-md px-3 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none ${
                outcomeTab === "rejected"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Rejections
            </button>
            <button
              id="analytics-outcome-tab-candidate-withdrew"
              type="button"
              role="tab"
              aria-selected={outcomeTab === "candidate_withdrew"}
              aria-controls="analytics-outcome-panel"
              tabIndex={outcomeTab === "candidate_withdrew" ? 0 : -1}
              onClick={() => selectOutcome("candidate_withdrew")}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight" || event.key === "ArrowLeft")
                  selectOutcome("rejected");
              }}
              className={`min-h-9 rounded-md px-3 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 motion-reduce:transition-none ${
                outcomeTab === "candidate_withdrew"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Candidate Withdraw
            </button>
          </div>
        }
      >
        <div
          id="analytics-outcome-panel"
          role="tabpanel"
          aria-labelledby={`analytics-outcome-tab-${outcomeTab}`}
        >
          <OutcomeDistribution breakdown={activeBreakdown} />
        </div>
      </Panel>

      <FilterDrawer
        key={`${filtersOpen}:${filters.source}:${filters.subsource}:${filters.position}:${filters.subject_id}:${filters.responsible_account_id}`}
        open={filtersOpen}
        filters={filters}
        options={options.data}
        onClose={() => setFiltersOpen(false)}
        onApply={(next) => {
          replaceFilters(next);
          setFiltersOpen(false);
        }}
      />
    </div>
  );
}
