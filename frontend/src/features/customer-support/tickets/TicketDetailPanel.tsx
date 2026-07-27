import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  CornerUpRight,
  Loader2,
  MessageSquareReply,
  UserCheck,
  UserMinus,
} from "lucide-react";
import { FormEvent } from "react";
import {
  getSupport,
  sendSupport,
  type SupportTicketDetail,
  type SupportTicketStatus,
} from "@/features/customer-support/api";
import {
  inputClass,
  primaryButton,
  secondaryButton,
  formatDate,
} from "@/features/customer-support/shared/ui";
import { EmptyState } from "@/shared/ui/EmptyState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

const STATUS_ACTIONS: Array<{
  status: SupportTicketStatus;
  label: string;
  icon: typeof CheckCircle2;
}> = [
  { status: "in_progress", label: "Start work", icon: MessageSquareReply },
  { status: "escalated", label: "Escalate", icon: CornerUpRight },
  { status: "resolved", label: "Resolve", icon: CheckCircle2 },
];

export function TicketDetailPanel({
  ticketId,
  csrfToken,
  currentStaffId,
  onBack,
}: {
  ticketId: number | null;
  csrfToken: string;
  currentStaffId: number | null;
  onBack: () => void;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["customer-support", "ticket", ticketId],
    queryFn: ({ signal }) => getSupport<SupportTicketDetail>(
      `/tickets/${ticketId}`,
      signal,
    ),
    enabled: ticketId !== null,
  });

  const refresh = () => {
    void queryClient.invalidateQueries({
      queryKey: ["customer-support", "ticket", ticketId],
    });
    void queryClient.invalidateQueries({
      queryKey: ["customer-support", "tickets"],
    });
  };
  const reply = useMutation({
    mutationFn: (body: string) => sendSupport(
      `/tickets/${ticketId}/messages`,
      "POST",
      { body },
      csrfToken,
    ),
    onSuccess: refresh,
  });
  const status = useMutation({
    mutationFn: (nextStatus: SupportTicketStatus) => sendSupport(
      `/tickets/${ticketId}/status`,
      "PATCH",
      { status: nextStatus, reason: "" },
      csrfToken,
    ),
    onSuccess: refresh,
  });
  const assignment = useMutation({
    mutationFn: (assignedStaffId: number | null) => sendSupport(
      `/tickets/${ticketId}/assignment`,
      "PATCH",
      { assignedStaffId },
      csrfToken,
    ),
    onSuccess: refresh,
  });

  if (ticketId === null) {
    return (
      <EmptyState
        title="Select a ticket"
        detail="Open a parent request to review its conversation and manage its lifecycle."
        icon={<MessageSquareReply className="h-5 w-5" />}
      />
    );
  }
  if (query.isLoading) return <TicketDetailSkeleton />;
  if (query.isError || !query.data) {
    return (
      <EmptyState
        title="Ticket unavailable"
        detail={query.error instanceof Error
          ? query.error.message
          : "The ticket could not be loaded from your assigned schools."}
        action={(
          <button type="button" className={secondaryButton} onClick={() => void query.refetch()}>
            Try again
          </button>
        )}
      />
    );
  }

  const { ticket, messages } = query.data;
  const isResolved = ticket.status === "resolved";
  const mutationError = reply.error || status.error || assignment.error;

  function submitReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = String(new FormData(form).get("body") || "").trim();
    if (!body) return;
    reply.mutate(body, { onSuccess: () => form.reset() });
  }

  return (
    <div className="min-w-0 space-y-4">
      <button type="button" onClick={onBack} className={`${secondaryButton} lg:hidden`}>
        <ArrowLeft className="h-4 w-4" />
        Back to tickets
      </button>

      <section className="overflow-hidden rounded-lg border border-border bg-card shadow-card">
        <header className="border-b border-border p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="break-words text-lg font-black text-foreground">{ticket.topic}</h2>
              <p className="mt-1 text-sm font-semibold text-muted-foreground">
                {ticket.requesterName} · {ticket.schoolName}
              </p>
            </div>
            <StatusBadge status={ticket.status} />
          </div>
          <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-3">
            <TicketFact label="Category" value={ticket.category.split("_").join(" ")} />
            <TicketFact
              label="Assigned to"
              value={ticket.assignedStaffName || "Unassigned"}
            />
            <TicketFact label="Updated" value={formatDate(ticket.updatedAt, true)} />
          </dl>
        </header>

        <div className="flex flex-wrap gap-2 border-b border-border p-3">
          {currentStaffId ? (
            ticket.assignedStaffId === currentStaffId ? (
              <button
                type="button"
                className={secondaryButton}
                disabled={assignment.isPending}
                onClick={() => assignment.mutate(null)}
              >
                <UserMinus className="h-4 w-4" />
                Unassign
              </button>
            ) : (
              <button
                type="button"
                className={secondaryButton}
                disabled={assignment.isPending}
                onClick={() => assignment.mutate(currentStaffId)}
              >
                <UserCheck className="h-4 w-4" />
                Assign to me
              </button>
            )
          ) : null}
          {STATUS_ACTIONS.filter((action) => action.status !== ticket.status).map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.status}
                type="button"
                className={action.status === "resolved" ? primaryButton : secondaryButton}
                disabled={status.isPending}
                onClick={() => status.mutate(action.status)}
              >
                <Icon className="h-4 w-4" />
                {action.label}
              </button>
            );
          })}
        </div>

        {mutationError ? (
          <p className="m-4 rounded-lg border border-destructive/25 bg-destructive/5 p-3 text-sm font-bold text-destructive" role="alert">
            {mutationError instanceof Error ? mutationError.message : "The ticket could not be updated."}
          </p>
        ) : null}

        <div className="space-y-3 p-4" aria-label="Ticket conversation">
          {messages.map((message) => {
            const fromParent = message.authorType === "parent";
            return (
              <article
                key={message.messageId}
                className={`flex ${fromParent ? "justify-start" : "justify-end"}`}
              >
                <div className={`max-w-[88%] rounded-xl px-4 py-3 ${
                  fromParent ? "bg-muted text-foreground" : "bg-primary text-primary-foreground"
                }`}>
                  <p className="whitespace-pre-wrap break-words text-sm leading-6">{message.body}</p>
                  <p className={`mt-2 text-[0.6875rem] font-bold ${
                    fromParent ? "text-muted-foreground" : "text-primary-foreground/75"
                  }`}>
                    {message.authorName || (fromParent ? ticket.requesterName : "Customer Support")}
                    {" · "}{formatDate(message.createdAt, true)}
                  </p>
                </div>
              </article>
            );
          })}
        </div>

        {isResolved ? (
          <p className="border-t border-border bg-emerald-50 px-4 py-4 text-sm font-bold text-emerald-800">
            This ticket is resolved and read-only. Change its status before sending another reply.
          </p>
        ) : (
          <form onSubmit={submitReply} className="border-t border-border p-4">
            <label htmlFor="support-ticket-reply" className="text-xs font-black uppercase tracking-wide text-muted-foreground">
              Reply
            </label>
            <textarea
              id="support-ticket-reply"
              name="body"
              required
              maxLength={4000}
              rows={4}
              className={`${inputClass} mt-2 min-h-28 py-3`}
              placeholder="Write a clear response to the parent…"
            />
            <button
              type="submit"
              disabled={reply.isPending}
              className={`${primaryButton} mt-3`}
            >
              {reply.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
              ) : (
                <MessageSquareReply className="h-4 w-4" />
              )}
              Send reply
            </button>
          </form>
        )}
      </section>
    </div>
  );
}

function TicketFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted px-3 py-2">
      <dt className="font-black uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words font-bold text-foreground">{value}</dd>
    </div>
  );
}

function TicketDetailSkeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading ticket">
      <span className="sr-only">Loading ticket</span>
      <div className="h-36 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
      <div className="h-80 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
    </div>
  );
}
