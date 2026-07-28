import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock3, CreditCard, Loader2, WalletCards } from "lucide-react";
import { BillingCountdownBanner } from "@/shared/billing/BillingCountdownBanner";
import type { BillingAccessStatus } from "@/shared/billing/model";
import { getStudent } from "@/workspaces/student/accountApi";
import type {
  StudentAccountProps,
  StudentInvoiceCheckout,
  StudentPayment,
  StudentPaymentsPayload,
} from "@/workspaces/student/accountModel";
import { StudentAccountShell } from "@/workspaces/student/StudentAccountShell";

function formatMoney(value: number, currency: string) {
  return new Intl.NumberFormat("uz-UZ", {
    style: "currency",
    currency: currency || "UZS",
    maximumFractionDigits: 0,
  }).format(value);
}

function submitPayme(checkout: StudentInvoiceCheckout) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkout.checkoutUrl;
  form.hidden = true;
  const fields: Record<string, string> = {
    merchant: checkout.merchantId,
    amount: String(checkout.amountMinor),
    "account[invoice_id]": String(checkout.invoiceId),
    lang: "uz",
    callback: checkout.callbackUrl,
    callback_timeout: "1500",
    description: `MSI School · invoice ${checkout.invoiceId}`,
  };
  for (const [name, value] of Object.entries(fields)) {
    const input = document.createElement("input");
    input.name = name;
    input.value = value;
    form.append(input);
  }
  document.body.append(form);
  form.submit();
  form.remove();
}

function PaymentCard({ payment }: { payment: StudentPayment }) {
  const checkout = useMutation({
    mutationFn: () => {
      if (!payment.invoiceId) throw new Error("Hisob topilmadi.");
      return getStudent<StudentInvoiceCheckout>(
        `/payments/${payment.invoiceId}/checkout`,
      );
    },
    onSuccess: submitPayme,
  });
  const isPaid = payment.state === "paid";
  return (
    <article className="rounded-xl border border-border bg-surface p-4 shadow-card">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {isPaid
              ? <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
              : <Clock3 className="h-5 w-5 text-amber-600" aria-hidden="true" />}
            <h2 className="truncate font-black">
              {payment.month || payment.subject || "Maktab to‘lovi"}
            </h2>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {[payment.subject, payment.dueDate ? `Muddat: ${payment.dueDate}` : ""]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <div className="shrink-0 sm:text-right">
          <p className="text-lg font-black tabular-nums">
            {formatMoney(payment.amount, payment.currency)}
          </p>
          <p className="text-xs font-bold uppercase text-muted-foreground">
            {isPaid ? "To‘langan" : payment.state === "debt" ? "Muddati o‘tgan" : "To‘lash kerak"}
          </p>
        </div>
      </div>
      {payment.canPayOnline && payment.invoiceId ? (
        <button
          type="button"
          disabled={checkout.isPending}
          onClick={() => checkout.mutate()}
          className="mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-black text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-wait disabled:opacity-60 sm:w-auto"
        >
          {checkout.isPending
            ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
            : <WalletCards className="h-4 w-4" aria-hidden="true" />}
          Payme orqali to‘lash
        </button>
      ) : null}
      {checkout.isError ? (
        <p className="mt-2 text-sm font-semibold text-destructive" role="alert">
          {checkout.error.message}
        </p>
      ) : null}
    </article>
  );
}

export default function StudentPaymentsPage(props: StudentAccountProps) {
  const billing = useQuery({
    queryKey: ["student", "billing-status"],
    queryFn: ({ signal }) => getStudent<BillingAccessStatus>("/billing-status", signal),
    refetchInterval: 60_000,
  });
  const payments = useQuery({
    queryKey: ["student", "payments"],
    queryFn: ({ signal }) => getStudent<StudentPaymentsPayload>("/payments", signal),
    refetchOnWindowFocus: true,
  });
  const isLoading = billing.isLoading || payments.isLoading;
  const error = billing.error || payments.error;

  return (
    <StudentAccountShell active="payments" status={billing.data} {...props}>
      {billing.data ? (
        <BillingCountdownBanner
          status={billing.data}
          paymentsHref="/student/payments"
          supportHref="/student/support"
        />
      ) : null}
      <header className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-primary">
          <CreditCard className="h-4 w-4" aria-hidden="true" />
          To‘lovlar
        </p>
        <h1 className="mt-2 text-2xl font-black">Hisob va to‘lovlar</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Hisobni Payme orqali xavfsiz to‘lang. To‘liq to‘lovdan keyin kirish avtomatik tiklanadi.
        </p>
      </header>

      {isLoading ? (
        <div className="space-y-3" aria-label="To‘lovlar yuklanmoqda">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-28 animate-pulse rounded-xl bg-muted motion-reduce:animate-none" />
          ))}
        </div>
      ) : error ? (
        <section className="rounded-xl border border-destructive/30 bg-destructive/10 p-5 text-center">
          <p className="font-black text-destructive">To‘lovlarni yuklab bo‘lmadi</p>
          <p className="mt-1 text-sm text-muted-foreground">{error.message}</p>
          <button
            type="button"
            onClick={() => {
              void billing.refetch();
              void payments.refetch();
            }}
            className="mt-4 min-h-11 rounded-lg border border-border bg-surface px-4 text-sm font-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Qayta urinish
          </button>
        </section>
      ) : payments.data?.items.length ? (
        <div className="space-y-3">
          {payments.data.items.map((payment) => (
            <PaymentCard key={payment.paymentId} payment={payment} />
          ))}
        </div>
      ) : (
        <section className="rounded-xl border border-dashed border-border bg-surface p-8 text-center">
          <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-600" aria-hidden="true" />
          <h2 className="mt-3 font-black">Hozircha hisob yo‘q</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Yangi hisoblar va to‘lovlar tarixi shu yerda ko‘rinadi.
          </p>
        </section>
      )}
    </StudentAccountShell>
  );
}
