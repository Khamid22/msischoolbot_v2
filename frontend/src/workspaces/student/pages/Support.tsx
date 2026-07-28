import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LifeBuoy, Loader2, MessageSquareText, Send } from "lucide-react";
import { useState } from "react";
import { BillingCountdownBanner } from "@/shared/billing/BillingCountdownBanner";
import type { BillingAccessStatus } from "@/shared/billing/model";
import { getStudent, sendStudent } from "@/workspaces/student/accountApi";
import type {
  StudentAccountProps,
  StudentTicket,
  StudentTicketsPayload,
} from "@/workspaces/student/accountModel";
import { StudentAccountShell } from "@/workspaces/student/StudentAccountShell";

export default function StudentSupportPage(props: StudentAccountProps) {
  const queryClient = useQueryClient();
  const [topic, setTopic] = useState("To‘lov bo‘yicha yordam");
  const [message, setMessage] = useState("");
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null);
  const [reply, setReply] = useState("");
  const billing = useQuery({
    queryKey: ["student", "billing-status"],
    queryFn: ({ signal }) => getStudent<BillingAccessStatus>("/billing-status", signal),
    refetchInterval: 60_000,
  });
  const tickets = useQuery({
    queryKey: ["student", "support", "tickets"],
    queryFn: ({ signal }) => getStudent<StudentTicketsPayload>("/support/tickets", signal),
  });
  const selectedTicket = tickets.data?.items.find(
    (ticket) => ticket.ticketId === selectedTicketId,
  );
  const createTicket = useMutation({
    mutationFn: () => sendStudent<StudentTicket>(
      "/support/tickets",
      "POST",
      { topic, message, category: "payment" },
      props.csrfToken || "",
    ),
    onSuccess: (ticket) => {
      setMessage("");
      setSelectedTicketId(ticket.ticketId);
      void queryClient.invalidateQueries({ queryKey: ["student", "support", "tickets"] });
    },
  });
  const sendReply = useMutation({
    mutationFn: () => {
      if (!selectedTicket) throw new Error("Murojaat tanlanmagan.");
      return sendStudent<StudentTicket>(
        `/support/tickets/${selectedTicket.ticketId}/messages`,
        "POST",
        { body: reply },
        props.csrfToken || "",
      );
    },
    onSuccess: () => {
      setReply("");
      void queryClient.invalidateQueries({ queryKey: ["student", "support", "tickets"] });
    },
  });

  return (
    <StudentAccountShell active="support" status={billing.data} {...props}>
      {billing.data ? (
        <BillingCountdownBanner
          status={billing.data}
          paymentsHref="/student/payments"
          supportHref="/student/support"
        />
      ) : null}
      <header className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-primary">
          <LifeBuoy className="h-4 w-4" aria-hidden="true" />
          Yordam
        </p>
        <h1 className="mt-2 text-2xl font-black">Customer Support bilan bog‘lanish</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          To‘lov yoki hisob bo‘yicha muammoni yozing. Javob shu sahifada ko‘rinadi.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(17rem,0.75fr)_minmax(0,1.25fr)]">
        <div className="space-y-4">
          <form
            className="rounded-xl border border-border bg-surface p-4 shadow-card"
            onSubmit={(event) => {
              event.preventDefault();
              if (topic.trim().length >= 2 && message.trim().length >= 5) {
                createTicket.mutate();
              }
            }}
          >
            <h2 className="font-black">Yangi murojaat</h2>
            <label className="mt-3 block text-sm font-bold">
              Mavzu
              <input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                maxLength={160}
                className="mt-1 min-h-11 w-full rounded-lg border border-border bg-background px-3 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="mt-3 block text-sm font-bold">
              Xabar
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                maxLength={4_000}
                rows={4}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Muammoni qisqacha tushuntiring"
              />
            </label>
            <button
              type="submit"
              disabled={createTicket.isPending || topic.trim().length < 2 || message.trim().length < 5}
              className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            >
              {createTicket.isPending
                ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
                : <Send className="h-4 w-4" aria-hidden="true" />}
              Yuborish
            </button>
            {createTicket.isError ? (
              <p className="mt-2 text-sm font-semibold text-destructive" role="alert">
                {createTicket.error.message}
              </p>
            ) : null}
          </form>

          <section className="rounded-xl border border-border bg-surface p-3 shadow-card">
            <h2 className="px-1 pb-2 font-black">Murojaatlar</h2>
            {tickets.isLoading ? (
              <div className="h-24 animate-pulse rounded-lg bg-muted motion-reduce:animate-none" />
            ) : tickets.isError ? (
              <p className="p-3 text-sm text-destructive" role="alert">
                {tickets.error.message}
              </p>
            ) : tickets.data?.items.length ? (
              <div className="space-y-1">
                {tickets.data.items.map((ticket) => (
                  <button
                    key={ticket.ticketId}
                    type="button"
                    onClick={() => setSelectedTicketId(ticket.ticketId)}
                    className={`w-full rounded-lg border px-3 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      selectedTicketId === ticket.ticketId
                        ? "border-primary bg-primary/5"
                        : "border-transparent hover:bg-muted"
                    }`}
                  >
                    <span className="block truncate text-sm font-black">{ticket.topic}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      #{ticket.ticketId} · {ticket.status.replace("_", " ")}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="p-3 text-sm text-muted-foreground">Hozircha murojaat yo‘q.</p>
            )}
          </section>
        </div>

        <section className="min-h-80 rounded-xl border border-border bg-surface p-4 shadow-card">
          {selectedTicket ? (
            <>
              <div className="border-b border-border pb-3">
                <h2 className="font-black">{selectedTicket.topic}</h2>
                <p className="mt-1 text-xs font-bold uppercase text-muted-foreground">
                  #{selectedTicket.ticketId} · {selectedTicket.status.replace("_", " ")}
                </p>
              </div>
              <div className="space-y-3 py-4">
                {selectedTicket.messages.map((item) => {
                  const ownMessage = item.authorType === "student";
                  return (
                    <div
                      key={item.messageId}
                      className={`max-w-[88%] rounded-xl px-3 py-2 text-sm ${
                        ownMessage
                          ? "ml-auto bg-primary text-primary-foreground"
                          : "bg-muted text-foreground"
                      }`}
                    >
                      <p>{item.body}</p>
                      <p className="mt-1 text-[0.6875rem] opacity-70">{item.createdAt}</p>
                    </div>
                  );
                })}
              </div>
              {selectedTicket.status !== "resolved" ? (
                <form
                  className="flex gap-2 border-t border-border pt-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (reply.trim()) sendReply.mutate();
                  }}
                >
                  <input
                    value={reply}
                    onChange={(event) => setReply(event.target.value)}
                    className="min-h-11 min-w-0 flex-1 rounded-lg border border-border bg-background px-3 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    placeholder="Javob yozing"
                  />
                  <button
                    type="submit"
                    disabled={sendReply.isPending || !reply.trim()}
                    aria-label="Javob yuborish"
                    className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                  >
                    {sendReply.isPending
                      ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
                      : <Send className="h-4 w-4" aria-hidden="true" />}
                  </button>
                </form>
              ) : (
                <p className="border-t border-border pt-3 text-sm text-muted-foreground">
                  Bu murojaat yopilgan. Yangi murojaat yarating.
                </p>
              )}
              {sendReply.isError ? (
                <p className="mt-2 text-sm text-destructive" role="alert">
                  {sendReply.error.message}
                </p>
              ) : null}
            </>
          ) : (
            <div className="grid min-h-72 place-items-center text-center">
              <div>
                <MessageSquareText className="mx-auto h-8 w-8 text-muted-foreground" aria-hidden="true" />
                <h2 className="mt-3 font-black">Murojaatni tanlang</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Suhbat va javoblar shu yerda ko‘rinadi.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </StudentAccountShell>
  );
}
