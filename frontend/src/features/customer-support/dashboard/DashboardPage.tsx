import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CircleDollarSign,
  Inbox,
  Link2Off,
  RefreshCw,
  ShieldCheck,
  TicketCheck,
  UserCheck,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import {
  getSupport,
  type CustomerSupportDashboard,
} from "@/features/customer-support/api";
import {
  SchoolWorkloadChart,
  TicketAgeChart,
  TicketCategoryChart,
  TicketFlowChart,
} from "@/features/customer-support/dashboard/DashboardCharts";
import {
  ActionRequiredPanel,
  ExceptionPanels,
  OldestTicketsPanel,
  RecentActivityPanel,
} from "@/features/customer-support/dashboard/DashboardPanels";
import { inputClass, secondaryButton } from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import { MetricGrid } from "@/shared/ui/MetricGrid";
import { PageHeader } from "@/shared/ui/PageHeader";

type DashboardPeriod = 7 | 30 | 90;

function initialFilters() {
  const params = new URLSearchParams(window.location.search);
  const requestedPeriod = Number(params.get("period"));
  return {
    period: ([7, 30, 90].includes(requestedPeriod) ? requestedPeriod : 30) as DashboardPeriod,
    schoolId: params.get("schoolId") || "",
  };
}

function MetricLink({
  label,
  value,
  detail,
  href,
  icon,
  tone = "default",
}: {
  label: string;
  value: number;
  detail: string;
  href: string;
  icon: ReactNode;
  tone?: "default" | "danger" | "warning";
}) {
  const toneClass = tone === "danger"
    ? "border-destructive/25 bg-destructive/5 text-destructive"
    : tone === "warning"
      ? "border-warning/35 bg-warning/10 text-warning-foreground"
      : "border-border bg-card text-primary";
  return (
    <a
      href={href}
      className={`group min-w-0 rounded-lg border p-3 shadow-sm hover:shadow-card focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 ${toneClass}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background/80 shadow-sm">
          {icon}
        </span>
        <span className="text-2xl font-black tabular-nums text-foreground">{value}</span>
      </div>
      <p className="mt-3 text-sm font-black text-foreground">{label}</p>
      <p className="mt-1 text-xs font-semibold leading-5 text-muted-foreground">{detail}</p>
    </a>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading operational dashboard">
      <span className="sr-only">Loading operational dashboard</span>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className="h-32 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
        ))}
      </div>
      <div className="h-80 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="h-72 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
        <div className="h-72 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
      </div>
    </div>
  );
}

export function DashboardPage({
  authLogin,
  title,
  description,
}: {
  authLogin: string;
  title: string;
  description: string;
}) {
  const initial = initialFilters();
  const [period, setPeriod] = useState<DashboardPeriod>(initial.period);
  const [schoolId, setSchoolId] = useState(initial.schoolId);
  const dashboard = useQuery({
    queryKey: ["customer-support", "dashboard", period, schoolId],
    queryFn: ({ signal }) => {
      const params = new URLSearchParams({ period: String(period) });
      if (schoolId) params.set("schoolId", schoolId);
      return getSupport<CustomerSupportDashboard>(`/dashboard?${params}`, signal);
    },
  });

  useEffect(() => {
    const params = new URLSearchParams();
    if (period !== 30) params.set("period", String(period));
    if (schoolId) params.set("schoolId", schoolId);
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${params.size ? `?${params}` : ""}`,
    );
  }, [period, schoolId]);

  const data = dashboard.data;
  const generatedAt = data?.generatedAt
    ? new Intl.DateTimeFormat(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(new Date(data.generatedAt))
    : "";

  return (
    <div className="flex min-w-0 flex-col gap-4 overflow-x-hidden">
      <PageHeader
        title={title}
        subtitle={description || "What requires attention now across your assigned schools."}
        badge={(
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase tracking-wide text-primary">
            Operations
          </span>
        )}
        actions={authLogin ? (
          <span className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground">
            <ShieldCheck className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
            <span className="truncate">{authLogin}</span>
          </span>
        ) : undefined}
      />

      <section className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3 shadow-sm lg:flex-row lg:items-end lg:justify-between">
        <div className="grid min-w-0 gap-3 sm:grid-cols-2">
          <label className="min-w-0">
            <span className="mb-1 block text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">School</span>
            <select
              value={schoolId}
              onChange={(event) => setSchoolId(event.target.value)}
              className={`${inputClass} min-w-0 sm:w-64`}
              disabled={dashboard.isLoading}
            >
              <option value="">All assigned schools</option>
              {data?.availableSchools.map((school) => (
                <option key={school.schoolId} value={school.schoolId}>{school.schoolName}</option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend className="mb-1 text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">Period</legend>
            <div className="flex rounded-lg border border-border bg-muted p-1">
              {([7, 30, 90] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setPeriod(value)}
                  aria-pressed={period === value}
                  className={`min-h-9 min-w-14 rounded-md px-3 text-xs font-black focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 ${
                    period === value ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {value}d
                </button>
              ))}
            </div>
          </fieldset>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 lg:justify-end">
          <p className="text-xs font-semibold text-muted-foreground" aria-live="polite">
            {dashboard.isFetching ? "Refreshing data…" : generatedAt ? `Updated ${generatedAt}` : "Waiting for data"}
          </p>
          <button
            type="button"
            className={secondaryButton}
            disabled={dashboard.isFetching}
            onClick={() => void dashboard.refetch()}
          >
            <RefreshCw className={`h-4 w-4 ${dashboard.isFetching ? "animate-spin motion-reduce:animate-none" : ""}`} aria-hidden="true" />
            Refresh
          </button>
        </div>
      </section>

      {dashboard.isLoading ? <DashboardSkeleton /> : dashboard.isError || !data ? (
        <EmptyState
          title="Operational dashboard unavailable"
          detail={dashboard.error instanceof Error
            ? `${dashboard.error.message} Check your school assignment or try again.`
            : "The dashboard could not be loaded. Check your school assignment or try again."}
          icon={<AlertTriangle className="h-5 w-5" />}
          action={(
            <button type="button" className={secondaryButton} onClick={() => void dashboard.refetch()}>
              Try again
            </button>
          )}
        />
      ) : (
        <>
          <MetricGrid className="lg:grid-cols-3 xl:grid-cols-6">
            <MetricLink
              label="Open tickets"
              value={data.metrics.openTickets}
              detail="All unresolved requests"
              href="/customer-support/tickets"
              icon={<Inbox className="h-5 w-5" aria-hidden="true" />}
            />
            <MetricLink
              label="Assigned to me"
              value={data.metrics.assignedToMe}
              detail="Your active workload"
              href="/customer-support/tickets?assignedToMe=true"
              icon={<UserCheck className="h-5 w-5" aria-hidden="true" />}
            />
            <MetricLink
              label="Unassigned"
              value={data.metrics.unassignedTickets}
              detail="Needs an owner"
              href="/customer-support/tickets?unassigned=true"
              icon={<TicketCheck className="h-5 w-5" aria-hidden="true" />}
              tone="warning"
            />
            <MetricLink
              label="SLA breached"
              value={data.metrics.slaBreachedTickets}
              detail="Response or resolution overdue"
              href="/customer-support/tickets?slaState=breached"
              icon={<AlertTriangle className="h-5 w-5" aria-hidden="true" />}
              tone="danger"
            />
            <MetricLink
              label="Overdue accounts"
              value={data.metrics.overduePaymentAccounts}
              detail="Payment action required"
              href={data.paymentExceptions.topOverdueAccounts[0]
                ? `/customer-support/students?recordId=${data.paymentExceptions.topOverdueAccounts[0].studentId}`
                : "/customer-support/students"}
              icon={<CircleDollarSign className="h-5 w-5" aria-hidden="true" />}
              tone="warning"
            />
            <MetricLink
              label="No parent link"
              value={data.metrics.studentsWithoutActiveParentLink}
              detail="Active students without access"
              href={data.accountExceptions.studentsWithoutActiveParentLink[0]
                ? `/customer-support/students?recordId=${data.accountExceptions.studentsWithoutActiveParentLink[0].studentId}`
                : "/customer-support/students"}
              icon={<Link2Off className="h-5 w-5" aria-hidden="true" />}
              tone="warning"
            />
          </MetricGrid>

          <ActionRequiredPanel
            tickets={data.actionRequiredTickets}
            escalatedCount={data.metrics.escalatedTickets}
            waitingCount={data.metrics.waitingOnRequesterTickets}
          />

          <ExceptionPanels
            overdueTotals={data.paymentExceptions.overdueTotals}
            dueSoonTotals={data.paymentExceptions.dueSoonTotals}
            payments={data.paymentExceptions.topOverdueAccounts}
            students={data.accountExceptions.studentsWithoutActiveParentLink}
          />

          <div className="grid min-w-0 gap-4 xl:grid-cols-2">
            <TicketFlowChart data={data.dailyTicketFlow} />
            <TicketAgeChart data={data.ticketAgeBuckets} />
            <TicketCategoryChart data={data.ticketCategories} />
            {data.schoolWorkload.length > 1 ? <SchoolWorkloadChart data={data.schoolWorkload} /> : null}
          </div>

          <div className="grid min-w-0 gap-4 xl:grid-cols-2">
            <OldestTicketsPanel tickets={data.oldestOpenTickets} />
            <RecentActivityPanel activity={data.recentActivity} />
          </div>
        </>
      )}
    </div>
  );
}
