import { FormEvent, ReactNode } from "react";
import { Activity, BookOpen, CreditCard, GraduationCap, LogOut, TrendingUp, UserRound } from "lucide-react";
import { TelegramLayout, Topbar } from "@/shared/ui/TelegramLayout";
import { csrfHeaders } from "@/shared/lib/api";
import { averageRecordedMetrics, finiteMetricOrNull } from "@/shared/lib/metricMath";

function asArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? (value as Array<Record<string, unknown>>) : [];
}

function asString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function asNumber(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

function asObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

type WorkspaceCard = {
  label: string;
  value: string;
  detail: string;
  tone?: string;
};

function childName(child: Record<string, unknown>): string {
  return (
    asString(child.student_full_name) ||
    asString(child.full_name) ||
    asString(child.name) ||
    "O'quvchi"
  );
}

function childCode(child: Record<string, unknown>): string {
  return asString(child.student_id) || asString(child.student_code) || "";
}

function childRowId(child: Record<string, unknown>): number {
  return asNumber(child.student_row_id) || asNumber(child.id);
}

function childIndicators(child: Record<string, unknown>) {
  return asArray(child.academic_indicators);
}

function childRecentLessons(child: Record<string, unknown>) {
  return asArray(child.recent_lessons).slice(0, 4);
}

function averageMetric(rows: Array<Record<string, unknown>>, key: string) {
  return averageRecordedMetrics(rows.map((row) => row[key]));
}

function formatScore(value: number | null, digits = 1) {
  if (value === null || !Number.isFinite(value)) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(digits);
}

function paymentSummary(child: Record<string, unknown>) {
  return asObject(child.payment_summary);
}

function money(value: unknown, currency: string) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return `0 ${currency}`;
  return `${Math.round(parsed).toLocaleString()} ${currency}`;
}

function workspaceCardIcon(label: string) {
  const normalized = label.toLowerCase();
  if (normalized.includes("payment")) return <CreditCard className="h-4 w-4" />;
  if (normalized.includes("support")) return <UserRound className="h-4 w-4" />;
  if (normalized.includes("progress") || normalized.includes("attendance")) return <TrendingUp className="h-4 w-4" />;
  return <GraduationCap className="h-4 w-4" />;
}

function WorkspaceSummaryCard({ card }: { card: WorkspaceCard }) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-surface p-3 shadow-card">
      <div className="flex items-center gap-2 text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground">
        {workspaceCardIcon(card.label)}
        <span className="min-w-0 break-words">{card.label}</span>
      </div>
      <p className={`mt-2 break-words text-xl font-bold leading-none ${card.tone || "text-foreground"}`}>{card.value}</p>
      <p className="mt-1 break-words text-xs text-muted-foreground">{card.detail}</p>
    </div>
  );
}

