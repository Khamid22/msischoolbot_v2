import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  ChevronRight,
  Inbox,
  Loader2,
  Plus,
  Search,
  ShieldCheck,
  TicketCheck,
} from "lucide-react";
import { FormEvent, useState } from "react";
import {
  getSupport,
  type SupportContext,
  type SupportTicketQueue,
  type SupportTicketStatus,
} from "@/features/customer-support/api";
import { inputClass } from "@/features/customer-support/shared/ui";
import { TicketDetailPanel } from "@/features/customer-support/tickets/TicketDetailPanel";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const TICKET_STATUSES: Array<{ value: "" | SupportTicketStatus; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "new", label: "New" },
  { value: "in_progress", label: "In progress" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
];
const SUPPORT_TICKET_PAGE_SIZE = 25;

export function TicketsPage({
  authLogin,
  title,
  description,
  csrfToken,
}: {
  authLogin: string;
  title: string;
  description: string;
  csrfToken: string;
}) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<"" | SupportTicketStatus>("");
  const [schoolId, setSchoolId] = useState("");
  const context = useQuery({
    queryKey: ["customer-support", "context"],
    queryFn: ({ signal }) => getSupport<SupportContext>("/context", signal),
  });
  const queue = useInfiniteQuery({
    queryKey: ["customer-support", "tickets", search, status, schoolId],
    initialPageParam: "",
    queryFn: ({ signal, pageParam }) => {
      const params = new URLSearchParams({
        limit: String(SUPPORT_TICKET_PAGE_SIZE),
      });
      if (search) params.set("q", search);
      if (status) params.set("status", status);
      if (schoolId) params.set("schoolId", schoolId);
      if (pageParam) params.set("cursor", pageParam);
      return getSupport<SupportTicketQueue>(`/tickets?${params}`, signal);
    },
    getNextPageParam: (lastPage) => lastPage.nextCursor || undefined,
  });
  const tickets = queue.data?.pages.flatMap((page) => page.items) || [];
  const actorStaffId = queue.data?.pages[0]?.actorStaffId || null;

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchInput.trim());
    setSelectedId(null);
  }

  return (
    <div className="flex min-w-0 flex-col gap-4 overflow-x-hidden">
      <PageHeader
        title={title}
        subtitle={description}
        badge={(
          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[0.6875rem] font-black uppercase tracking-wide text-primary">
            Customer Support
          </span>
        )}
        actions={authLogin ? (
          <span className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
            <span className="truncate">{authLogin}</span>
          </span>
        ) : undefined}
      />

      <form
        onSubmit={submitSearch}
        className="grid gap-3 rounded-lg border border-border bg-card p-3 shadow-sm sm:grid-cols-[minmax(0,1fr)_12rem_12rem_auto]"
      >
        <label className="relative min-w-0">
          <span className="sr-only">Search tickets</span>
          <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            className={`${inputClass} pl-10`}
            placeholder="Parent or topic"
            maxLength={200}
          />
        </label>
        <label>
          <span className="sr-only">Ticket status</span>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as "" | SupportTicketStatus);
              setSelectedId(null);
            }}
            className={inputClass}
          >
            {TICKET_STATUSES.map((option) => (
              <option key={option.value || "all"} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr-only">School</span>
          <select
            value={schoolId}
            onChange={(event) => {
              setSchoolId(event.target.value);
              setSelectedId(null);
            }}
            className={inputClass}
            disabled={context.isLoading}
          >
            <option value="">All assigned schools</option>
            {context.data?.schools.map((school) => (
              <option key={school.id} value={school.id}>{school.school_name}</option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
        >
          <Search className="h-4 w-4" />
          Search
        </button>
      </form>

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]">
        <section
          className={`${selectedId ? "hidden lg:flex" : "flex"} min-h-[28rem] min-w-0 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-card lg:max-h-[calc(100dvh-14rem)]`}
          aria-label="Support ticket queue"
        >
          <header className="flex min-h-14 items-center justify-between border-b border-border px-4 py-3">
            <div>
              <h2 className="text-sm font-black">Parent tickets</h2>
              <p className="text-xs font-semibold text-muted-foreground" aria-live="polite">
                {queue.isLoading ? "Loading…" : `${tickets.length} loaded`}
              </p>
            </div>
            {queue.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-primary motion-reduce:animate-none" />
            ) : (
              <Inbox className="h-4 w-4 text-muted-foreground" />
            )}
          </header>
          <div className="miniapp-scroll min-h-0 flex-1 overflow-y-auto">
            {queue.isLoading ? (
              <TicketQueueSkeleton />
            ) : queue.isError ? (
              <EmptyState
                title="Could not load tickets"
                detail={queue.error instanceof Error ? queue.error.message : "Try again."}
                action={(
                  <button
                    type="button"
                    className="min-h-11 rounded-lg border border-border px-4 text-sm font-black"
                    onClick={() => void queue.refetch()}
                  >
                    Try again
                  </button>
                )}
                className="m-4"
              />
            ) : tickets.length ? (
              tickets.map((ticket) => (
                <button
                  key={ticket.ticketId}
                  type="button"
                  onClick={() => setSelectedId(ticket.ticketId)}
                  aria-pressed={selectedId === ticket.ticketId}
                  className={`flex min-h-24 w-full items-start gap-3 border-b border-border px-4 py-3 text-left transition-colors hover:bg-muted/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none ${
                    selectedId === ticket.ticketId ? "bg-primary/8" : "bg-card"
                  }`}
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <TicketCheck className="h-5 w-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-start justify-between gap-2">
                      <span className="break-words text-sm font-black text-foreground">{ticket.topic}</span>
                      <StatusBadge status={ticket.status} className="shrink-0 text-[0.625rem]" />
                    </span>
                    <span className="mt-1 block truncate text-xs font-semibold text-muted-foreground">
                      {ticket.requesterName} · {ticket.schoolName}
                    </span>
                    <span className="mt-2 block text-xs font-bold text-muted-foreground">
                      {ticket.assignedStaffName || "Unassigned"} · {ticket.replyCount} replies
                    </span>
                  </span>
                  <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-muted-foreground" />
                </button>
              ))
            ) : (
              <EmptyState
                title="No matching tickets"
                detail="New parent requests in your assigned schools will appear here."
                icon={<TicketCheck className="h-5 w-5" />}
                className="m-4"
              />
            )}
          </div>
          {queue.hasNextPage ? (
            <footer className="border-t border-border p-3">
              <button
                type="button"
                onClick={() => void queue.fetchNextPage()}
                disabled={queue.isFetchingNextPage}
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-border bg-background px-4 text-sm font-black text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 disabled:opacity-50"
              >
                {queue.isFetchingNextPage ? (
                  <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Load more
              </button>
            </footer>
          ) : null}
        </section>

        <section className={`${selectedId ? "block" : "hidden lg:block"} min-w-0`}>
          <TicketDetailPanel
            ticketId={selectedId}
            csrfToken={csrfToken}
            currentStaffId={actorStaffId}
            onBack={() => setSelectedId(null)}
          />
        </section>
      </div>
    </div>
  );
}

function TicketQueueSkeleton() {
  return (
    <div className="space-y-px" role="status" aria-label="Loading tickets">
      <span className="sr-only">Loading tickets</span>
      {[1, 2, 3, 4].map((item) => (
        <div
          key={item}
          className="h-24 animate-pulse border-b border-border bg-muted motion-reduce:animate-none"
        />
      ))}
    </div>
  );
}
