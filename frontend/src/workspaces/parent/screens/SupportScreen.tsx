import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, LifeBuoy, MessageCircle, Plus, Send } from "lucide-react";
import { FormEvent, useState } from "react";
import { getParent, sendParent } from "@/workspaces/parent/api";
import {
  EmptyState,
  ErrorState,
  formatDate,
  LoadingState,
  ParentPageHeader,
} from "@/workspaces/parent/components";
import type {
  ParentChild,
  ParentLanguage,
  ParentTicket,
  TicketsPayload,
} from "@/workspaces/parent/model";
import { navigateParentWorkspace } from "@/workspaces/parent/navigation";

const CATEGORIES = [
  "payment",
  "teacher",
  "lesson_quality",
  "schedule",
  "attendance",
  "technical",
  "account",
  "other",
] as const;

export function SupportScreen({
  children,
  selectedTicketId,
  language,
  csrfToken,
}: {
  children: ParentChild[];
  selectedTicketId: number | null;
  language: ParentLanguage;
  csrfToken: string;
}) {
  if (selectedTicketId) {
    return (
      <TicketDetail
        ticketId={selectedTicketId}
        language={language}
        csrfToken={csrfToken}
      />
    );
  }
  return (
    <TicketList
      children={children}
      language={language}
      csrfToken={csrfToken}
    />
  );
}

