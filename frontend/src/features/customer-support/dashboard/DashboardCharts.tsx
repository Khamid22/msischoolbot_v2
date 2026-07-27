import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ReactNode } from "react";
import type {
  CustomerSupportDailyTicketFlow,
  CustomerSupportSchoolWorkload,
  CustomerSupportTicketAgeBucket,
  CustomerSupportTicketCategoryVolume,
} from "@/features/customer-support/model";

function categoryLabel(value: string) {
  return value.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function dayLabel(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
    new Date(`${value}T00:00:00`),
  );
}

function ChartCard({
  title,
  description,
  summary,
  children,
  table,
}: {
  title: string;
  description: string;
  summary: string;
  children: ReactNode;
  table: ReactNode;
}) {
  return (
    <section className="min-w-0 rounded-lg border border-border bg-card p-4 shadow-card">
      <header>
        <h2 className="text-base font-black text-foreground">{title}</h2>
        <p className="mt-1 text-sm leading-5 text-muted-foreground">{description}</p>
        <p className="sr-only">{summary}</p>
      </header>
      <div className="mt-4 h-64 min-w-0" aria-label={summary} role="img">
        {children}
      </div>
      <details className="mt-3 rounded-md border border-border bg-muted/40">
        <summary className="cursor-pointer px-3 py-2 text-xs font-black text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35">
          View chart data
        </summary>
        <div className="miniapp-table-scroll border-t border-border">{table}</div>
      </details>
    </section>
  );
}

function DataTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: Array<Array<string | number>>;
}) {
  return (
    <table className="w-full min-w-[24rem] text-left text-xs">
      <thead>
        <tr className="text-muted-foreground">
          {headers.map((header) => (
            <th key={header} scope="col" className="px-3 py-2 font-black">{header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={`${row[0]}-${rowIndex}`} className="border-t border-border/70">
            {row.map((cell, cellIndex) => (
              <td key={`${cellIndex}-${cell}`} className="px-3 py-2 font-semibold tabular-nums">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function TicketFlowChart({ data }: { data: CustomerSupportDailyTicketFlow[] }) {
  const totalOpened = data.reduce((total, item) => total + item.opened, 0);
  const totalResolved = data.reduce((total, item) => total + item.resolved, 0);
  const summary = `${totalOpened} tickets opened and ${totalResolved} resolved during this period.`;
  return (
    <ChartCard
      title="Ticket flow"
      description="Daily opened versus resolved parent tickets."
      summary={summary}
      table={(
        <DataTable
          headers={["Day", "Opened", "Resolved"]}
          rows={data.map((item) => [dayLabel(item.day), item.opened, item.resolved])}
        />
      )}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 4 }} accessibilityLayer>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="day" tickFormatter={dayLabel} minTickGap={24} tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} width={36} tick={{ fontSize: 11 }} />
          <Tooltip labelFormatter={dayLabel} />
          <Legend />
          <Line
            type="monotone"
            dataKey="opened"
            name="Opened"
            stroke="hsl(var(--primary))"
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="resolved"
            name="Resolved"
            stroke="hsl(var(--success))"
            strokeDasharray="6 4"
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function TicketAgeChart({ data }: { data: CustomerSupportTicketAgeBucket[] }) {
  const oldest = data.at(-1)?.count || 0;
  return (
    <ChartCard
      title="Open-ticket age"
      description="How long unresolved tickets have remained open."
      summary={`${oldest} unresolved tickets are eight days old or older.`}
      table={(
        <DataTable
          headers={["Age", "Tickets"]}
          rows={data.map((item) => [item.label, item.count])}
        />
      )}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 36, left: 14, bottom: 4 }} accessibilityLayer>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" allowDecimals={false} />
          <YAxis type="category" dataKey="label" width={52} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="count" name="Tickets" fill="hsl(var(--warning))" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            <LabelList dataKey="count" position="right" className="fill-foreground text-[0.6875rem]" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function TicketCategoryChart({ data }: { data: CustomerSupportTicketCategoryVolume[] }) {
  const chartData = data.slice(0, 10).map((item) => ({
    ...item,
    label: categoryLabel(item.category),
  }));
  const leading = chartData[0];
  return (
    <ChartCard
      title="Tickets by category"
      description="New tickets created during the selected period."
      summary={leading ? `${leading.label} is the largest category with ${leading.count} tickets.` : "No tickets were created in this period."}
      table={(
        <DataTable
          headers={["Category", "Tickets"]}
          rows={chartData.map((item) => [item.label, item.count])}
        />
      )}
    >
      {chartData.length ? (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 36, left: 28, bottom: 4 }} accessibilityLayer>
            <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="label" width={92} tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="count" name="Tickets" fill="hsl(var(--info))" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              <LabelList dataKey="count" position="right" className="fill-foreground text-[0.6875rem]" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex h-full items-center justify-center rounded-md border border-dashed border-border bg-muted/30 px-6 text-center text-sm font-semibold text-muted-foreground">
          No tickets were created during this period.
        </div>
      )}
    </ChartCard>
  );
}

export function SchoolWorkloadChart({ data }: { data: CustomerSupportSchoolWorkload[] }) {
  const busiest = data[0];
  return (
    <ChartCard
      title="Workload by school"
      description="Open, unassigned, and SLA-breached tickets."
      summary={busiest ? `${busiest.schoolName} has the largest open workload at ${busiest.openTickets} tickets.` : "No school workload is available."}
      table={(
        <DataTable
          headers={["School", "Open", "Unassigned", "SLA breached"]}
          rows={data.map((item) => [
            item.schoolName,
            item.openTickets,
            item.unassignedTickets,
            item.slaBreachedTickets,
          ])}
        />
      )}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 28 }} accessibilityLayer>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="schoolName" interval={0} angle={-20} textAnchor="end" height={52} tick={{ fontSize: 10 }} />
          <YAxis allowDecimals={false} width={36} />
          <Tooltip />
          <Legend />
          <Bar dataKey="openTickets" name="Open" fill="hsl(var(--primary))" isAnimationActive={false} />
          <Bar dataKey="unassignedTickets" name="Unassigned" fill="hsl(var(--warning))" isAnimationActive={false} />
          <Bar dataKey="slaBreachedTickets" name="SLA breached" fill="hsl(var(--destructive))" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
