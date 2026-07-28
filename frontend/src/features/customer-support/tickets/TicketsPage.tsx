import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  ChevronRight,
  Inbox,
  Loader2,
  Plus,
  TicketCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  getSupport,
  type SupportContext,
  type SupportTicketQueue,
  type SupportTicketPriority,
  type SupportTicketSlaState,
  type SupportTicketStatus,
} from "@/features/customer-support/api";
import { TicketDetailPanel } from "@/features/customer-support/tickets/TicketDetailPanel";
import {
  TicketQueueFilters,
  type TicketQueueFilterValues,
} from "@/features/customer-support/tickets/TicketQueueFilters";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PageHeader } from "@/shared/ui/PageHeader";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const SUPPORT_TICKET_PAGE_SIZE = 25;

function readTicketFilters() {
  const params = new URLSearchParams(window.location.search);
  const assignment: TicketQueueFilterValues["assignment"] =
    params.get("assignedToMe") === "true"
      ? "mine"
      : params.get("unassigned") === "true"
        ? "unassigned"
        : "";
  return {
    selectedId: Number(params.get("ticketId") || 0) || null,
    search: params.get("q") || "",
    status: (params.get("status") || "") as "" | SupportTicketStatus,
    schoolId: params.get("schoolId") || "",
    category: params.get("category") || "",
    priority: (params.get("priority") || "") as "" | SupportTicketPriority,
    slaState: (params.get("slaState") || "") as "" | SupportTicketSlaState,
    assignment,
  };
}

export function TicketsPage({
  title,
  description,
  csrfToken,
}: {
  title: string;
  description: string;
  csrfToken: string;
}) {
  const initial = readTicketFilters();
  const [selectedId, setSelectedId] = useState<number | null>(initial.selectedId);
  const [searchInput, setSearchInput] = useState(initial.search);
  const [search, setSearch] = useState(initial.search);
  const [status, setStatus] = useState<"" | SupportTicketStatus>(initial.status);
  const [schoolId, setSchoolId] = useState(initial.schoolId);
  const [category, setCategory] = useState(initial.category);
  const [priority, setPriority] = useState<"" | SupportTicketPriority>(initial.priority);
  const [slaState, setSlaState] = useState<"" | SupportTicketSlaState>(initial.slaState);
  const [assignment, setAssignment] = useState(initial.assignment);
  const context = useQuery({
    queryKey: ["customer-support", "context"],
    queryFn: ({ signal }) => getSupport<SupportContext>("/context", signal),
  });
  const queue = useInfiniteQuery({
    queryKey: [
      "customer-support",
      "tickets",
      search,
      status,
      schoolId,
      category,
      priority,
      slaState,
      assignment,
    ],
    initialPageParam: "",
    queryFn: ({ signal, pageParam }) => {
      const params = new URLSearchParams({
        limit: String(SUPPORT_TICKET_PAGE_SIZE),
      });
      if (search) params.set("q", search);
      if (status) params.set("status", status);
      if (schoolId) params.set("schoolId", schoolId);
      if (category) params.set("category", category);
      if (priority) params.set("priority", priority);
      if (slaState) params.set("slaState", slaState);
      if (assignment === "mine") params.set("assignedToMe", "true");
      if (assignment === "unassigned") params.set("unassigned", "true");
      if (pageParam) params.set("cursor", pageParam);
      return getSupport<SupportTicketQueue>(`/tickets?${params}`, signal);
    },
    getNextPageParam: (lastPage) => lastPage.nextCursor || undefined,
  });
  const tickets = queue.data?.pages.flatMap((page) => page.items) || [];

  useEffect(() => {
    const normalizedSearch = searchInput.trim();
    if (normalizedSearch === search) return;
    const timeout = window.setTimeout(() => {
      setSearch(normalizedSearch);
      setSelectedId(null);
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [search, searchInput]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("q", search);
    if (status) params.set("status", status);
    if (schoolId) params.set("schoolId", schoolId);
    if (category) params.set("category", category);
    if (priority) params.set("priority", priority);
    if (slaState) params.set("slaState", slaState);
    if (assignment === "mine") params.set("assignedToMe", "true");
    if (assignment === "unassigned") params.set("unassigned", "true");
    if (selectedId) params.set("ticketId", String(selectedId));
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${params.size ? `?${params}` : ""}`,
    );
  }, [assignment, category, priority, schoolId, search, selectedId, slaState, status]);

  function applySearch() {
    setSearch(searchInput.trim());
    setSelectedId(null);
  }

  function updateFilters(filters: TicketQueueFilterValues) {
    setStatus(filters.status);
    setSchoolId(filters.schoolId);
    setCategory(filters.category);
    setPriority(filters.priority);
    setSlaState(filters.slaState);
    setAssignment(filters.assignment);
    setSelectedId(null);
  }

  return (
    <div className="flex min-w-0 flex-col gap-4 overflow-x-hidden">
      <PageHeader title={title} subtitle={description} />

      <TicketQueueFilters
        searchInput={searchInput}
        filters={{ status, schoolId, category, priority, slaState, assignment }}
        schools={context.data?.schools || []}
        isSchoolLoading={context.isLoading}
        onSearchInputChange={setSearchInput}
        onSearch={applySearch}
        onFiltersChange={updateFilters}
      />

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