function TicketList({
  children,
  language,
  csrfToken,
}: {
  children: ParentChild[];
  language: ParentLanguage;
  csrfToken: string;
}) {
  const isRu = language === "ru";
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();
  const tickets = useQuery({
    queryKey: ["parent", "tickets"],
    queryFn: ({ signal }) => getParent<TicketsPayload>("/tickets", signal),
  });
  const mutation = useMutation({
    mutationFn: (body: {
      studentRowId: number;
      category: string;
      topic: string;
      message: string;
    }) => sendParent<ParentTicket>("/tickets", "POST", body, csrfToken),
    onSuccess: (ticket) => {
      void queryClient.invalidateQueries({ queryKey: ["parent", "tickets"] });
      navigateParentWorkspace(`/parent/support/${ticket.ticketId}`);
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    mutation.mutate({
      studentRowId: Number(data.get("studentId")),
      category: String(data.get("category") || "other"),
      topic: String(data.get("topic") || ""),
      message: String(data.get("message") || ""),
    });
  }

  return (
    <>
      <ParentPageHeader
        title={isRu ? "Помощь" : "Yordam"}
        description={isRu
          ? "Обращения в службу поддержки школы и ответы сотрудников."
          : "Maktab yordam xizmatiga murojaatlar va xodimlar javoblari."}
        action={
          children.length ? (
            <button
              type="button"
              onClick={() => setShowForm((current) => !current)}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            >
              <Plus className="h-4 w-4" />
              {isRu ? "Новое обращение" : "Yangi murojaat"}
            </button>
          ) : undefined
        }
      />

      {showForm ? (
        <form onSubmit={submit} className="rounded-xl border border-primary/25 bg-surface p-4 shadow-card">
          <h2 className="font-black text-foreground">{isRu ? "Новое обращение" : "Yangi murojaat"}</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-bold text-foreground">
              {isRu ? "Ребёнок" : "Bola"}
              <select
                name="studentId"
                required
                className="mt-1 min-h-11 w-full rounded-lg border border-border bg-background px-3 text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
              >
                <option value="">{isRu ? "Выберите" : "Tanlang"}</option>
                {children.map((child) => (
                  <option key={child.studentRowId} value={child.studentRowId}>{child.fullName}</option>
                ))}
              </select>
            </label>
            <label className="text-sm font-bold text-foreground">
              {isRu ? "Категория" : "Toifa"}
              <select
                name="category"
                className="mt-1 min-h-11 w-full rounded-lg border border-border bg-background px-3 text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
              >
                {CATEGORIES.map((category) => (
                  <option key={category} value={category}>{categoryLabel(category, language)}</option>
                ))}
              </select>
            </label>
          </div>
          <label className="mt-4 block text-sm font-bold text-foreground">
            {isRu ? "Тема" : "Mavzu"}
            <input
              name="topic"
              required
              minLength={2}
              maxLength={160}
              className="mt-1 min-h-11 w-full rounded-lg border border-border bg-background px-3 text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            />
          </label>
          <label className="mt-4 block text-sm font-bold text-foreground">
            {isRu ? "Сообщение" : "Xabar"}
            <textarea
              name="message"
              required
              minLength={5}
              maxLength={4000}
              rows={5}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            />
          </label>
          {mutation.isError ? (
            <p className="mt-3 text-sm font-semibold text-destructive" role="alert">
              {mutation.error instanceof Error ? mutation.error.message : "Could not create ticket."}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={mutation.isPending}
            className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-bold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {mutation.isPending
              ? (isRu ? "Отправка…" : "Yuborilmoqda…")
              : (isRu ? "Отправить" : "Yuborish")}
          </button>
        </form>
      ) : null}

      {tickets.isLoading ? <LoadingState label={isRu ? "Загрузка обращений" : "Murojaatlar yuklanmoqda"} /> : null}
      {tickets.isError ? (
        <ErrorState
          message={tickets.error instanceof Error ? tickets.error.message : "Could not load tickets."}
          retry={() => void tickets.refetch()}
          label={isRu ? "Повторить" : "Qayta urinish"}
        />
      ) : null}
      {!tickets.isLoading && !tickets.isError ? (
        tickets.data?.items.length ? (
          <div className="space-y-2">
            {tickets.data.items.map((ticket) => (
              <a
                key={ticket.ticketId}
                href={`/parent/support/${ticket.ticketId}`}
                className="group flex min-h-24 items-center gap-3 rounded-xl border border-border bg-surface p-4 shadow-card hover:border-primary/35 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
              >
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <MessageCircle className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="truncate font-black text-foreground">{ticket.topic}</h2>
                    <TicketStatus status={ticket.status} language={language} />
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {ticket.studentName} · {formatDate(ticket.updatedAt)}
                  </p>
                </div>
                <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 motion-reduce:transition-none" />
              </a>
            ))}
          </div>
        ) : (
          <EmptyState
            title={isRu ? "Обращений пока нет" : "Hozircha murojaatlar yo‘q"}
            description={children.length
              ? (isRu ? "Если нужна помощь, создайте новое обращение." : "Yordam kerak bo‘lsa, yangi murojaat yarating.")
              : (isRu ? "Сначала школа должна подключить ребёнка." : "Avval maktab bolani ulashi kerak.")}
          />
        )
      ) : null}
    </>
  );
}

function TicketDetail({
  ticketId,
  language,
  csrfToken,
}: {
  ticketId: number;
  language: ParentLanguage;
  csrfToken: string;
}) {
  const isRu = language === "ru";
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["parent", "ticket", ticketId],
    queryFn: ({ signal }) => getParent<ParentTicket>(`/tickets/${ticketId}`, signal),
  });
  const reply = useMutation({
    mutationFn: (body: string) => sendParent<ParentTicket>(
      `/tickets/${ticketId}/messages`,
      "POST",
      { body },
      csrfToken,
    ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["parent", "ticket", ticketId] });
      void queryClient.invalidateQueries({ queryKey: ["parent", "tickets"] });
    },
  });
  if (query.isLoading) return <LoadingState label={isRu ? "Загрузка обращения" : "Murojaat yuklanmoqda"} />;
  if (query.isError || !query.data) {
    return (
      <ErrorState
        message={query.error instanceof Error ? query.error.message : "Ticket was not found."}
        retry={() => void query.refetch()}
        label={isRu ? "Повторить" : "Qayta urinish"}
      />
    );
  }
  const ticket = query.data;

  function submitReply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const body = String(new FormData(form).get("body") || "");
    reply.mutate(body, { onSuccess: () => form.reset() });
  }

  return (
    <>
      <ParentPageHeader
        title={ticket.topic}
        description={`${ticket.studentName} · ${ticket.schoolName}`}
        action={<TicketStatus status={ticket.status} language={language} />}
      />
      <a href="/parent/support" className="text-sm font-bold text-primary hover:underline">
        ← {isRu ? "Все обращения" : "Barcha murojaatlar"}
      </a>
      <section className="space-y-3 rounded-xl border border-border bg-surface p-4 shadow-card">
        {ticket.messages.map((message) => {
          const fromParent = message.authorType === "parent";
          return (
            <div key={message.messageId} className={`flex ${fromParent ? "justify-end" : "justify-start"}`}>
              <article className={`max-w-[88%] rounded-2xl px-4 py-3 ${fromParent ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"}`}>
                <p className="whitespace-pre-wrap text-sm leading-6">{message.body}</p>
                <p className={`mt-2 text-[0.6875rem] font-semibold ${fromParent ? "text-primary-foreground/75" : "text-muted-foreground"}`}>
                  {fromParent ? (isRu ? "Вы" : "Siz") : (message.authorName || (isRu ? "Поддержка" : "Yordam"))}
                  {" · "}{formatDate(message.createdAt)}
                </p>
              </article>
            </div>
          );
        })}
      </section>
      {ticket.status === "resolved" ? (
        <section className="rounded-xl border border-border bg-muted p-4">
          <p className="text-sm font-semibold text-foreground">
            {isRu
              ? "Обращение закрыто. Если вопрос остался, создайте новое."
              : "Murojaat yopilgan. Savol qolsa, yangi murojaat yarating."}
          </p>
          <a href="/parent/support" className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground">
            {isRu ? "Создать новое" : "Yangisini yaratish"}
          </a>
        </section>
      ) : (
        <form onSubmit={submitReply} className="rounded-xl border border-border bg-surface p-4">
          <label className="text-sm font-bold text-foreground">
            {isRu ? "Ответ" : "Javob"}
            <textarea
              name="body"
              required
              rows={4}
              maxLength={4000}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-base focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            />
          </label>
          {reply.isError ? (
            <p className="mt-2 text-sm font-semibold text-destructive" role="alert">
              {reply.error instanceof Error ? reply.error.message : "Could not send reply."}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={reply.isPending}
            className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {reply.isPending ? (isRu ? "Отправка…" : "Yuborilmoqda…") : (isRu ? "Отправить" : "Yuborish")}
          </button>
        </form>
      )}
    </>
  );
}

function TicketStatus({
  status,
  language,
}: {
  status: ParentTicket["status"];
  language: ParentLanguage;
}) {
  const isRu = language === "ru";
  const labels = isRu
    ? { new: "Новое", in_progress: "В работе", escalated: "Передано", resolved: "Закрыто" }
    : { new: "Yangi", in_progress: "Jarayonda", escalated: "Yo‘naltirilgan", resolved: "Yopilgan" };
  const tone = status === "resolved"
    ? "bg-emerald-100 text-emerald-800"
    : status === "escalated"
      ? "bg-amber-100 text-amber-800"
      : "bg-primary/10 text-primary";
  return <span className={`rounded-full px-2 py-1 text-[0.6875rem] font-bold ${tone}`}>{labels[status]}</span>;
}

function categoryLabel(category: string, language: ParentLanguage) {
  const ru: Record<string, string> = {
    payment: "Оплата",
    teacher: "Учитель",
    lesson_quality: "Качество урока",
    schedule: "Расписание",
    attendance: "Посещаемость",
    technical: "Техническая проблема",
    account: "Аккаунт",
    other: "Другое",
  };
  const uz: Record<string, string> = {
    payment: "To‘lov",
    teacher: "O‘qituvchi",
    lesson_quality: "Dars sifati",
    schedule: "Jadval",
    attendance: "Davomat",
    technical: "Texnik muammo",
    account: "Hisob",
    other: "Boshqa",
  };
  return (language === "ru" ? ru : uz)[category] || category;
}
