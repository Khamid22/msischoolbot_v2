import { AlertTriangle, CalendarClock, Clock3, Filter, Loader2, TrendingUp, UsersRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type ReactNode } from "react";

import { recruitmentRequest } from "@/features/recruitment/api";
import { dateLabel, humanize, type HrAnalyticsDashboard } from "@/features/recruitment/model";
import { PageState, fieldClass, queryError, replaceUrlParams } from "@/features/recruitment/ui";

type Options = { sources: Array<{ id: number; label: string }>; positions: string[]; subjects: Array<{ id: number; name: string }>; responsible_people: Array<{ id: number; name: string }> };
const api = "/api/v1/hr/analytics";
const keys = ["date_from", "date_to", "source", "position", "subject_id", "responsible_account_id"] as const;

function initialFilters() {
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(keys.map((key) => [key, params.get(key) || ""])) as Record<(typeof keys)[number], string>;
}

function Metric({ label, value, icon }: { label: string; value: string | number; icon: ReactNode }) {
  return <article className="rounded-xl border border-border bg-card p-3 shadow-sm"><div className="flex items-center justify-between gap-2"><p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p><span className="text-primary">{icon}</span></div><p className="mt-2 text-2xl font-bold tracking-tight">{value}</p></article>;
}

export function AnalyticsView({ basePath }: { basePath: string }) {
  const [filters, setFilters] = useState(initialFilters);
  const options = useQuery({ queryKey: ["hr-analytics", "options"], queryFn: () => recruitmentRequest<Options>(`${api}/options`) });
  const params = useMemo(() => {
    const value = new URLSearchParams();
    Object.entries(filters).forEach(([key, entry]) => { if (entry) value.set(key, entry); });
    return value;
  }, [filters]);
  const dashboard = useQuery({ queryKey: ["hr-analytics", "dashboard", params.toString()], queryFn: () => recruitmentRequest<HrAnalyticsDashboard>(`${api}/dashboard${params.size ? `?${params}` : ""}`) });
  const update = (key: keyof typeof filters, value: string) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    replaceUrlParams(next);
  };
  if (dashboard.isLoading) return <PageState><span className="inline-flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Loading HR analytics…</span></PageState>;
  if (dashboard.error || !dashboard.data) return <PageState tone="error">{queryError(dashboard.error)}</PageState>;
  const data = dashboard.data;
  const funnelMax = Math.max(1, ...data.funnel.map((item) => Number(item.candidates || 0)));
  return <div className="space-y-3">
    <section className="rounded-xl border border-border bg-card p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground"><Filter className="h-4 w-4" />Dashboard filters · {data.range.timezone}</div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
        <label className="text-[11px] font-semibold">From<input type="date" value={filters.date_from || data.range.from} onChange={(event) => update("date_from", event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className="text-[11px] font-semibold">To<input type="date" value={filters.date_to || data.range.to} onChange={(event) => update("date_to", event.target.value)} className={`${fieldClass} mt-1`} /></label>
        <label className="text-[11px] font-semibold">Source<select value={filters.source} onChange={(event) => update("source", event.target.value)} className={`${fieldClass} mt-1`}><option value="">All</option>{options.data?.sources.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <label className="text-[11px] font-semibold">Position<select value={filters.position} onChange={(event) => update("position", event.target.value)} className={`${fieldClass} mt-1`}><option value="">All</option>{options.data?.positions.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="text-[11px] font-semibold">Subject<select value={filters.subject_id} onChange={(event) => update("subject_id", event.target.value)} className={`${fieldClass} mt-1`}><option value="">All</option>{options.data?.subjects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label className="text-[11px] font-semibold">Responsible<select value={filters.responsible_account_id} onChange={(event) => update("responsible_account_id", event.target.value)} className={`${fieldClass} mt-1`}><option value="">All</option>{options.data?.responsible_people.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      </div>
    </section>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Metric label="Active candidates" value={data.kpis.active_candidates || 0} icon={<UsersRound className="h-4 w-4" />} />
      <Metric label="New this month" value={data.kpis.new_this_month || 0} icon={<TrendingUp className="h-4 w-4" />} />
      <Metric label="Hired this month" value={data.kpis.hired_this_month || 0} icon={<UsersRound className="h-4 w-4" />} />
      <Metric label="Average time to hire" value={`${data.kpis.average_time_to_hire_days ?? 0}d`} icon={<Clock3 className="h-4 w-4" />} />
      <Metric label="Overall conversion" value={`${data.kpis.overall_conversion_percentage ?? 0}%`} icon={<TrendingUp className="h-4 w-4" />} />
    </div>
    <div className="grid gap-3 xl:grid-cols-2">
      <section className="rounded-xl border border-border bg-card p-3"><h2 className="text-sm font-semibold">Recruitment funnel</h2><div className="mt-3 space-y-2">{data.funnel.length ? data.funnel.map((item) => <div key={item.stage}><div className="mb-1 flex justify-between text-xs"><span>{humanize(item.stage)}{item.conversion_percentage !== null && item.conversion_percentage !== undefined ? ` · ${item.conversion_percentage}% from prior stage` : ""}</span><strong>{item.candidates}</strong></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Number(item.candidates) / funnelMax * 100}%` }} /></div></div>) : <p className="text-sm text-muted-foreground">No stage activity in this period.</p>}</div></section>
      <section className="rounded-xl border border-border bg-card p-3"><div className="flex items-center justify-between"><h2 className="text-sm font-semibold">Stage time and SLA</h2><span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-700"><AlertTriangle className="h-3.5 w-3.5" />{data.sla.breaches} breaches</span></div><div className="mt-3 divide-y divide-border">{data.time_in_stage.map((item) => <div key={item.stage} className="grid grid-cols-[1fr_auto_auto] gap-3 py-2 text-xs"><span className="font-medium">{humanize(item.stage)}</span><span>{item.average_days ?? 0} days</span><span className={item.sla_breaches ? "font-semibold text-red-600" : "text-muted-foreground"}>{item.sla_breaches} late</span></div>)}</div></section>
      <section className="rounded-xl border border-border bg-card p-3"><h2 className="text-sm font-semibold">Source conversion</h2><div className="mt-3 divide-y divide-border">{data.source_conversion.map((item) => <div key={item.source} className="grid grid-cols-[1fr_auto_auto] gap-3 py-2 text-xs"><span className="font-medium">{item.source}</span><span>{item.hired}/{item.candidates} hired</span><strong>{item.conversion_percentage ?? 0}%</strong></div>)}</div></section>
      <section className="rounded-xl border border-border bg-card p-3"><h2 className="flex items-center gap-2 text-sm font-semibold"><CalendarClock className="h-4 w-4" />Operational attention</h2><div className="mt-3 grid gap-3 sm:grid-cols-2"><div><p className="mb-2 text-[11px] font-semibold uppercase text-muted-foreground">Overdue actions</p>{data.overdue_actions.slice(0, 5).map((item) => <a key={item.id} href={`${basePath}/candidates/${item.candidate_id}`} className="block border-b border-border py-2 text-xs hover:text-primary"><strong className="block truncate">{item.candidate_name}</strong>{item.title} · {dateLabel(item.due_at)}</a>)}</div><div><p className="mb-2 text-[11px] font-semibold uppercase text-muted-foreground">Upcoming appointments</p>{data.upcoming_appointments.slice(0, 5).map((item) => <a key={item.id} href={`${basePath}/candidates/${item.candidate_id}?tab=evaluations`} className="block border-b border-border py-2 text-xs hover:text-primary"><strong className="block truncate">{item.candidate_name}</strong>{humanize(item.appointment_type)} · {dateLabel(item.starts_at)}</a>)}</div></div></section>
    </div>
  </div>;
}
