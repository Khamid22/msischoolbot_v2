import { Clock3, CreditCard, LockKeyhole, MessageCircleQuestion } from "lucide-react";
import { useEffect, useState } from "react";
import type { BillingAccessStatus } from "@/shared/billing/model";

type BillingLanguage = "ru" | "uz";

function remainingSeconds(deadlineAt: string | null, fallback: number) {
  const deadline = deadlineAt ? Date.parse(deadlineAt) : Number.NaN;
  if (!Number.isFinite(deadline)) return Math.max(0, fallback);
  return Math.max(0, Math.ceil((deadline - Date.now()) / 1_000));
}

function countdownLabel(seconds: number) {
  const hours = Math.floor(seconds / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  const remaining = seconds % 60;
  return [hours, minutes, remaining]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

export function BillingCountdownBanner({
  status,
  paymentsHref,
  supportHref,
  language = "uz",
}: {
  status: BillingAccessStatus;
  paymentsHref: string;
  supportHref: string;
  language?: BillingLanguage;
}) {
  const [seconds, setSeconds] = useState(() => remainingSeconds(
    status.countdownDeadlineAt,
    status.remainingSeconds,
  ));

  useEffect(() => {
    const update = () => setSeconds(
      remainingSeconds(status.countdownDeadlineAt, status.remainingSeconds),
    );
    update();
    const timer = window.setInterval(update, 1_000);
    return () => window.clearInterval(timer);
  }, [status.countdownDeadlineAt, status.remainingSeconds]);

  if (!status.countdownDeadlineAt && status.mode === "normal") return null;

  const isHeld = status.mode === "payment_only" || seconds === 0;
  const isRu = language === "ru";
  const title = isHeld
    ? isRu ? "Доступ ограничен до оплаты" : "To‘lovgacha kirish cheklangan"
    : isRu ? "Оплатите счёт до окончания таймера" : "Taymer tugashidan oldin to‘lang";
  const description = status.invoices.length
    ? isRu
      ? "Оплата полного остатка автоматически восстановит доступ всей семье."
      : "Qoldiq to‘liq to‘lansa, butun oilaning kirishi avtomatik tiklanadi."
    : isRu
      ? "На связанном семейном аккаунте есть неоплаченный счёт. Детали доступны владельцу счёта."
      : "Bog‘langan oilaviy hisobda to‘lanmagan hisob bor. Tafsilotlar hisob egasiga ko‘rinadi.";

  return (
    <section
      className={`rounded-xl border p-4 shadow-card ${
        isHeld
          ? "border-destructive/30 bg-destructive/10"
          : "border-amber-300/70 bg-amber-50 text-amber-950"
      }`}
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 rounded-lg p-2 ${isHeld ? "bg-destructive/15 text-destructive" : "bg-amber-200/70"}`}>
          {isHeld
            ? <LockKeyhole className="h-5 w-5" aria-hidden="true" />
            : <Clock3 className="h-5 w-5" aria-hidden="true" />}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-black">{title}</h2>
            {!isHeld ? (
              <span className="rounded-md bg-foreground px-2.5 py-1 font-mono text-sm font-black tabular-nums text-background">
                {countdownLabel(seconds)}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm opacity-80">{description}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {status.invoices.length ? (
              <a
                href={paymentsHref}
                className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-black text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <CreditCard className="h-4 w-4" aria-hidden="true" />
                {isRu ? "Перейти к оплате" : "To‘lovga o‘tish"}
              </a>
            ) : null}
            <a
              href={supportHref}
              className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-black text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <MessageCircleQuestion className="h-4 w-4" aria-hidden="true" />
              {isRu ? "Поддержка" : "Yordam"}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
