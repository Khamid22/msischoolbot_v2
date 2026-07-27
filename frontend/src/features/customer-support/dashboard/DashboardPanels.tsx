import {
  CalendarClock,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  Link2Off,
  MessageSquareMore,
  TicketCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import type {
  CustomerSupportActivity,
  CustomerSupportCurrencyAmount,
  CustomerSupportDashboardTicket,
  CustomerSupportOverduePayment,
  CustomerSupportStudentWithoutParent,
} from "@/features/customer-support/model";
import { formatDate } from "@/features/customer-support/shared/ui";
import { StatusBadge } from "@/shared/ui/StatusBadge";

function words(value: string) {
  return value.split("_").join(" ");
}

function amount(value: number | string, currency: string) {
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(Number(value))} ${currency}`;
}

function priorityClass(priority: CustomerSupportDashboardTicket["priority"]) {
  if (priority === "urgent") return "border-destructive/30 bg-destructive/10 text-destructive";
  if (priority === "high") return "border-warning/40 bg-warning/15 text-warning-foreground";
  return "border-border bg-muted text-muted-foreground";
}

function TicketRow({ ticket }: { ticket: CustomerSupportDashboardTicket }) {
  return (
    <a
      href={`/customer-support/tickets?ticketId=${ticket.ticketId}`}
      className="group grid min-h-16 min-w-0 gap-2 border-t border-border px-4 py-3 first:border-t-0 hover:bg-muted/55 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35 sm:grid-cols-[minmax(0,1fr)_auto]"
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-black text-foreground">{ticket.title}</p>
          <span className={`rounded-full border px-2 py-0.5 text-[0.625rem] font-black uppercase ${priorityClass(ticket.priority)}`}>
            {ticket.priority}
          </span>
          {ticket.slaState === "breached" ? (
            <span className="rounded-full bg-destructive px-2 py-0.5 text-[0.625rem] font-black uppercase text-destructive-foreground">
              SLA breached
            </span>
          ) : null}
        </div>
        <p className="mt-1 truncate text-xs font-semibold text-muted-foreground">
          {ticket.requesterName || "Parent"} · {ticket.schoolName} · {words(ticket.category)}
        </p>
      </div>
      <div className="flex items-center justify-between gap-3 sm:justify-end">
        <StatusBadge status={ticket.status} />
        <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground" aria-hidden="true" />
      </div>
    </a>
  );
}

function Panel({
  title,
  description,
  icon,
  children,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="min-w-0 overflow-hidden rounded-lg border border-border bg-card shadow-card">
      <header className="flex items-start gap-3 border-b border-border px-4 py-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </span>
        <div>
          <h2 className="text-sm font-black text-foreground">{title}</h2>
          <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{description}</p>
        </div>
      </header>
      {children}
    </section>
  );
}

function EmptyPanel({ message }: { message: string }) {
  return <p className="px-4 py-7 text-center text-sm font-semibold text-muted-foreground">{message}</p>;
}

export function ActionRequiredPanel({
  tickets,
  escalatedCount,
  waitingCount,
}: {
  tickets: CustomerSupportDashboardTicket[];
  escalatedCount: number;
  waitingCount: number;
}) {
  return (
    <Panel
      title="Action required"
      description={`${escalatedCount} escalated · ${waitingCount} waiting on parent`}
      icon={<MessageSquareMore className="h-5 w-5" aria-hidden="true" />}
    >
      {tickets.length ? tickets.map((ticket) => <TicketRow key={ticket.ticketId} ticket={ticket} />) : (
        <EmptyPanel message="No open tickets currently require attention." />
      )}
      <a
        href="/customer-support/tickets"
        className="flex min-h-11 items-center justify-center gap-2 border-t border-border px-4 text-sm font-black text-primary hover:bg-primary/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
      >
        Open ticket queue
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </a>
    </Panel>
  );
}

function Totals({ label, totals }: { label: string; totals: CustomerSupportCurrencyAmount[] }) {
  return (
    <div>
      <p className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">{label}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {totals.length ? totals.map((total) => (
          <span key={total.currency} className="rounded-md border border-border bg-muted px-2.5 py-1.5 text-xs font-black tabular-nums text-foreground">
            {amount(total.amount, total.currency)}
            <span className="ml-1 text-muted-foreground">· {total.accountCount}</span>
          </span>
        )) : <span className="text-xs font-semibold text-muted-foreground">None</span>}
      </div>
    </div>
  );
}

export function ExceptionPanels({
  overdueTotals,
  dueSoonTotals,
  payments,
  students,
}: {
  overdueTotals: CustomerSupportCurrencyAmount[];
  dueSoonTotals: CustomerSupportCurrencyAmount[];
  payments: CustomerSupportOverduePayment[];
  students: CustomerSupportStudentWithoutParent[];
}) {
  return (
    <div className="grid min-w-0 gap-4 xl:grid-cols-2">
      <Panel
        title="Payment exceptions"
        description="Unpaid records that are overdue or due within seven days."
        icon={<CircleDollarSign className="h-5 w-5" aria-hidden="true" />}
      >
        <div className="grid gap-3 border-b border-border p-4 sm:grid-cols-2">
          <Totals label="Overdue" totals={overdueTotals} />
          <Totals label="Due soon" totals={dueSoonTotals} />
        </div>
        {payments.length ? payments.map((payment) => (
          <a
            key={payment.paymentId}
            href={`/customer-support/students?recordId=${payment.studentId}`}
            className="group flex min-h-14 items-center gap-3 border-t border-border px-4 py-3 first:border-t-0 hover:bg-muted/55 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
          >
            <CalendarClock className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-black">{payment.studentName}</p>
              <p className="truncate text-xs font-semibold text-muted-foreground">
                {payment.studentCode} · {payment.schoolName} · {payment.daysOverdue}d overdue
              </p>
            </div>
            <span className="shrink-0 text-xs font-black tabular-nums">{amount(payment.amount, payment.currency)}</span>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          </a>
        )) : <EmptyPanel message="No overdue payment accounts in this scope." />}
      </Panel>

      <Panel
        title="Account exceptions"
        description="Active students without an active parent link."
        icon={<Link2Off className="h-5 w-5" aria-hidden="true" />}
      >
        {students.length ? students.map((student) => (
          <a
            key={student.studentId}
            href={`/customer-support/students?recordId=${student.studentId}`}
            className="group flex min-h-14 items-center gap-3 border-t border-border px-4 py-3 first:border-t-0 hover:bg-muted/55 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
          >
            <Link2Off className="h-4 w-4 shrink-0 text-warning-foreground" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-black">{student.studentName}</p>
              <p className="truncate text-xs font-semibold text-muted-foreground">
                {student.studentCode} · {student.schoolName}
              </p>
            </div>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          </a>
        )) : <EmptyPanel message="Every active student has an active parent link." />}
      </Panel>
    </div>
  );
}

export function OldestTicketsPanel({ tickets }: { tickets: CustomerSupportDashboardTicket[] }) {
  return (
    <Panel
      title="Oldest unresolved tickets"
      description="Long-running conversations that may need intervention."
      icon={<Clock3 className="h-5 w-5" aria-hidden="true" />}
    >
      {tickets.length ? tickets.map((ticket) => <TicketRow key={ticket.ticketId} ticket={ticket} />) : (
        <EmptyPanel message="There are no unresolved tickets." />
      )}
    </Panel>
  );
}

export function RecentActivityPanel({ activity }: { activity: CustomerSupportActivity[] }) {
  return (
    <Panel
      title="Recent activity"
      description="Latest ticket and payment changes in the selected scope."
      icon={<TicketCheck className="h-5 w-5" aria-hidden="true" />}
    >
      {activity.length ? activity.map((item) => {
        const href = item.activityType === "ticket"
          ? `/customer-support/tickets?ticketId=${item.entityId}`
          : `/customer-support/students`;
        return (
          <a
            key={item.activityId}
            href={href}
            className="flex min-h-14 items-center gap-3 border-t border-border px-4 py-3 first:border-t-0 hover:bg-muted/55 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/35"
          >
            {item.activityType === "ticket" ? (
              <MessageSquareMore className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            ) : (
              <CircleDollarSign className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-black">{item.summary}</p>
              <p className="truncate text-xs font-semibold text-muted-foreground">
                {words(item.eventType)} · {item.schoolName}
              </p>
            </div>
            <time className="shrink-0 text-[0.6875rem] font-bold text-muted-foreground" dateTime={item.occurredAt}>
              {formatDate(item.occurredAt, true)}
            </time>
          </a>
        );
      }) : <EmptyPanel message="No ticket or payment activity in this period." />}
    </Panel>
  );
}
