import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarClock,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Clock3,
  Filter,
  RotateCcw,
  SearchCheck,
  ShieldCheck,
  TrendingUp,
  UserCheck,
  UserMinus,
  UsersRound,
  XCircle,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { recruitmentRequest } from "@/features/recruitment/api";
import {
  dateLabel,
  humanize,
  stageLabels,
  type HrAnalyticsDashboard,
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
const chartColors = {
  primary: "hsl(var(--primary))",
  secondary: "#8B9CF6",
  lime: "#B7F34A",
  success: "hsl(var(--success))",
  destructive: "hsl(var(--destructive))",
  amber: "#F59E0B",
  muted: "#CBD5E1",
};
const sourcePalette = [
  chartColors.primary,
  "#2563EB",
  "#84CC16",
  chartColors.secondary,
  chartColors.amber,
  "#0D9488",
  "#7C3AED",
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

function numberValue(value: unknown, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${new Intl.NumberFormat("en").format(Number(value))}${suffix}`;
}

function trendBucketLabel(value: string, bucket: HrAnalyticsDashboard["range"]["bucket"]) {
  const parsed = new Date(`${value}T00:00:00+05:00`);
  if (bucket === "month") return new Intl.DateTimeFormat("en", { month: "short", year: "2-digit", timeZone: "Asia/Tashkent" }).format(parsed);
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: "Asia/Tashkent" }).format(parsed);
}

function KpiCard({
  label,
  metric,
  period,
  icon,
  accent,
}: {
  label: string;
  metric: { value: number; total: number; previous: number; delta_percentage?: number | null };
  period: string;
  icon: ReactNode;
  accent?: boolean;
}) {
  return (
    <article className={`min-h-[98px] rounded-xl border p-2.5 shadow-sm transition-[border-color,box-shadow] duration-200 motion-reduce:transition-none ${accent ? "border-lime-300 bg-lime-200/80 text-slate-950" : "border-border bg-card"}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className={`text-[10px] font-semibold uppercase leading-tight tracking-[0.08em] ${accent ? "text-slate-700" : "text-muted-foreground"}`}>{label}</p>
          <p className="mt-1 text-2xl font-bold tracking-tight tabular-nums">{numberValue(metric.value)}</p>
        </div>
        <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${accent ? "bg-white/65 text-slate-900" : "bg-primary/8 text-primary"}`}>{icon}</span>
      </div>
      <div className={`mt-1.5 flex items-center justify-between gap-2 text-[10px] font-semibold ${accent ? "text-slate-700" : "text-muted-foreground"}`}>
        <span>{period}</span>
        <span>Total {numberValue(metric.total)}</span>
      </div>
    </article>
  );
}

function EvaluationKpi({
  label,
  metric,
}: {
  label: string;
  metric: {
    total: number;
    unique_candidates: number;
    passed: number;
    failed: number;
    pass_rate: number;
  };
}) {
  return (
    <article className="rounded-xl border border-border bg-card p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-1 text-2xl font-bold tabular-nums">
            {numberValue(metric.unique_candidates)}
          </p>
          <p className="text-[10px] text-muted-foreground">
            Unique candidates · best valid attempt
          </p>
        </div>
        <span className="rounded-full bg-primary/8 px-2 py-1 text-xs font-semibold text-primary">
          {numberValue(metric.pass_rate, "%")}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <span className="rounded-lg bg-emerald-50 px-2 py-1.5 font-semibold text-emerald-800">
          Passed {numberValue(metric.passed)}
        </span>
        <span className="rounded-lg bg-red-50 px-2 py-1.5 font-semibold text-red-700">
          Failed {numberValue(metric.failed)}
        </span>
      </div>
      <p className="mt-2 text-[10px] font-semibold text-muted-foreground">
        Total attempts {numberValue(metric.total)}
      </p>
    </article>
  );
}

function SecondaryMetric({
  label,
  value,
  total,
  icon,
  tone = "primary",
}: {
  label: string;
  value: string | number;
  total?: number;
  icon: ReactNode;
  tone?: "primary" | "success" | "warning" | "danger";
}) {
  const toneClass = {
    primary: "bg-primary/8 text-primary",
    success: "bg-success/10 text-success",
    warning: "bg-amber-100 text-amber-800",
    danger: "bg-destructive/8 text-destructive",
  }[tone];
  return (
    <article className="flex min-h-[64px] items-center gap-2 rounded-xl border border-border bg-card p-2">
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneClass}`}>{icon}</span>
      <div className="min-w-0">
        <p className="line-clamp-2 text-[10px] font-semibold uppercase leading-tight tracking-wide text-muted-foreground">{label}</p>
        <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2 gap-y-0">
          <p className="text-lg font-bold tabular-nums">{value}</p>
          {total !== undefined ? <span className="text-[10px] font-semibold text-muted-foreground">Total {numberValue(total)}</span> : null}
        </div>
      </div>
    </article>
  );
}

