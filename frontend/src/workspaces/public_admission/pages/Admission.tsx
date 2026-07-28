import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock3, Download, FileCheck2, Loader2, ShieldCheck, Upload, WalletCards } from "lucide-react";
import { useMemo, type FormEvent } from "react";
import { inputClass, money, primaryButton, secondaryButton } from "@/features/customer-support/shared/ui";

type PublicAdmissionData = {
  admissionId: number;
  studentFullName: string;
  schoolName: string;
  preferredLanguage: "uz" | "ru";
  status: string;
  contract: {
    status: string;
    originalFileName: string;
    signedFileName: string;
    rejectionReason: string;
  } | null;
  invoice: {
    invoiceId: number;
    invoiceNumber: string;
    currency: string;
    totalMinor: number;
    paidMinor: number;
    balanceMinor: number;
    status: string;
    dueDate: string;
  } | null;
  paymeIsAvailable: boolean;
  checkoutUrl: string;
  merchantId: string;
  callbackUrl: string;
};

const copy = {
  uz: {
    title: "Qabul jarayoni",
    contract: "Shartnoma",
    invoice: "Birinchi hisob",
    download: "Shartnomani yuklab olish",
    signed: "Imzolangan nusxani yuboring",
    upload: "Yuborish",
    waitReview: "Shartnoma yuborildi. Maktab tasdiqlashini kuting.",
    pay: "Payme orqali to'lash",
    unavailable: "Payme hozircha sozlanmagan. Yordam xizmati bilan bog'laning.",
    activated: "Qabul muvaffaqiyatli faollashtirildi.",
    paid: "To'lov tasdiqlandi. Faollashtirish holatini tekshirmoqdamiz.",
    secure: "Xavfsiz qabul havolasi",
  },
  ru: {
    title: "Процесс зачисления",
    contract: "Договор",
    invoice: "Первый счёт",
    download: "Скачать договор",
    signed: "Загрузите подписанную копию",
    upload: "Отправить",
    waitReview: "Договор отправлен. Ожидайте подтверждения школы.",
    pay: "Оплатить через Payme",
    unavailable: "Payme пока не настроен. Свяжитесь со службой поддержки.",
    activated: "Зачисление успешно активировано.",
    paid: "Оплата подтверждена. Проверяем статус активации.",
    secure: "Защищённая ссылка зачисления",
  },
} as const;

async function parseResponse<T>(response: Response): Promise<T> {
  const envelope = await response.json().catch(() => ({}));
  if (!response.ok || envelope.status !== "success") {
    throw new Error(String(envelope.message || "The request could not be completed."));
  }
  return envelope.data as T;
}