function ChildStatsCard({ child }: { child: Record<string, unknown> }) {
  const indicators = childIndicators(child);
  const lessons = childRecentLessons(child);
  const summary = paymentSummary(child);
  const currency = asString(summary.currency) || "UZS";
  const aap = averageMetric(indicators, "aap");
  const ar = averageMetric(indicators, "ar");
  const ep = averageMetric(indicators, "ep");
  const progress = finiteMetricOrNull(summary.program_completion_rate)
    ?? averageMetric(indicators, "program_completion_rate");
  const debt = Number(summary.debt_total || 0);
  const due = Number(summary.due_total || 0);
  const subjects = indicators.map((indicator) => asString(indicator.subject_display_name) || asString(indicator.subject_name)).filter(Boolean);

  return (
    <section className="overflow-hidden rounded-xl border border-foreground/10 bg-surface shadow-card">
      <div className="border-b border-foreground/8 px-4 py-4">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-sm font-bold text-primary">
            {childName(child).slice(0, 2).toUpperCase()}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="break-words font-display text-base font-bold leading-tight">{childName(child)}</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {childCode(child) ? `Code ${childCode(child)} · ` : ""}
              {asString(child.school_name) || "MSI School"}
            </p>
            {subjects.length ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {subjects.slice(0, 3).map((subject) => (
                  <span key={subject} className="rounded-md bg-muted px-2 py-1 text-[0.6875rem] font-bold text-muted-foreground">
                    {subject}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 p-4 sm:grid-cols-4">
        <Metric icon={<GraduationCap className="h-4 w-4" />} label="AAP" value={`${formatScore(aap)} / 9`} />
        <Metric icon={<Activity className="h-4 w-4" />} label="Attendance" value={ar !== null ? `${Math.round(ar)}%` : "-"} />
        <Metric icon={<TrendingUp className="h-4 w-4" />} label="Exam" value={`${formatScore(ep, 0)} / 9`} />
        <Metric icon={<BookOpen className="h-4 w-4" />} label="Progress" value={progress !== null ? `${Math.round(progress)}%` : "-"} />
      </div>

      <div className="grid gap-3 border-t border-foreground/8 p-4 lg:grid-cols-[minmax(0,1fr),minmax(16rem,0.55fr)]">
        <div>
          <h3 className="text-sm font-bold">Recent lessons</h3>
          {lessons.length ? (
            <div className="mt-2 space-y-2">
              {lessons.map((lesson, index) => (
                <div key={`${asString(lesson.date)}-${asString(lesson.lesson_number)}-${index}`} className="rounded-lg border border-foreground/8 bg-background px-3 py-2">
                  <p className="break-words text-xs font-bold">{asString(lesson.lesson_number) || "Lesson"} · {asString(lesson.subject_display_name) || asString(lesson.subject_name)}</p>
                  <p className="mt-0.5 break-words text-xs text-muted-foreground">{asString(lesson.topic) || asString(lesson.group_name) || "-"}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-2 rounded-lg border border-dashed border-foreground/10 bg-background px-3 py-6 text-center text-xs text-muted-foreground">
              No recent lesson records yet.
            </p>
          )}
        </div>

        <div className="rounded-lg border border-foreground/8 bg-background p-3">
          <h3 className="flex items-center gap-2 text-sm font-bold">
            <CreditCard className="h-4 w-4 text-muted-foreground" />
            Payments
          </h3>
          <div className="mt-3 grid gap-2">
            <PaymentLine label="Debt" value={money(debt, currency)} tone={debt > 0 ? "text-red-600" : "text-foreground"} />
            <PaymentLine label="Due" value={money(due, currency)} tone={due > 0 ? "text-amber-700" : "text-foreground"} />
            <PaymentLine label="Paid" value={money(summary.paid_total, currency)} tone="text-emerald-700" />
          </div>
        </div>
      </div>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-background p-3">
      <div className="flex items-center gap-2 text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-2 text-lg font-bold leading-none">{value}</p>
    </div>
  );
}

function PaymentLine({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-muted px-3 py-2 text-xs">
      <span className="font-semibold text-muted-foreground">{label}</span>
      <span className={`text-right font-bold ${tone}`}>{value}</span>
    </div>
  );
}

export default function ParentHome(props: Record<string, unknown>) {
  const authLogin = asString(props.authLogin) || "Ota-ona";
  const logoutUrl = asString(props.logoutUrl) || "/logout";
  const csrfToken = asString(props.csrfToken);
  const children = asArray(props.parentChildren);
  const workspaceCards = asArray(props.workspaceCards)
    .map((card) => ({
      label: asString(card.label),
      value: asString(card.value),
      detail: asString(card.detail),
      tone: asString(card.tone),
    }))
    .filter((card) => card.label && card.value);

  async function handleLogout(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      window.sessionStorage.setItem("msiManualLoginMode", "1");
    } catch {
      // The logged_out URL flag still prevents auto-login when storage is unavailable.
    }
    await fetch(logoutUrl, {
      method: "POST",
      headers: csrfHeaders(csrfToken),
      credentials: "same-origin",
    }).catch(() => {});
    window.location.href = "/?logged_out=1";
  }

  const topbar = (
    <Topbar
      title={authLogin}
      subtitle="Ota-ona kabineti / Кабинет родителя"
      leadingContent={
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          <UserRound className="h-4 w-4 text-foreground" />
        </span>
      }
      rightContent={
        <form onSubmit={handleLogout}>
          <button
            type="submit"
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-foreground/10 text-xs font-bold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 sm:w-auto sm:gap-1.5 sm:px-3"
            aria-label="Chiqish / Выйти"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Chiqish / Выйти</span>
          </button>
        </form>
      }
    />
  );

  return (
    <TelegramLayout topbar={topbar}>
      <div className="mx-auto w-full max-w-[var(--workspace-content-max-width)] py-4">
        {workspaceCards.length ? (
          <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {workspaceCards.map((card) => (
              <WorkspaceSummaryCard key={`${card.label}-${card.value}`} card={card} />
            ))}
          </div>
        ) : null}

        {children.length ? (
          <div className="space-y-4">
            <div className="mb-4">
              <h1 className="font-display text-lg font-bold">Farzandlar statistikasi / Статистика детей</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                AAP, attendance, exams, lessons, and payments are shown from the parent account.
              </p>
            </div>
            {children.map((child) => (
              <ChildStatsCard key={`${childRowId(child)}-${childCode(child)}`} child={child} />
            ))}
          </div>
        ) : (
          <section className="mt-12 rounded-xl border border-foreground/10 bg-surface p-5 text-center shadow-card">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
              <UserRound className="h-5 w-5 text-muted-foreground" />
            </span>
            <h1 className="mt-4 font-display text-lg font-bold">Farzand ulanmagan / Ребёнок не подключён</h1>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
              Administrator yuborgan yangi havolani Telegram ichida oching. Ulanish tugagach,
              kabinet avtomatik ochiladi.
            </p>
          </section>
        )}
      </div>
    </TelegramLayout>
  );
}
