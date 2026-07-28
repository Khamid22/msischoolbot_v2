import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock3, CreditCard, Loader2, TriangleAlert, WalletCards } from "lucide-react";
import { getParent } from "@/workspaces/parent/api";
import {
  EmptyState,
  ErrorState,
  formatDate,
  formatMoney,
  LoadingState,
  ParentPageHeader,
} from "@/workspaces/parent/components";
import type {
  ParentChild,
  ParentLanguage,
  ParentInvoiceCheckout,
  ParentPayment,
  PaymentsPayload,
} from "@/workspaces/parent/model";

const STATE_ORDER = ["debt", "due", "upcoming", "paid"] as const;

export function PaymentsScreen({
  children,
  selectedStudentId,
  language,
}: {
  children: ParentChild[];
  selectedStudentId: number | null;
  language: ParentLanguage;
}) {
  const isRu = language === "ru";
  const query = useQuery({
    queryKey: ["parent", "payments", selectedStudentId],
    queryFn: ({ signal }) => getParent<PaymentsPayload>(
      `/payments${selectedStudentId ? `?studentId=${selectedStudentId}` : ""}`,
      signal,
    ),
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
  if (query.isLoading) {
    return <LoadingState label={isRu ? "Загрузка платежей" : "To‘lovlar yuklanmoqda"} />;
  }
  if (query.isError) {
    return (
      <ErrorState
        message={query.error instanceof Error ? query.error.message : "Could not load payments."}
        retry={() => void query.refetch()}
        label={isRu ? "Повторить" : "Qayta urinish"}
      />
    );
  }

  const payload = query.data;
  const records = payload?.items || [];
  const summary = payload?.summary;
  const childNames = new Map(children.map((child) => [child.studentRowId, child.fullName]));
  const grouped = STATE_ORDER.map((state) => ({
    state,
    items: records.filter((item) => item.state === state),
  })).filter((group) => group.items.length);

  return (
    <>
      <ParentPageHeader
        title={isRu ? "Платежи" : "To‘lovlar"}
        description={isRu
          ? "Текущие начисления и история оплат. Изменение платежей недоступно."
          : "Joriy hisoblar va to‘lovlar tarixi. To‘lovlarni o‘zgartirish mumkin emas."}
      />
      {summary ? (
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {[
            [TriangleAlert, isRu ? "Долг" : "Qarz", summary.debtTotal, "text-destructive"],
            [CreditCard, isRu ? "К оплате" : "To‘lash", summary.dueTotal, "text-amber-700"],
            [Clock3, isRu ? "Предстоящие" : "Kelgusi", summary.upcomingTotal, "text-primary"],
            [CheckCircle2, isRu ? "Оплачено" : "To‘langan", summary.paidTotal, "text-emerald-700"],
          ].map(([Icon, label, value, tone]) => {
            const MetricIcon = Icon as typeof CreditCard;
            return (
              <section key={String(label)} className="rounded-xl border border-border bg-surface p-3 shadow-card">
                <p className="flex items-center gap-2 text-xs font-bold text-muted-foreground">
                  <MetricIcon className="h-4 w-4" /> {String(label)}
                </p>
                <p className={`mt-3 break-words text-lg font-black tabular-nums ${String(tone)}`}>
                  {formatMoney(Number(value), summary.currency)}
                </p>
              </section>
            );
          })}
        </div>
      ) : null}
      {grouped.length ? (
        <div className="space-y-5">
          {grouped.map((group) => (
            <section key={group.state}>
              <h2 className="mb-2 text-sm font-black uppercase tracking-wide text-muted-foreground">
                {paymentStateLabel(group.state, language)}
              </h2>
              <div className="space-y-2">
                {group.items.map((payment) => (
                  <PaymentRow
                    key={payment.paymentId}
                    payment={payment}
                    childName={childNames.get(payment.studentRowId) || ""}
                    language={language}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <EmptyState
          title={isRu ? "Платежей пока нет" : "Hozircha to‘lovlar yo‘q"}
          description={isRu
            ? "Начисления и оплаченные счета появятся здесь."
            : "Hisoblar va to‘langan to‘lovlar shu yerda ko‘rinadi."}
        />
      )}
    </>
  );
}

function PaymentRow({
  payment,
  childName,
  language,
}: {
  payment: ParentPayment;
  childName: string;
  language: ParentLanguage;
}) {
  const isRu = language === "ru";
  const checkout = useMutation({
    mutationFn: () => {
      if (!payment.invoiceId) throw new Error(isRu ? "Счёт не найден." : "Hisob topilmadi.");
      return getParent<ParentInvoiceCheckout>(`/payments/${payment.invoiceId}/checkout`);
    },
    onSuccess: (data) => submitPaymeCheckout(data, language),
  });
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <h3 className="font-bold text-foreground">{payment.month || payment.subject || (isRu ? "Платёж" : "To‘lov")}</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          {[childName, payment.subject, payment.dueDate ? `${isRu ? "до" : "muddat"} ${formatDate(payment.dueDate)}` : ""]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-stretch gap-2 sm:items-end">
        <p className="text-base font-black tabular-nums text-foreground">
          {formatMoney(payment.amount, payment.currency)}
        </p>
        {payment.canPayOnline && payment.invoiceId ? (
          <button
            type="button"
            disabled={checkout.isPending}
            onClick={() => checkout.mutate()}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-black text-primary-foreground transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60 motion-reduce:transition-none"
          >
            {checkout.isPending
              ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              : <WalletCards className="h-4 w-4" aria-hidden="true" />}
            {isRu ? "Оплатить через Payme" : "Payme orqali to‘lash"}
          </button>
        ) : null}
        {checkout.isError ? (
          <p role="alert" className="max-w-xs text-xs font-bold text-destructive">
            {checkout.error instanceof Error
              ? checkout.error.message
              : isRu ? "Не удалось открыть Payme." : "Payme ochilmadi."}
          </p>
        ) : null}
      </div>
    </article>
  );
}

function submitPaymeCheckout(
  checkout: ParentInvoiceCheckout,
  language: ParentLanguage,
) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkout.checkoutUrl;
  form.style.display = "none";
  const fields: Record<string, string> = {
    merchant: checkout.merchantId,
    amount: String(checkout.amountMinor),
    "account[invoice_id]": String(checkout.invoiceId),
    lang: language,
    callback: checkout.callbackUrl,
    callback_timeout: "1500",
    description: `MSI School · invoice ${checkout.invoiceId}`,
  };
  Object.entries(fields).forEach(([name, value]) => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.append(input);
  });
  document.body.append(form);
  form.submit();
  form.remove();
}

function paymentStateLabel(state: string, language: ParentLanguage) {
  const ru: Record<string, string> = { debt: "Долг", due: "К оплате", upcoming: "Предстоящие", paid: "Оплачено" };
  const uz: Record<string, string> = { debt: "Qarz", due: "To‘lash", upcoming: "Kelgusi", paid: "To‘langan" };
  return (language === "ru" ? ru : uz)[state] || state;
}