export default function PublicAdmission({ accessToken = "" }: { accessToken?: string }) {
  const query = useQuery({
    queryKey: ["public-admission", accessToken],
    queryFn: async () => {
      const response = await fetch(`/api/v1/public/admissions/${encodeURIComponent(accessToken)}`, {
        credentials: "omit",
        cache: "no-store",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      return parseResponse<PublicAdmissionData>(response);
    },
    refetchInterval: (state) => {
      const status = state.state.data?.status;
      return status === "awaiting_payment" ? 5000 : false;
    },
  });
  const mutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.set("document", file);
      const response = await fetch(`/api/v1/public/admissions/${encodeURIComponent(accessToken)}/contract`, {
        method: "POST",
        credentials: "omit",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: formData,
      });
      return parseResponse<PublicAdmissionData>(response);
    },
    onSuccess: (data) => query.refetch().then(() => data),
  });
  const language = query.data?.preferredLanguage === "ru" ? "ru" : "uz";
  const text = copy[language];
  const invoice = query.data?.invoice;
  const statusSteps = useMemo(() => [
    { label: text.contract, done: query.data?.contract?.status === "accepted" },
    { label: text.invoice, done: invoice?.status === "paid" },
    { label: language === "uz" ? "Faollashtirish" : "Активация", done: query.data?.status === "active" },
  ], [invoice?.status, language, query.data?.contract?.status, query.data?.status, text.contract, text.invoice]);

  function submitContract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = new FormData(event.currentTarget).get("document");
    if (file instanceof File && file.size > 0) mutation.mutate(file);
  }

  if (query.isLoading) {
    return <main className="min-h-screen bg-background p-4"><div className="mx-auto h-96 max-w-2xl animate-pulse rounded-2xl bg-muted motion-reduce:animate-none" /></main>;
  }
  if (query.isError || !query.data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 text-center shadow-card">
          <ShieldCheck className="mx-auto h-10 w-10 text-muted-foreground" />
          <h1 className="mt-4 text-xl font-black text-foreground">Admission link unavailable</h1>
          <p className="mt-2 text-sm font-semibold text-muted-foreground">
            {query.error instanceof Error ? query.error.message : "Ask Customer Support for a new secure link."}
          </p>
        </div>
      </main>
    );
  }

  const data = query.data;
  return (
    <main className="min-h-screen bg-background px-[calc(var(--app-left-inset)+1rem)] pb-[calc(var(--app-bottom-inset)+2rem)] pt-[calc(var(--app-top-inset)+1rem)]">
      <div className="mx-auto max-w-2xl space-y-4">
        <header className="rounded-2xl bg-primary p-5 text-primary-foreground shadow-card">
          <p className="flex items-center gap-2 text-xs font-black uppercase tracking-widest opacity-80">
            <ShieldCheck className="h-4 w-4" /> {text.secure}
          </p>
          <h1 className="mt-3 text-2xl font-black">{text.title}</h1>
          <p className="mt-1 text-sm font-bold opacity-85">{data.studentFullName} · {data.schoolName}</p>
        </header>

        <ol className="grid grid-cols-3 gap-2 rounded-2xl border border-border bg-card p-3 shadow-sm">
          {statusSteps.map((step, index) => (
            <li key={step.label} className="text-center">
              <span className={`mx-auto flex h-9 w-9 items-center justify-center rounded-full ${step.done ? "bg-emerald-100 text-emerald-700" : "bg-muted text-muted-foreground"}`}>
                {step.done ? <CheckCircle2 className="h-5 w-5" /> : <span className="text-xs font-black">{index + 1}</span>}
              </span>
              <span className="mt-1 block text-[0.6875rem] font-black text-foreground">{step.label}</span>
            </li>
          ))}
        </ol>

        {data.status === "active" ? (
          <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-900">
            <CheckCircle2 className="h-8 w-8" />
            <p className="mt-3 text-lg font-black">{text.activated}</p>
          </section>
        ) : null}

        <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-base font-black text-foreground"><FileCheck2 className="h-5 w-5 text-primary" /> {text.contract}</h2>
          {data.contract ? (
            <div className="mt-4 space-y-3">
              <a href={`/api/v1/public/admissions/${encodeURIComponent(accessToken)}/contract/download`} className={secondaryButton}>
                <Download className="h-4 w-4" /> {text.download}
              </a>
              {["sent", "rejected"].includes(data.contract.status) ? (
                <form className="space-y-3 rounded-xl bg-muted/40 p-3" onSubmit={submitContract}>
                  <label className="block text-sm font-black text-foreground" htmlFor="signed-contract">{text.signed}</label>
                  <input id="signed-contract" name="document" type="file" required accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" className={`${inputClass} file:mr-3 file:border-0 file:bg-transparent file:font-bold`} />
                  <button type="submit" className={primaryButton} disabled={mutation.isPending}>
                    {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Upload className="h-4 w-4" />}
                    {text.upload}
                  </button>
                </form>
              ) : null}
              {["submitted", "accepted"].includes(data.contract.status) ? (
                <p className="flex items-center gap-2 rounded-lg bg-muted p-3 text-sm font-bold text-muted-foreground">
                  <Clock3 className="h-4 w-4" /> {text.waitReview}
                </p>
              ) : null}
              {mutation.isError ? (
                <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm font-bold text-destructive">
                  {mutation.error instanceof Error ? mutation.error.message : "The signed contract could not be uploaded. Please try again."}
                </p>
              ) : null}
            </div>
          ) : (
            <p className="mt-3 text-sm font-semibold text-muted-foreground">Customer Support is preparing the contract.</p>
          )}
        </section>

        {invoice ? (
          <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h2 className="flex items-center gap-2 text-base font-black text-foreground"><WalletCards className="h-5 w-5 text-primary" /> {text.invoice}</h2>
            <div className="mt-4 flex flex-wrap items-end justify-between gap-3 rounded-xl bg-muted/40 p-4">
              <div>
                <p className="font-mono text-xs font-black text-muted-foreground">{invoice.invoiceNumber}</p>
                <p className="mt-1 text-2xl font-black text-foreground">{money(invoice.balanceMinor / 100, invoice.currency)}</p>
                <p className="text-xs font-semibold text-muted-foreground">Due {invoice.dueDate}</p>
              </div>
              <span className="rounded-full bg-background px-3 py-1 text-xs font-black uppercase text-muted-foreground">{invoice.status.replace(/_/g, " ")}</span>
            </div>
            {invoice.balanceMinor > 0 && data.status === "awaiting_payment" ? data.paymeIsAvailable ? (
              <form method="POST" action={data.checkoutUrl} className="mt-4">
                <input type="hidden" name="merchant" value={data.merchantId} />
                <input type="hidden" name="amount" value={invoice.balanceMinor} />
                <input type="hidden" name="account[invoice_id]" value={invoice.invoiceId} />
                <input type="hidden" name="lang" value={language} />
                <input type="hidden" name="callback" value={data.callbackUrl} />
                <input type="hidden" name="callback_timeout" value="1500" />
                <input type="hidden" name="description" value={`MSI School · ${invoice.invoiceNumber}`} />
                <button type="submit" className={`${primaryButton} w-full`}>
                  <WalletCards className="h-5 w-5" /> {text.pay}
                </button>
              </form>
            ) : (
              <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm font-bold text-amber-900">{text.unavailable}</p>
            ) : invoice.status === "paid" && data.status !== "active" ? (
              <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm font-bold text-emerald-900">{text.paid}</p>
            ) : null}
          </section>
        ) : null}
      </div>
    </main>
  );
}