function Panel({
  title,
  description,
  icon,
  className = "",
  children,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm ${className}`}>
      <header className="flex min-h-12 items-start justify-between gap-2 border-b border-border/70 px-3 py-1.5">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-[13px] font-semibold leading-tight">{icon}{title}</h2>
          {description ? <p className="mt-0.5 line-clamp-2 text-[10px] leading-tight text-muted-foreground">{description}</p> : null}
        </div>
      </header>
      {children}
    </section>
  );
}

function EmptyChart({ children }: { children: ReactNode }) {
  return <div className="flex min-h-52 items-center justify-center px-3 text-center text-sm text-muted-foreground">{children}</div>;
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-2" aria-label="Loading HR analytics">
      <div className="h-16 animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none" />
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => <div key={index} className="h-[98px] animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none" />)}
      </div>
      <div className="grid gap-2 xl:grid-cols-12">
        <div className="h-72 animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none xl:col-span-8" />
        <div className="h-72 animate-pulse rounded-xl border border-border bg-muted/45 motion-reduce:animate-none xl:col-span-4" />
      </div>
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
  const relevantSubsources = options?.subsources.filter((item) => String(item.parent_id) === draft.source) || [];
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Analytics filters"
      description="Use standardized recruitment values for reliable comparisons."
      footer={(
        <div className="flex justify-end gap-2">
          <button type="button" className={secondaryButtonClass} onClick={() => {
            const cleared = { ...draft, source: "", subsource: "", position: "", subject_id: "", responsible_account_id: "" };
            setDraft(cleared);
          }}>Clear</button>
          <button type="button" className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-semibold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40" onClick={() => onApply(draft)}>
            <Check className="h-4 w-4" />Apply
          </button>
        </div>
      )}
    >
      <div className="grid gap-4">
        <label className="text-xs font-semibold">Source
          <select autoFocus value={draft.source} onChange={(event) => update("source", event.target.value)} className={`${fieldClass} mt-1`}>
            <option value="">All sources</option>
            {options?.sources.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold">Subsource
          <select value={draft.subsource} onChange={(event) => update("subsource", event.target.value)} disabled={!draft.source} className={`${fieldClass} mt-1 disabled:cursor-not-allowed disabled:opacity-60`}>
            <option value="">All subsources</option>
            {relevantSubsources.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold">Position
          <select value={draft.position} onChange={(event) => update("position", event.target.value)} className={`${fieldClass} mt-1`}>
            <option value="">All positions</option>
            {options?.position_options.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold">Subject
          <select value={draft.subject_id} onChange={(event) => update("subject_id", event.target.value)} className={`${fieldClass} mt-1`}>
            <option value="">All subjects</option>
            {options?.subjects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="text-xs font-semibold">Handled by
          <select value={draft.responsible_account_id} onChange={(event) => update("responsible_account_id", event.target.value)} className={`${fieldClass} mt-1`}>
            <option value="">All responsible people</option>
            {options?.responsible_people.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <span className="mt-1 block text-[11px] font-normal text-muted-foreground">Includes anyone responsible during at least one recruitment stage.</span>
        </label>
      </div>
    </Drawer>
  );
}

function activityLabel(eventType: string) {
  const known: Record<string, string> = {
    "candidate.created": "Application received",
    "candidate.stage_changed": "Recruitment stage changed",
    "candidate.final_decision_made": "Final decision recorded",
    "candidate.interview_recorded": "Job interview recorded",
    "candidate.subject_test_recorded": "Subject test recorded",
    "candidate.demo_recorded": "Demo lesson evaluated",
    "candidate.appointment_scheduled": "Appointment scheduled",
    "candidate.document_uploaded": "Document uploaded",
    "candidate.profile_updated": "Candidate profile updated",
  };
  return known[eventType] || humanize(eventType.replace(/^candidate\./, ""));
}

export function AnalyticsView({ basePath, role = "hr_manager" }: { basePath: string; role?: RecruitmentRole }) {
  const [filters, setFilters] = useState(() => initialFilters(role));
  const [filtersOpen, setFiltersOpen] = useState(false);
  const tashkentToday = useMemo(() => tashkentDateKey(), []);
  const selectedMonth = filters.date_from.slice(0, 7);
  const currentMonth = tashkentToday.slice(0, 7);
  const options = useQuery({
    queryKey: ["hr-analytics", "options"],
    queryFn: () => recruitmentRequest<Options>(`${api}/options`),
  });
  const params = useMemo(() => {
    const value = new URLSearchParams();
    Object.entries(filters).forEach(([key, entry]) => { if (entry) value.set(key, entry); });
    return value;
  }, [filters]);
  const dashboard = useQuery({
    queryKey: ["hr-analytics", "dashboard", params.toString()],
    queryFn: () => recruitmentRequest<HrAnalyticsDashboard>(`${api}/dashboard?${params}`),
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
  const activeFilterCount = ["source", "subsource", "position", "subject_id", "responsible_account_id"]
    .filter((key) => Boolean(filters[key as keyof Filters])).length;

  if (dashboard.isLoading) return <AnalyticsSkeleton />;
  if (dashboard.error || !dashboard.data) {
    return (
      <PageState tone="error">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>{queryError(dashboard.error)}</span>
          <button type="button" className={secondaryButtonClass} onClick={() => void dashboard.refetch()}><RotateCcw className="h-4 w-4" />Retry</button>
        </div>
      </PageState>
    );
  }

  const data = dashboard.data;
  const selectedPeriod = monthLabel(selectedMonth);
  const topSources = data.source_distribution.slice(0, 6);
  const hasTrend = data.activity_trend.some((item) => item.applications || item.shortlisted || item.hired || item.rejected);
  const applicationPeak = data.activity_trend.reduce<(typeof data.activity_trend)[number] | null>(
    (peak, item) => (!peak || item.applications > peak.applications ? item : peak),
    null,
  );
  const maxJourney = Math.max(1, ...data.journey.map((item) => item.candidates));
  const roleIsHr = data.role === "hr_manager";
  const filterNames: Array<[keyof Filters, string]> = [
    ["source", "Source"],
    ["subsource", "Subsource"],
    ["position", "Position"],
    ["subject_id", "Subject"],
    ["responsible_account_id", "Handled by"],
  ];
  const optionLabel = (key: keyof Filters, value: string) => {
    if (key === "source") return options.data?.sources.find((item) => String(item.id) === value)?.label || value;
    if (key === "subsource") return options.data?.subsources.find((item) => String(item.id) === value)?.label || value;
    if (key === "position") return options.data?.position_options.find((item) => String(item.id) === value)?.label || value;
    if (key === "subject_id") return options.data?.subjects.find((item) => String(item.id) === value)?.name || value;
    if (key === "responsible_account_id") return options.data?.responsible_people.find((item) => String(item.id) === value)?.name || value;
    return value;
  };

  return (
    <div className="space-y-2">
      <section className="rounded-xl border border-border bg-card p-2 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div
            className="inline-flex min-h-10 items-center overflow-hidden rounded-lg border border-border"
            role="group"
            aria-label="Analytics month"
          >
            <button
              type="button"
              className="flex h-10 w-10 items-center justify-center text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
              onClick={() => selectMonth(shiftMonth(selectedMonth, -1))}
              aria-label="Previous month"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <label className="relative flex h-10 min-w-36 cursor-pointer items-center justify-center border-x border-border px-4 text-xs font-semibold">
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
              className="flex h-10 w-10 items-center justify-center text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35 disabled:cursor-not-allowed disabled:opacity-35"
              onClick={() => selectMonth(shiftMonth(selectedMonth, 1))}
              aria-label="Next month"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          <button type="button" className={`${secondaryButtonClass} relative !min-h-10 !px-3 !text-xs before:absolute before:-inset-y-0.5 before:inset-x-0`} onClick={() => setFiltersOpen(true)}>
            <Filter className="h-4 w-4" />Filters
            {activeFilterCount ? <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] text-primary-foreground">{activeFilterCount}</span> : null}
          </button>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 border-t border-border/70 pt-1.5">
          <p className="mr-auto text-xs font-semibold text-foreground">{selectedPeriod}</p>
          {filterNames.filter(([key]) => filters[key]).map(([key, label]) => (
            <button key={key} type="button" onClick={() => replaceFilters({
              ...filters,
              [key]: "",
              ...(key === "source" ? { subsource: "" } : {}),
            })} className="inline-flex min-h-9 items-center rounded-full border border-border bg-muted/50 px-2.5 text-[11px] font-semibold hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">
              {label}: {optionLabel(key, filters[key])}<XCircle className="ml-1.5 h-3.5 w-3.5" />
            </button>
          ))}
          {activeFilterCount ? <button type="button" onClick={clearFilters} className="min-h-9 px-2 text-[11px] font-semibold text-primary hover:underline">Clear all</button> : null}
        </div>
      </section>

      <h2 className="text-xs font-semibold">
        Recruitment activity · {selectedPeriod}
      </h2>

      <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5" aria-label="Canonical recruitment event metrics">
        <KpiCard label="Applications" metric={data.summary_cards.applications} period={selectedPeriod} icon={<UsersRound className="h-4 w-4" />} accent />
        <KpiCard label="Final Decision" metric={data.summary_cards.final_decision} period={selectedPeriod} icon={<SearchCheck className="h-4 w-4" />} />
        <KpiCard label="Teacher Academy" metric={data.summary_cards.teacher_academy} period={selectedPeriod} icon={<ShieldCheck className="h-4 w-4" />} />
        <KpiCard label="Active Teachers" metric={data.summary_cards.active_teachers} period={selectedPeriod} icon={<UserCheck className="h-4 w-4" />} />
        <KpiCard label="Rejected" metric={data.summary_cards.rejected} period={selectedPeriod} icon={<UserMinus className="h-4 w-4" />} />
      </section>

      <section className="grid gap-2 md:grid-cols-3" aria-label="Evaluation outcome metrics">
        <EvaluationKpi label="Job Interviews" metric={data.evaluation_kpis.interview} />
        <EvaluationKpi label="Demo Lessons" metric={data.evaluation_kpis.demo} />
        <EvaluationKpi label="Subject Tests" metric={data.evaluation_kpis.subject_test} />
      </section>

      <div className="grid gap-2 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4" aria-label="Additional selected cohort metrics">
          <SecondaryMetric label="Teacher Academy added" value={numberValue(data.secondary_kpis.academy_accepted)} total={data.secondary_kpis.academy_total} icon={<ShieldCheck className="h-4 w-4" />} tone="warning" />
          <SecondaryMetric label="Withdrawn" value={numberValue(data.secondary_kpis.withdrawn)} total={data.secondary_kpis.withdrawn_total} icon={<UserMinus className="h-4 w-4" />} />
          <SecondaryMetric label="Avg time to hire" value={numberValue(data.secondary_kpis.average_time_to_hire_days, "d")} icon={<Clock3 className="h-4 w-4" />} />
          <SecondaryMetric label="Active conversion" value={numberValue(data.secondary_kpis.overall_conversion_percentage, "%")} icon={<TrendingUp className="h-4 w-4" />} tone="success" />
        </section>
        <section className="rounded-xl border border-border bg-card p-2" aria-label="Live recruitment snapshot">
          <div className="mb-2 flex items-center justify-between gap-2 px-1">
            <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Live snapshot</h2>
            <span className="text-[10px] text-muted-foreground">As of {dateLabel(data.as_of)}</span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <SecondaryMetric label="Current active pipeline" value={numberValue(data.secondary_kpis.active_candidates)} icon={<UsersRound className="h-4 w-4" />} />
            <SecondaryMetric label="SLA overdue now" value={numberValue(data.secondary_kpis.sla_overdue_now)} icon={<AlertTriangle className="h-4 w-4" />} tone={data.secondary_kpis.sla_overdue_now ? "danger" : "success"} />
          </div>
        </section>
      </div>

      <div className="grid gap-2 xl:grid-cols-12">
        <Panel title={`Recruitment activity · ${selectedPeriod}`} description="Applications and actual stage events" icon={<Activity className="h-4 w-4 text-primary" />} className="xl:col-span-8">
          {hasTrend ? (
            <div className="h-[260px] min-w-0 px-1 pb-1 pt-2 sm:px-2">
              <p className="sr-only">Recruitment activity chart. Applications, shortlisted candidates, active hires and rejections over the selected period.</p>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.activity_trend} margin={{ top: 14, right: 12, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                  <XAxis dataKey="bucket" tickFormatter={(value) => trendBucketLabel(String(value), data.range.bucket)} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} minTickGap={20} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <Tooltip labelFormatter={(value) => trendBucketLabel(String(value), data.range.bucket)} contentStyle={{ borderRadius: 10, borderColor: "hsl(var(--border))", fontSize: 12, maxWidth: 260 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {applicationPeak && applicationPeak.applications > 0 ? (
                    <ReferenceLine
                      x={applicationPeak.bucket}
                      stroke={chartColors.amber}
                      strokeDasharray="4 4"
                      label={{
                        value: `Peak ${applicationPeak.applications} · ${trendBucketLabel(applicationPeak.bucket, data.range.bucket)}`,
                        position: "insideTopRight",
                        fill: "#B45309",
                        fontSize: 10,
                      }}
                    />
                  ) : null}
                  <Line type="monotone" dataKey="applications" name="Applications" stroke={chartColors.primary} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
                  <Line type="monotone" dataKey="shortlisted" name="Shortlisted" stroke={chartColors.secondary} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="hired" name="Active Teachers" stroke={chartColors.success} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="rejected" name="Rejected" stroke={chartColors.destructive} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyChart>No recruitment events in this period.</EmptyChart>}
        </Panel>

        <Panel title={`Applicant sources · ${selectedPeriod}`} description={`Application cohort · ${data.summary_cards.applications.value} applications`} icon={<CircleDot className="h-4 w-4 text-primary" />} className="xl:col-span-4">
          {topSources.length ? (
            <div className="grid min-h-[260px] grid-cols-1 items-center gap-1 p-2 sm:grid-cols-[minmax(0,1fr)_minmax(150px,0.8fr)] xl:grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_minmax(150px,0.8fr)]">
              <div className="h-44 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={topSources} dataKey="candidates" nameKey="source" innerRadius="54%" outerRadius="82%" paddingAngle={1} minAngle={3} stroke="none">
                      {topSources.map((item, index) => <Cell key={item.source} fill={sourcePalette[index % sourcePalette.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: 10, borderColor: "hsl(var(--border))", fontSize: 12 }} formatter={(value, _name, item) => [`${value} · ${item.payload.percentage}%`, item.payload.source]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="grid gap-2 text-[11px]" aria-label="Applicant source counts">
                {topSources.map((item, index) => (
                  <li key={item.source} className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: sourcePalette[index % sourcePalette.length] }} /><span className="truncate">{item.source}</span></span>
                    <strong className="tabular-nums">{item.candidates} · {item.percentage}%</strong>
                  </li>
                ))}
              </ul>
            </div>
          ) : <EmptyChart>No source data in this cohort.</EmptyChart>}
        </Panel>

        <Panel title={`Recruitment journey · ${selectedPeriod}`} description="Application cohort · distinct applicants who reached each stage" icon={<BarChart3 className="h-4 w-4 text-primary" />} className="xl:col-span-7">
          <div className="space-y-2 p-3">
            {data.journey.map((item) => (
              <div key={item.stage}>
                <div className="mb-1 flex items-center justify-between gap-2 text-[11px]">
                  <span className="font-semibold">{stageLabels[item.stage] || humanize(item.stage)}</span>
                  <span className="flex items-center gap-2 tabular-nums text-muted-foreground">
                    {item.conversion_percentage !== null && item.conversion_percentage !== undefined ? `${item.conversion_percentage}% from prior` : "Entry stage"}
                    <strong className="text-foreground">{item.candidates}</strong>
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${item.candidates / maxJourney * 100}%` }} />
                </div>
              </div>
            ))}
            <div className="grid gap-1.5 border-t border-border pt-2 sm:grid-cols-2">
              {data.outcomes.map((item) => (
                <div key={item.outcome} className="flex min-h-9 items-center justify-between rounded-lg bg-muted/45 px-2.5 text-[11px]">
                  <span className="font-semibold">{stageLabels[item.outcome] || humanize(item.outcome)}</span>
                  <strong className="tabular-nums">{item.candidates}</strong>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title={`Applications by position · ${selectedPeriod}`} description="Application cohort · standardized positions" icon={<UsersRound className="h-4 w-4 text-primary" />} className="xl:col-span-5">
          {data.position_distribution.length ? (
            <div className="h-[280px] min-w-0 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.position_distribution.slice(0, 8)} layout="vertical" margin={{ top: 0, right: 32, left: 16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                  <XAxis type="number" allowDecimals={false} hide />
                  <YAxis type="category" dataKey="position" width={132} tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 10, borderColor: "hsl(var(--border))", fontSize: 12 }} />
                  <Bar dataKey="candidates" name="Applications" fill={chartColors.primary} radius={[0, 6, 6, 0]} maxBarSize={22}>
                    <LabelList dataKey="candidates" position="right" fill="hsl(var(--foreground))" fontSize={10} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyChart>No position data in this cohort.</EmptyChart>}
        </Panel>

        <Panel title="Stage time and SLA" description="Historical stage entries for the selected application cohort." icon={<Clock3 className="h-4 w-4 text-primary" />} className="xl:col-span-6">
          <div className="divide-y divide-border/70">
            {data.time_in_stage.length ? data.time_in_stage.map((item) => {
              const target = Number(item.sla_target_days || 0);
              const ratio = target ? Math.min(100, Number(item.average_days || 0) / target * 100) : 0;
              return (
                <div key={item.stage} className="grid gap-2 px-3 py-1.5 sm:grid-cols-[minmax(120px,1fr)_minmax(120px,1.2fr)_auto] sm:items-center">
                  <div>
                    <p className="text-xs font-semibold">{stageLabels[item.stage] || humanize(item.stage)}</p>
                    <p className="text-[11px] text-muted-foreground">{item.entries} stage entries</p>
                  </div>
                  <div>
                    <div className="mb-1 flex justify-between text-[10px] text-muted-foreground"><span>{item.average_days ?? 0}d average</span><span>{target ? `${target}d target` : "No SLA"}</span></div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${ratio > 100 ? "bg-destructive" : ratio >= 75 ? "bg-amber-500" : "bg-success"}`} style={{ width: `${target ? Math.max(4, ratio) : 0}%` }} /></div>
                  </div>
                  <span className={`inline-flex min-h-8 items-center justify-center rounded-full px-2 text-[10px] font-semibold ${item.sla_breaches ? "bg-destructive/8 text-destructive" : "bg-success/10 text-success"}`}>{item.sla_breaches ? `${item.sla_breaches} late` : "On track"}</span>
                </div>
              );
            }) : <EmptyChart>No stage-time data in this cohort.</EmptyChart>}
          </div>
        </Panel>

        <Panel title="Source quality" description="Subsource-level shortlisting and Active Teacher conversion." icon={<TrendingUp className="h-4 w-4 text-primary" />} className="xl:col-span-6">
          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full min-w-[540px] text-left text-xs">
              <thead className="bg-muted/45 text-[10px] uppercase tracking-wide text-muted-foreground"><tr><th className="px-3 py-1.5">Source</th><th className="px-3 py-1.5">Applicants</th><th className="px-3 py-1.5">Shortlisted</th><th className="px-3 py-1.5">Active Teachers</th><th className="px-3 py-1.5">Conversion</th></tr></thead>
              <tbody className="divide-y divide-border/70">
                {data.source_quality.slice(0, 10).map((item) => <tr key={`${item.source}:${item.subsource}`} className="hover:bg-muted/25"><td className="px-3 py-1.5"><strong className="block">{item.source}</strong><span className="text-[10px] text-muted-foreground">{item.subsource}</span></td><td className="px-3 py-1.5 tabular-nums">{item.candidates}</td><td className="px-3 py-1.5 tabular-nums">{item.shortlisted}</td><td className="px-3 py-1.5 tabular-nums">{item.hired}</td><td className="px-3 py-1.5 font-semibold tabular-nums">{item.conversion_percentage ?? 0}%</td></tr>)}
              </tbody>
            </table>
          </div>
          <div className="divide-y divide-border/70 sm:hidden">
            {data.source_quality.slice(0, 10).map((item) => <div key={`${item.source}:${item.subsource}`} className="px-3 py-1.5 text-xs"><div className="flex justify-between gap-2"><strong>{item.source} · {item.subsource}</strong><strong>{item.conversion_percentage ?? 0}%</strong></div><p className="mt-1 text-muted-foreground">{item.candidates} applicants · {item.shortlisted} shortlisted · {item.hired} hired</p></div>)}
          </div>
          {!data.source_quality.length ? <EmptyChart>No source-quality data in this cohort.</EmptyChart> : null}
        </Panel>

        <Panel title={roleIsHr ? "Operational attention" : "Executive attention"} description={roleIsHr ? "Live work across the current pipeline; the cohort date does not limit this panel." : "Read-only live overview across the current pipeline."} icon={<CalendarClock className="h-4 w-4 text-primary" />} className="h-full xl:col-span-5">
          <div className="grid gap-2 p-2 sm:grid-cols-2 xl:h-[272px] xl:grid-cols-1 xl:overflow-y-auto 2xl:grid-cols-2">
            <div>
              <p className="sticky top-0 z-10 mb-2 flex items-center justify-between bg-card py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground"><span>Overdue actions</span><span className="rounded-full bg-destructive/8 px-2 py-1 text-destructive">{data.overdue_actions.length}</span></p>
              <div className="space-y-1">
                {data.overdue_actions.slice(0, 5).map((item) => {
                  const content = <><span className="min-w-0"><strong className="block truncate">{item.candidate_name}</strong><span className="block truncate text-[11px] text-muted-foreground">{item.title} · {dateLabel(item.due_at)}</span></span>{roleIsHr ? <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" /> : null}</>;
                  return roleIsHr ? <a key={item.id} href={`${basePath}/candidates/${item.candidate_id}`} className="flex min-h-12 items-center justify-between gap-2 rounded-lg px-2 text-xs hover:bg-muted/55 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">{content}</a> : <div key={item.id} className="flex min-h-12 items-center gap-2 rounded-lg px-2 text-xs">{content}</div>;
                })}
                {!data.overdue_actions.length ? <p className="rounded-lg border border-dashed border-border px-3 py-3 text-xs text-muted-foreground">No overdue actions.</p> : null}
              </div>
            </div>
            <div>
              <p className="sticky top-0 z-10 mb-2 flex items-center justify-between bg-card py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground"><span>Upcoming</span><span className="rounded-full bg-primary/8 px-2 py-1 text-primary">{data.upcoming_appointments.length}</span></p>
              <div className="space-y-1">
                {data.upcoming_appointments.slice(0, 5).map((item) => {
                  const content = <><span className="min-w-0"><strong className="block truncate">{item.candidate_name}</strong><span className="block truncate text-[11px] text-muted-foreground">{humanize(item.appointment_type)} · {dateLabel(item.starts_at)}</span></span>{roleIsHr ? <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" /> : null}</>;
                  return roleIsHr ? <a key={item.id} href={`${basePath}/candidates/${item.candidate_id}?tab=evaluations`} className="flex min-h-12 items-center justify-between gap-2 rounded-lg px-2 text-xs hover:bg-muted/55 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">{content}</a> : <div key={item.id} className="flex min-h-12 items-center gap-2 rounded-lg px-2 text-xs">{content}</div>;
                })}
                {!data.upcoming_appointments.length ? <p className="rounded-lg border border-dashed border-border px-3 py-3 text-xs text-muted-foreground">No upcoming appointments.</p> : null}
              </div>
            </div>
          </div>
        </Panel>

        <Panel title={`Recent candidates · ${selectedPeriod}`} description="Latest application-cohort candidates" icon={<UsersRound className="h-4 w-4 text-primary" />} className="h-full xl:col-span-7">
          <div className="no-scrollbar hidden h-[272px] overflow-x-hidden overflow-y-auto md:block">
            <table className="w-full table-fixed text-left text-xs">
              <colgroup>
                <col className="w-[19%]" />
                <col className="w-[17%]" />
                <col className="w-[10%]" />
                <col className="w-[13%]" />
                <col className="w-[18%]" />
                <col className="w-[23%]" />
              </colgroup>
              <thead className="sticky top-0 z-10 bg-muted text-[10px] uppercase tracking-wide text-muted-foreground"><tr><th className="px-2 py-1.5">Candidate</th><th className="px-2 py-1.5">Position</th><th className="px-2 py-1.5">Source</th><th className="px-2 py-1.5">Applied</th><th className="px-2 py-1.5">Stage</th><th className="px-2 py-1.5">Next action</th></tr></thead>
              <tbody className="divide-y divide-border/70">
                {data.recent_candidates.map((item) => <tr key={item.id} className="h-12 hover:bg-muted/25"><td className="px-2 py-1"><a href={`${basePath}/candidates/${item.id}`} className="inline-flex min-h-10 max-w-full items-center break-words font-semibold leading-tight hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30">{item.full_name}</a></td><td className="truncate px-2 py-1">{item.position}</td><td className="px-2 py-1 leading-tight"><span className="block truncate">{item.source}</span>{item.subsource ? <span className="block truncate text-[10px] text-muted-foreground">{item.subsource}</span> : null}</td><td className="truncate px-2 py-1">{dateLabel(item.application_date)}</td><td className="truncate px-2 py-1">{stageLabels[item.status] || humanize(item.status)}</td><td className="truncate px-2 py-1">{item.next_action || "—"}</td></tr>)}
              </tbody>
            </table>
          </div>
          <div className="no-scrollbar max-h-[300px] divide-y divide-border/70 overflow-y-auto md:hidden">
            {data.recent_candidates.map((item) => <a key={item.id} href={`${basePath}/candidates/${item.id}`} className="block min-h-[60px] px-3 py-1.5 hover:bg-muted/35 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/30"><div className="flex items-start justify-between gap-2"><strong className="truncate text-xs">{item.full_name}</strong><span className="shrink-0 text-[10px] font-semibold text-primary">{stageLabels[item.status] || humanize(item.status)}</span></div><p className="mt-0.5 truncate text-[11px] text-muted-foreground">{item.position} · {item.source}{item.subsource ? ` / ${item.subsource}` : ""}</p><p className="mt-0.5 truncate text-[10px] text-muted-foreground">{dateLabel(item.application_date)} · {item.next_action || "No next action"}</p></a>)}
          </div>
          {!data.recent_candidates.length ? <EmptyChart>No recent candidates in this cohort.</EmptyChart> : null}
        </Panel>

        <Panel title="Recent activity" description="Actor-attributed events that occurred within the selected dates." icon={<Activity className="h-4 w-4 text-primary" />} className="xl:col-span-12">
          <ol className="grid gap-px bg-border/70 sm:grid-cols-2 xl:grid-cols-3">
            {data.recent_activity.map((item) => (
              <li key={item.id} className="flex min-h-[68px] gap-2 bg-card px-3 py-1.5">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/8 text-primary"><Activity className="h-4 w-4" /></span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold">{activityLabel(item.event_type)}</p>
                  <a href={`${basePath}/candidates/${item.candidate_id}`} className="mt-0.5 block truncate text-xs text-primary hover:underline">{item.candidate_name}</a>
                  <p className="mt-1 text-[10px] text-muted-foreground">{item.actor} · {dateLabel(item.created_at)}</p>
                </div>
              </li>
            ))}
          </ol>
          {!data.recent_activity.length ? <EmptyChart>No recent recruitment activity in this period.</EmptyChart> : null}
        </Panel>
      </div>

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
