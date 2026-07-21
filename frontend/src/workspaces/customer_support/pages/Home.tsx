import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  AlertTriangle,
  Archive,
  ArrowLeft,
  Banknote,
  BookOpen,
  Check,
  ChevronRight,
  CircleDollarSign,
  Copy,
  CreditCard,
  Edit3,
  GraduationCap,
  KeyRound,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Unlink,
  UserRound,
  UsersRound,
  XCircle,
} from "lucide-react";
import {
  deleteSupport,
  getSupport,
  sendSupport,
  type ParentDetail,
  type PaymentPayload,
  type SearchPayload,
  type StudentDetail,
  type SupportContext,
  type SupportDetail,
  type SupportRecordKind,
  type SupportRecordSummary,
} from "@/features/customer-support/api";
import { EmptyState } from "@/shared/ui/EmptyState";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { PageHeader } from "@/shared/ui/PageHeader";
import { RoleWorkspaceShell } from "@/shared/ui/RoleWorkspaceShell";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type Props = {
  authLogin?: string;
  csrfToken?: string;
  title?: string;
  description?: string;
};

type DialogState =
  | { type: "create-student" }
  | { type: "edit-student" }
  | { type: "edit-parent" }
  | { type: "credentials"; title: string; login: string; password: string; inviteUrl?: string }
  | { type: "reason"; action: "archive" | "reactivate" | "deactivate-parent" | "reactivate-parent" | "unlink" | "void"; targetId?: number; label: string }
  | { type: "payment"; payment?: Record<string, unknown> }
  | { type: "link-child" }
  | null;

const primaryButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-black text-primary-foreground transition-colors duration-150 hover:brightness-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none";
const secondaryButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-black text-foreground transition-colors duration-150 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/25 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none";
const dangerButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm font-black text-destructive transition-colors duration-150 hover:bg-destructive/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-destructive/30 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none";
const inputClass = "min-h-11 w-full rounded-lg border border-border bg-background px-3 text-base font-semibold text-foreground outline-none transition-colors duration-150 placeholder:text-muted-foreground/70 focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground motion-reduce:transition-none";

function asText(value: unknown) {
  return String(value ?? "").trim();
}

function asNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDate(value: unknown, includeTime = false) {
  const raw = asText(value);
  if (!raw) return "Not set";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw;
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(new Date(parsed));
}

function money(value: unknown, currency = "UZS") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "UZS",
    maximumFractionDigits: 0,
  }).format(asNumber(value));
}

function readLocation() {
  const params = new URLSearchParams(window.location.search);
  const kind = params.get("type");
  return {
    query: params.get("q") || "",
    recordType: kind === "student" || kind === "parent" ? kind : "all",
    status: params.get("status") || "all",
    schoolId: params.get("school") || "",
    selectedKind: (params.get("recordType") === "parent" ? "parent" : params.get("recordType") === "student" ? "student" : null) as SupportRecordKind | null,
    selectedId: Number(params.get("recordId") || 0) || null,
  };
}

function Field({ label, value, mono = false }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="min-w-0 rounded-lg border border-border/80 bg-background px-3 py-2.5">
      <dt className="text-[11px] font-black uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={`mt-1 break-words text-sm font-bold text-foreground ${mono ? "font-mono" : ""}`}>{value || "Not set"}</dd>
    </div>
  );
}

function Section({ title, icon, action, children }: { title: string; icon: ReactNode; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-card shadow-sm">
      <header className="flex min-h-14 flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2 className="flex min-w-0 items-center gap-2 text-sm font-black text-foreground">
          <span className="text-primary">{icon}</span>
          <span className="break-words">{title}</span>
        </h2>
        {action}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

function RecordCard({ item, selected, onSelect }: { item: SupportRecordSummary; selected: boolean; onSelect: () => void }) {
  const Icon = item.kind === "student" ? GraduationCap : UsersRound;
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`flex min-h-[6.25rem] w-full items-start gap-3 border-b border-border px-4 py-3 text-left transition-colors duration-150 last:border-b-0 hover:bg-muted/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 motion-reduce:transition-none ${selected ? "bg-primary/8" : "bg-card"}`}
    >
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${item.kind === "student" ? "bg-primary/10 text-primary" : "bg-emerald-50 text-emerald-700"}`}>
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-start justify-between gap-2">
          <span className="min-w-0 break-words text-sm font-black text-foreground">{item.display_name}</span>
          <StatusBadge status={item.status} className="shrink-0 text-[10px]" />
        </span>
        <span className="mt-1 block break-words text-xs font-semibold text-muted-foreground">{item.secondary}</span>
        <span className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-bold text-muted-foreground">
          <span>{item.school_name}</span>
          {item.outstanding > 0 ? <span className="text-amber-700">Due {money(item.outstanding)}</span> : null}
          <span>{item.linked_count} {item.kind === "student" ? "parents" : "students"}</span>
        </span>
      </span>
      <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
    </button>
  );
}

function Label({ children, htmlFor }: { children: ReactNode; htmlFor: string }) {
  return <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-black uppercase tracking-wide text-muted-foreground">{children}</label>;
}

function DetailSkeleton() {
  return (
    <div className="space-y-4" aria-label="Loading record">
      {[1, 2, 3].map((item) => <div key={item} className="h-40 animate-pulse rounded-lg border border-border bg-muted motion-reduce:animate-none" />)}
    </div>
  );
}

function ActivityList({ items }: { items: Array<Record<string, unknown>> }) {
  if (!items.length) return <p className="text-sm font-semibold text-muted-foreground">No Customer Support changes have been recorded yet.</p>;
  return (
    <ol className="space-y-3">
      {items.map((item) => (
        <li key={asText(item.id)} className="relative border-l-2 border-primary/20 pl-4">
          <span className="absolute -left-[5px] top-1.5 h-2 w-2 rounded-full bg-primary" />
          <p className="break-words text-sm font-black text-foreground">{asText(item.eventType).replace(/\./g, " · ").replace(/_/g, " ")}</p>
          <p className="mt-0.5 text-xs font-semibold text-muted-foreground">{asText(item.actor)} · {formatDate(item.createdAt, true)}</p>
        </li>
      ))}
    </ol>
  );
}

function PaymentsSection({
  detail,
  onAdd,
  onEdit,
  onSettle,
  onVoid,
}: {
  detail: StudentDetail;
  onAdd: () => void;
  onEdit: (payment: Record<string, unknown>) => void;
  onSettle: (payment: Record<string, unknown>, paid: boolean) => void;
  onVoid: (payment: Record<string, unknown>) => void;
}) {
  const payload = detail.payments;
  const items = payload.items || [];
  return (
    <Section
      title="Payments"
      icon={<CircleDollarSign className="h-4 w-4" />}
      action={<button type="button" onClick={onAdd} className={secondaryButton}><Plus className="h-4 w-4" />Add payment</button>}
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(["paid", "due", "debt", "upcoming"] as const).map((key) => (
          <div key={key} className="rounded-lg bg-muted px-3 py-2">
            <p className="text-[10px] font-black uppercase tracking-wide text-muted-foreground">{key}</p>
            <p className="mt-1 break-words text-sm font-black tabular-nums text-foreground">{money(payload.totals?.[key] || 0, payload.currency)}</p>
          </div>
        ))}
      </div>
      {items.length ? (
        <div className="mt-4 space-y-2">
          {items.map((payment) => {
            const state = asText(payment.state);
            const voided = state === "voided";
            return (
              <article key={asText(payment.id)} className={`rounded-lg border p-3 ${voided ? "border-border bg-muted/60" : "border-border bg-background"}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words text-sm font-black text-foreground">{asText(payment.subject) || "Subject"} · {asText(payment.month_label) || "Payment"}</p>
                    <p className="mt-1 text-xs font-semibold text-muted-foreground">Due {formatDate(payment.due_date)} · {money(payment.amount, asText(payment.currency) || payload.currency)}</p>
                    {voided && asText(payment.void_reason) ? <p className="mt-1 text-xs font-bold text-destructive">Voided: {asText(payment.void_reason)}</p> : null}
                  </div>
                  <StatusBadge status={state} className="text-[10px]" />
                </div>
                {!voided ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button type="button" className={secondaryButton} onClick={() => onEdit(payment)}><Edit3 className="h-4 w-4" />Edit</button>
                    <button type="button" className={secondaryButton} onClick={() => onSettle(payment, state !== "paid")}>
                      {state === "paid" ? <RefreshCw className="h-4 w-4" /> : <Check className="h-4 w-4" />}
                      {state === "paid" ? "Mark unpaid" : "Mark paid"}
                    </button>
                    <button type="button" className={dangerButton} onClick={() => onVoid(payment)}><XCircle className="h-4 w-4" />Void</button>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      ) : <p className="mt-4 text-sm font-semibold text-muted-foreground">No payment records.</p>}
    </Section>
  );
}

function StudentView({
  detail,
  onEdit,
  onReset,
  onLifecycle,
  onInvite,
  onAddPayment,
  onEditPayment,
  onSettle,
  onVoid,
}: {
  detail: StudentDetail;
  onEdit: () => void;
  onReset: () => void;
  onLifecycle: (active: boolean) => void;
  onInvite: () => void;
  onAddPayment: () => void;
  onEditPayment: (payment: Record<string, unknown>) => void;
  onSettle: (payment: Record<string, unknown>, paid: boolean) => void;
  onVoid: (payment: Record<string, unknown>) => void;
}) {
  const profile = detail.profile;
  const archived = asText(profile.status) === "archived";
  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            {asText(profile.photo_url) ? <img src={asText(profile.photo_url)} alt="" className="h-14 w-14 shrink-0 rounded-lg border border-border object-cover" /> : <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><GraduationCap className="h-6 w-6" /></span>}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="break-words text-xl font-black text-foreground">{asText(profile.full_name)}</h1>
                <StatusBadge status={asText(profile.status)} />
              </div>
              <p className="mt-1 break-words text-sm font-semibold text-muted-foreground">{asText(profile.student_code)} · {asText(profile.school_name) || "School not set"}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onEdit} className={secondaryButton}><Edit3 className="h-4 w-4" />Edit profile</button>
            <button type="button" onClick={() => onLifecycle(archived)} className={archived ? primaryButton : dangerButton}>
              {archived ? <RefreshCw className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
              {archived ? "Reactivate" : "Archive"}
            </button>
          </div>
        </div>
      </section>

      <Section title="Profile" icon={<UserRound className="h-4 w-4" />}>
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Field label="Full name" value={asText(profile.full_name)} />
          <Field label="Student code" value={asText(profile.student_code)} mono />
          <Field label="School" value={asText(profile.school_name)} />
          <Field label="Phone" value={asText(profile.phone)} />
          <Field label="Telegram" value={asText(profile.telegram_username) ? `@${asText(profile.telegram_username)}` : "Not linked"} />
          <Field label="Updated" value={formatDate(profile.updated_at, true)} />
        </dl>
        {asText(profile.profile_description) ? <p className="mt-3 rounded-lg bg-muted px-3 py-2 text-sm leading-6 text-foreground">{asText(profile.profile_description)}</p> : null}
      </Section>

      <Section title="Account access" icon={<KeyRound className="h-4 w-4" />} action={<button type="button" onClick={onReset} className={secondaryButton}><KeyRound className="h-4 w-4" />Reset access</button>}>
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <Field label="Login" value={asText(profile.login)} mono />
          <Field label="Account status" value={<StatusBadge status={asText(profile.account_status)} className="text-[10px]" />} />
          <Field label="Last login" value={formatDate(profile.last_login_at, true)} />
        </dl>
        <p className="mt-3 text-xs font-semibold leading-5 text-muted-foreground">Passwords are protected and cannot be viewed. A reset creates a temporary password, invalidates existing sessions, and forces a password change.</p>
      </Section>

      <Section title="Family" icon={<UsersRound className="h-4 w-4" />} action={<button type="button" onClick={onInvite} className={secondaryButton}><Send className="h-4 w-4" />Create parent invite</button>}>
        {detail.parents.length ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {detail.parents.map((parent) => (
              <article key={asText(parent.id)} className="rounded-lg border border-border bg-background p-3">
                <p className="break-words text-sm font-black text-foreground">{asText(parent.display_name) || "Parent"}</p>
                <p className="mt-1 break-words text-xs font-semibold text-muted-foreground">{asText(parent.phone) || asText(parent.telegram_username) || "No contact"}</p>
              </article>
            ))}
          </div>
        ) : <p className="text-sm font-semibold text-muted-foreground">No parent is linked. Create an invitation to establish a verified link.</p>}
      </Section>

      <Section title="Academic snapshot — read only" icon={<BookOpen className="h-4 w-4" />}>
        {detail.academic.length ? (
          <div className="grid gap-2 md:grid-cols-2">
            {detail.academic.map((item) => (
              <article key={`${asText(item.id)}-${asText(item.subject_id)}`} className="rounded-lg border border-border bg-background p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="break-words text-sm font-black text-foreground">{asText(item.subject_name)}</p>
                    <p className="mt-1 break-words text-xs font-semibold text-muted-foreground">{asText(item.group_name)}</p>
                  </div>
                  <StatusBadge status={asText(item.status)} className="text-[10px]" />
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
                  <div><dt className="text-[10px] font-bold text-muted-foreground">HOMEWORK</dt><dd className="mt-1 text-sm font-black">{asNumber(item.homework_average).toFixed(1)}</dd></div>
                  <div><dt className="text-[10px] font-bold text-muted-foreground">EXAM</dt><dd className="mt-1 text-sm font-black">{asNumber(item.exam_average).toFixed(1)}</dd></div>
                  <div><dt className="text-[10px] font-bold text-muted-foreground">ATTENDANCE</dt><dd className="mt-1 text-sm font-black">{asNumber(item.attendanceRate)}%</dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : <p className="text-sm font-semibold text-muted-foreground">Not enrolled. Academic Department assigns subjects and groups.</p>}
      </Section>

      <PaymentsSection detail={detail} onAdd={onAddPayment} onEdit={onEditPayment} onSettle={onSettle} onVoid={onVoid} />
      <Section title="Activity" icon={<ShieldCheck className="h-4 w-4" />}><ActivityList items={detail.activity} /></Section>
    </div>
  );
}

function ParentView({
  detail,
  onEdit,
  onLink,
  onUnlink,
  onLifecycle,
}: {
  detail: ParentDetail;
  onEdit: () => void;
  onLink: () => void;
  onUnlink: (student: Record<string, unknown>) => void;
  onLifecycle: (active: boolean) => void;
}) {
  const profile = detail.profile;
  const outstanding = detail.children.reduce((sum, child) => sum + asNumber(child.outstanding), 0);
  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="break-words text-xl font-black text-foreground">{asText(profile.display_name) || "Parent"}</h1>
              <StatusBadge status={asText(profile.status)} />
            </div>
            <p className="mt-1 break-words text-sm font-semibold text-muted-foreground">{asText(profile.phone) || asText(profile.telegram_username) || "No contact details"}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={onEdit} className={secondaryButton}><Edit3 className="h-4 w-4" />Edit profile</button>
            <button type="button" onClick={() => onLifecycle(asText(profile.status) !== "active")} className={asText(profile.status) === "active" ? dangerButton : primaryButton}>
              {asText(profile.status) === "active" ? <Archive className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
              {asText(profile.status) === "active" ? "Deactivate" : "Reactivate"}
            </button>
          </div>
        </div>
      </section>

      <Section title="Profile and access" icon={<UserRound className="h-4 w-4" />}>
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <Field label="Full name" value={asText(profile.display_name)} />
          <Field label="Phone" value={asText(profile.phone)} />
          <Field label="Telegram" value={asText(profile.telegram_username) ? `@${asText(profile.telegram_username)}` : "Not linked"} />
          <Field label="Language" value={asText(profile.preferred_language).toUpperCase()} />
          <Field label="Account status" value={<StatusBadge status={asText(profile.account_status)} className="text-[10px]" />} />
          <Field label="Last login" value={formatDate(profile.last_login_at, true)} />
        </dl>
      </Section>

      <Section title="Linked students" icon={<GraduationCap className="h-4 w-4" />} action={<button type="button" onClick={onLink} className={secondaryButton}><Link2 className="h-4 w-4" />Link student</button>}>
        <div className="mb-3 flex flex-wrap gap-2">
          <span className="rounded-lg bg-muted px-3 py-2 text-xs font-black text-foreground">{detail.children.length} visible students</span>
          <span className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-black text-amber-800">Outstanding {money(outstanding)}</span>
          {detail.hiddenChildCount > 0 ? <span className="rounded-lg bg-muted px-3 py-2 text-xs font-black text-muted-foreground">{detail.hiddenChildCount} outside your school scope</span> : null}
        </div>
        {detail.children.length ? (
          <div className="space-y-2">
            {detail.children.map((student) => (
              <article key={asText(student.id)} className="flex flex-col gap-3 rounded-lg border border-border bg-background p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="break-words text-sm font-black text-foreground">{asText(student.full_name)}</p>
                  <p className="mt-1 break-words text-xs font-semibold text-muted-foreground">{asText(student.student_code)} · {asText(student.school_name)} · Due {money(student.outstanding)}</p>
                </div>
                <button type="button" onClick={() => onUnlink(student)} className={dangerButton}><Unlink className="h-4 w-4" />Unlink</button>
              </article>
            ))}
          </div>
        ) : <p className="text-sm font-semibold text-muted-foreground">No visible linked students.</p>}
      </Section>

      <Section title="Activity" icon={<ShieldCheck className="h-4 w-4" />}><ActivityList items={detail.activity} /></Section>
    </div>
  );
}

function LinkChildModal({
  excludedIds,
  saving,
  onClose,
  onLink,
}: {
  excludedIds: number[];
  saving: boolean;
  onClose: () => void;
  onLink: (studentId: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<SupportRecordSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  const excludedKey = excludedIds.join(",");

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      const params = new URLSearchParams({ type: "student", status: "active", limit: "20" });
      if (query.trim()) params.set("q", query.trim());
      getSupport<SearchPayload>(`/records?${params}`, controller.signal)
        .then((payload) => setItems(payload.items.filter((item) => !excludedIds.includes(item.id))))
        .catch((error) => {
          if ((error as Error).name !== "AbortError") setItems([]);
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
    // The stable key avoids rerunning for a new array with identical ids.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [excludedKey, query]);

  return (
    <Modal title="Link student" subtitle="Search is limited to students inside your allowed school scope." onClose={onClose} size="md" mobileMode="fullscreen">
      <ModalBody>
        <Label htmlFor="link-student-search">Search student</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input id="link-student-search" value={query} onChange={(event) => setQuery(event.target.value)} className={`${inputClass} pl-10`} placeholder="Name, student code, or phone" autoFocus />
        </div>
        <div className="miniapp-scroll mt-4 max-h-[50dvh] overflow-y-auto rounded-lg border border-border">
          {loading ? <div className="flex min-h-28 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-primary motion-reduce:animate-none" /></div> : items.length ? items.map((item) => (
            <button key={item.id} type="button" onClick={() => setSelected(item.id)} aria-pressed={selected === item.id} className={`flex min-h-16 w-full items-center justify-between gap-3 border-b border-border px-3 py-2 text-left last:border-b-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 ${selected === item.id ? "bg-primary/10" : "bg-background hover:bg-muted"}`}>
              <span className="min-w-0"><span className="block break-words text-sm font-black">{item.display_name}</span><span className="mt-1 block break-words text-xs font-semibold text-muted-foreground">{item.secondary} · {item.school_name}</span></span>
              {selected === item.id ? <Check className="h-4 w-4 shrink-0 text-primary" /> : <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />}
            </button>
          )) : <p className="px-4 py-8 text-center text-sm font-semibold text-muted-foreground">No available students match this search.</p>}
        </div>
      </ModalBody>
      <ModalFooter><div className="flex justify-end gap-2"><button type="button" onClick={onClose} className={secondaryButton}>Cancel</button><button type="button" disabled={!selected || saving} onClick={() => selected && onLink(selected)} className={primaryButton}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}Link student</button></div></ModalFooter>
    </Modal>
  );
}

export default function CustomerSupportWorkspace({
  authLogin = "",
  csrfToken = "",
  title = "Customer Records",
  description = "Find students and parents, restore account access, and manage payment records.",
}: Props) {
  const initial = useMemo(readLocation, []);
  const [context, setContext] = useState<SupportContext | null>(null);
  const [query, setQuery] = useState(initial.query);
  const [debouncedQuery, setDebouncedQuery] = useState(initial.query);
  const [recordType, setRecordType] = useState(initial.recordType);
  const [status, setStatus] = useState(initial.status);
  const [schoolId, setSchoolId] = useState(initial.schoolId);
  const [records, setRecords] = useState<SupportRecordSummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [selectedKind, setSelectedKind] = useState<SupportRecordKind | null>(initial.selectedKind);
  const [selectedId, setSelectedId] = useState<number | null>(initial.selectedId);
  const [detail, setDetail] = useState<SupportDetail | null>(null);
  const [loadingContext, setLoadingContext] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dialog, setDialog] = useState<DialogState>(null);
  const [requestError, setRequestError] = useState("");
  const [settlementTarget, setSettlementTarget] = useState<{ payment: Record<string, unknown>; paid: boolean } | null>(null);
  const { toast, showToast, clearToast } = useFloatingToast();
  const listScrollRef = useRef<HTMLDivElement>(null);

  const updateUrl = useCallback((push = false, overrides: Partial<ReturnType<typeof readLocation>> = {}) => {
    const values = {
      query,
      recordType,
      status,
      schoolId,
      selectedKind,
      selectedId,
      ...overrides,
    };
    const params = new URLSearchParams();
    if (values.query) params.set("q", values.query);
    if (values.recordType !== "all") params.set("type", values.recordType);
    if (values.status !== "all") params.set("status", values.status);
    if (values.schoolId) params.set("school", values.schoolId);
    if (values.selectedKind && values.selectedId) {
      params.set("recordType", values.selectedKind);
      params.set("recordId", String(values.selectedId));
    }
    const url = `${window.location.pathname}${params.size ? `?${params}` : ""}`;
    window.history[push ? "pushState" : "replaceState"]({}, "", url);
  }, [query, recordType, status, schoolId, selectedKind, selectedId]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onPopState = () => {
      const state = readLocation();
      setQuery(state.query);
      setDebouncedQuery(state.query);
      setRecordType(state.recordType);
      setStatus(state.status);
      setSchoolId(state.schoolId);
      setSelectedKind(state.selectedKind);
      setSelectedId(state.selectedId);
      if (!state.selectedId) setDetail(null);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingContext(true);
    getSupport<SupportContext>("/context", controller.signal)
      .then(setContext)
      .catch((error) => setRequestError(error instanceof Error ? error.message : "Could not load Customer Support."))
      .finally(() => setLoadingContext(false));
    return () => controller.abort();
  }, []);

  const loadRecords = useCallback(async (append = false) => {
    const controller = new AbortController();
    append ? setLoadingMore(true) : setLoadingRecords(true);
    if (!append) setRequestError("");
    const params = new URLSearchParams({ type: recordType, status, limit: "25" });
    if (debouncedQuery) params.set("q", debouncedQuery);
    if (schoolId) params.set("schoolId", schoolId);
    if (append && nextCursor) params.set("cursor", nextCursor);
    try {
      const payload = await getSupport<SearchPayload>(`/records?${params}`, controller.signal);
      setRecords((current) => append ? [...current, ...payload.items] : payload.items);
      setNextCursor(payload.nextCursor || null);
      if (!append) listScrollRef.current?.scrollTo({ top: 0 });
    } catch (error) {
      if ((error as Error).name !== "AbortError") setRequestError(error instanceof Error ? error.message : "Could not load records.");
    } finally {
      append ? setLoadingMore(false) : setLoadingRecords(false);
    }
    return () => controller.abort();
  }, [debouncedQuery, nextCursor, recordType, schoolId, status]);

  useEffect(() => {
    void loadRecords(false);
    updateUrl(false, { selectedKind, selectedId });
    // nextCursor intentionally does not trigger a new first-page request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, recordType, status, schoolId]);

  const loadDetail = useCallback(async (kind: SupportRecordKind, id: number) => {
    setLoadingDetail(true);
    setRequestError("");
    try {
      const payload = await getSupport<SupportDetail>(`/${kind === "student" ? "students" : "parents"}/${id}`);
      setDetail(payload);
    } catch (error) {
      setDetail(null);
      setRequestError(error instanceof Error ? error.message : "Could not load this record.");
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedKind || !selectedId) return;
    void loadDetail(selectedKind, selectedId);
  }, [loadDetail, selectedId, selectedKind]);

  function selectRecord(item: SupportRecordSummary) {
    setSelectedKind(item.kind);
    setSelectedId(item.id);
    setDetail(null);
    updateUrl(true, { selectedKind: item.kind, selectedId: item.id });
  }

  function closeDetail() {
    setSelectedKind(null);
    setSelectedId(null);
    setDetail(null);
    updateUrl(false, { selectedKind: null, selectedId: null });
  }

  async function runMutation<T>(operation: () => Promise<T>, onSuccess: (result: T) => void, message: string) {
    setSaving(true);
    setRequestError("");
    try {
      const result = await operation();
      setDialog(null);
      onSuccess(result);
      showToast(message, "success");
      void loadRecords(false);
    } catch (error) {
      const messageText = error instanceof Error ? error.message : "The change could not be saved.";
      setRequestError(messageText);
      showToast(messageText, "error");
    } finally {
      setSaving(false);
    }
  }

  function currentProfile() {
    return detail?.profile || {};
  }

  async function submitCreateStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await runMutation(
      () => sendSupport<{ record: StudentDetail; credentials: { login: string; temporaryPassword: string } }>("/students", "POST", {
        fullName: data.get("fullName"),
        schoolId: Number(data.get("schoolId")),
        phone: data.get("phone"),
        photoUrl: data.get("photoUrl"),
        profileDescription: data.get("profileDescription"),
      }, csrfToken),
      (result) => {
        setDetail(result.record);
        const id = asNumber(result.record.profile.id);
        setSelectedKind("student");
        setSelectedId(id);
        updateUrl(true, { selectedKind: "student", selectedId: id });
        setDialog({ type: "credentials", title: "Student account created", login: result.credentials.login, password: result.credentials.temporaryPassword });
      },
      "Student created.",
    );
  }

  async function submitEditRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) return;
    const data = new FormData(event.currentTarget);
    const profile = detail.profile;
    if (detail.kind === "student") {
      await runMutation(
        () => sendSupport<StudentDetail>(`/students/${asNumber(profile.id)}`, "PATCH", {
          expectedVersion: asNumber(profile.version),
          fullName: data.get("fullName"),
          schoolId: Number(data.get("schoolId")),
          phone: data.get("phone"),
          photoUrl: data.get("photoUrl"),
          profileDescription: data.get("profileDescription"),
          status: data.get("status"),
          reason: "Customer Support profile correction",
        }, csrfToken),
        setDetail,
        "Student profile updated.",
      );
    } else {
      await runMutation(
        () => sendSupport<ParentDetail>(`/parents/${asNumber(profile.id)}`, "PATCH", {
          expectedVersion: asNumber(profile.version),
          displayName: data.get("displayName"),
          phone: data.get("phone"),
          telegramUsername: data.get("telegramUsername"),
          preferredLanguage: data.get("preferredLanguage"),
          reason: "Customer Support profile correction",
        }, csrfToken),
        setDetail,
        "Parent profile updated.",
      );
    }
  }

  async function submitReason(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!dialog || dialog.type !== "reason" || !detail) return;
    const reason = asText(new FormData(event.currentTarget).get("reason"));
    const profile = detail.profile;
    if (dialog.action === "archive" || dialog.action === "reactivate") {
      const action = dialog.action;
      await runMutation(
        () => sendSupport<StudentDetail>(`/students/${asNumber(profile.id)}/${action === "archive" ? "archive" : "reactivate"}`, "POST", { expectedVersion: asNumber(profile.version), reason }, csrfToken),
        setDetail,
        action === "archive" ? "Student archived." : "Student reactivated.",
      );
    } else if (dialog.action === "deactivate-parent" || dialog.action === "reactivate-parent") {
      const active = dialog.action === "reactivate-parent";
      await runMutation(
        () => sendSupport<ParentDetail>(`/parents/${asNumber(profile.id)}/${active ? "reactivate" : "deactivate"}`, "POST", { expectedVersion: asNumber(profile.version), reason }, csrfToken),
        setDetail,
        active ? "Parent reactivated." : "Parent deactivated.",
      );
    } else if (dialog.action === "unlink" && dialog.targetId) {
      await runMutation(
        () => deleteSupport<ParentDetail>(`/parents/${asNumber(profile.id)}/children/${dialog.targetId}?reason=${encodeURIComponent(reason)}&expectedVersion=${asNumber(profile.version)}`, csrfToken),
        setDetail,
        "Student unlinked.",
      );
    } else if (dialog.action === "void" && dialog.targetId && detail.kind === "student") {
      const payment = detail.payments.items.find((item) => asNumber(item.id) === dialog.targetId);
      if (!payment) return;
      await runMutation(
        () => sendSupport<PaymentPayload>(`/payments/${dialog.targetId}/void`, "POST", { expectedVersion: asNumber(payment.version), reason }, csrfToken),
        (payments) => setDetail({ ...detail, payments }),
        "Payment voided.",
      );
    }
  }

  async function resetAccess() {
    if (!detail || detail.kind !== "student") return;
    const id = asNumber(detail.profile.id);
    await runMutation(
      () => sendSupport<{ record: StudentDetail; credentials: { login: string; temporaryPassword: string } }>(`/students/${id}/reset-access`, "POST", { expectedVersion: asNumber(detail.profile.version) }, csrfToken),
      (result) => {
        setDetail(result.record);
        setDialog({ type: "credentials", title: "Temporary access generated", login: result.credentials.login, password: result.credentials.temporaryPassword });
      },
      "Student access reset.",
    );
  }

  async function createInvite() {
    if (!detail || detail.kind !== "student") return;
    const id = asNumber(detail.profile.id);
    await runMutation(
      () => sendSupport<{ inviteUrl: string }>(`/students/${id}/parent-invites`, "POST", { expectedVersion: asNumber(detail.profile.version) }, csrfToken),
      (result) => setDialog({ type: "credentials", title: "Parent invitation created", login: "Invitation link", password: "", inviteUrl: result.inviteUrl }),
      "Parent invitation created.",
    );
  }

  async function submitPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail || detail.kind !== "student" || !dialog || dialog.type !== "payment") return;
    const data = new FormData(event.currentTarget);
    const existing = dialog.payment;
    const body = {
      ...(existing ? { expectedVersion: asNumber(existing.version) } : { expectedVersion: asNumber(detail.profile.version), subjectId: Number(data.get("subjectId")) }),
      monthLabel: data.get("monthLabel"),
      amount: Number(data.get("amount")),
      currency: data.get("currency"),
      dueDate: data.get("dueDate"),
      ...(existing ? {} : { paidAt: data.get("paidAt") }),
      notes: data.get("notes"),
      reason: existing ? "Customer Support payment correction" : undefined,
    };
    const path = existing ? `/payments/${asNumber(existing.id)}` : `/students/${asNumber(detail.profile.id)}/payments`;
    await runMutation(
      () => sendSupport<PaymentPayload>(path, existing ? "PATCH" : "POST", body, csrfToken),
      (payments) => setDetail({ ...detail, payments }),
      existing ? "Payment updated." : "Payment created.",
    );
  }

  async function confirmSettlement() {
    if (!settlementTarget || !detail || detail.kind !== "student") return;
    const { payment, paid } = settlementTarget;
    await runMutation(
      () => sendSupport<PaymentPayload>(`/payments/${asNumber(payment.id)}/settlement`, "POST", { expectedVersion: asNumber(payment.version), paid, paidAt: paid ? new Date().toISOString().slice(0, 10) : "", reason: paid ? "Payment confirmed by Customer Support" : "Settlement correction by Customer Support" }, csrfToken),
      (payments) => {
        setDetail({ ...detail, payments });
        setSettlementTarget(null);
      },
      paid ? "Payment marked paid." : "Payment marked unpaid.",
    );
  }

  async function linkChild(studentId: number) {
    if (!detail || detail.kind !== "parent") return;
    await runMutation(
      () => sendSupport<ParentDetail>(`/parents/${asNumber(detail.profile.id)}/children`, "POST", { studentId, expectedVersion: asNumber(detail.profile.version) }, csrfToken),
      setDetail,
      "Student linked.",
    );
  }

  function copy(value: string, label: string) {
    void navigator.clipboard.writeText(value).then(() => showToast(`${label} copied.`, "success"));
  }

  const activeSubjects = detail?.kind === "student"
    ? detail.academic.filter((item) => asText(item.status) === "active")
    : [];
  const navItems = useMemo(() => [
    { key: "records", label: "Records", href: "/customer-support", icon: UsersRound },
  ] as const, []);

  return (
    <RoleWorkspaceShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active="records"
      homeHref="/customer-support"
      navItems={navItems}
      roleLabel="Customer Support"
      sectionLabel="Customer Support"
      workspaceLabel="Customer Support"
      mobileNavigationMode="drawer"
      desktopSidebarMode="collapsible"
      desktopSidebarInitialState="adaptive"
      desktopSidebarStorageKey="msi:customer-support:sidebar:v1"
      maxWidthClass="max-w-[100rem]"
      sectionClassName="gap-0"
    >
      <div className="flex min-w-0 flex-col gap-4 overflow-x-hidden">
        <PageHeader
          title={title}
          subtitle={description}
          badge={<span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-black uppercase tracking-wide text-primary">Customer Support</span>}
          actions={<span className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground"><ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" /><span className="truncate">{authLogin}</span></span>}
        />

        <section className="sticky top-0 z-20 rounded-lg border border-border bg-card/95 p-3 shadow-card backdrop-blur sm:p-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(18rem,1fr)_11rem_12rem_12rem_auto] lg:items-end">
            <div>
              <Label htmlFor="support-search">Search records</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input id="support-search" value={query} onChange={(event) => setQuery(event.target.value)} className={`${inputClass} pl-10`} placeholder="Name, code, phone, Telegram…" autoComplete="off" />
              </div>
            </div>
            <div><Label htmlFor="record-type">Record type</Label><select id="record-type" value={recordType} onChange={(event) => setRecordType(event.target.value as typeof recordType)} className={inputClass}><option value="all">All records</option><option value="student">Students</option><option value="parent">Parents</option></select></div>
            <div><Label htmlFor="record-status">Status</Label><select id="record-status" value={status} onChange={(event) => setStatus(event.target.value)} className={inputClass}><option value="all">All statuses</option><option value="active">Active</option><option value="disabled">Disabled</option><option value="archived">Archived</option></select></div>
            <div><Label htmlFor="record-school">School</Label><select id="record-school" value={schoolId} onChange={(event) => setSchoolId(event.target.value)} className={inputClass} disabled={loadingContext}><option value="">All allowed schools</option>{context?.schools.map((school) => <option key={school.id} value={school.id}>{school.school_name}</option>)}</select></div>
            <button type="button" className={primaryButton} onClick={() => setDialog({ type: "create-student" })}><Plus className="h-4 w-4" />New student</button>
          </div>
        </section>

        {requestError ? <div className="flex items-start gap-2 rounded-lg border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm font-bold text-destructive" role="alert"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><span className="break-words">{requestError}</span></div> : null}

        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]">
          <section className={`${selectedId ? "hidden lg:flex" : "flex"} min-h-[28rem] min-w-0 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-card lg:max-h-[calc(100dvh-14rem)]`} aria-label="Search results">
            <header className="flex min-h-14 items-center justify-between border-b border-border px-4 py-3">
              <div><h2 className="text-sm font-black">Records</h2><p className="text-xs font-semibold text-muted-foreground">{loadingRecords ? "Searching…" : `${records.length} loaded`}</p></div>
              {loadingRecords ? <Loader2 className="h-4 w-4 animate-spin text-primary motion-reduce:animate-none" /> : null}
            </header>
            <div ref={listScrollRef} className="miniapp-scroll min-h-0 flex-1 overflow-y-auto">
              {loadingRecords && !records.length ? <div className="space-y-px">{[1, 2, 3, 4].map((item) => <div key={item} className="h-24 animate-pulse border-b border-border bg-muted motion-reduce:animate-none" />)}</div> : records.length ? records.map((item) => <RecordCard key={`${item.kind}-${item.id}`} item={item} selected={selectedKind === item.kind && selectedId === item.id} onSelect={() => selectRecord(item)} />) : <EmptyState title="No matching records" detail="Try another name, phone number, school, or status." icon={<Search className="h-5 w-5" />} className="m-4" />}
            </div>
            {nextCursor ? <footer className="border-t border-border p-3"><button type="button" onClick={() => void loadRecords(true)} disabled={loadingMore} className={`${secondaryButton} w-full`}>{loadingMore ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Plus className="h-4 w-4" />}Load more</button></footer> : null}
          </section>

          <section className={`${selectedId ? "block" : "hidden lg:block"} min-w-0`} aria-label="Selected record">
            {selectedId ? <button type="button" onClick={closeDetail} className={`${secondaryButton} mb-3 lg:hidden`}><ArrowLeft className="h-4 w-4" />Back to records</button> : null}
            {loadingDetail ? <DetailSkeleton /> : detail?.kind === "student" ? (
              <StudentView
                detail={detail}
                onEdit={() => setDialog({ type: "edit-student" })}
                onReset={() => void resetAccess()}
                onLifecycle={(active) => setDialog({ type: "reason", action: active ? "reactivate" : "archive", label: active ? "Reactivate student" : "Archive student" })}
                onInvite={() => void createInvite()}
                onAddPayment={() => setDialog({ type: "payment" })}
                onEditPayment={(payment) => setDialog({ type: "payment", payment })}
                onSettle={(payment, paid) => setSettlementTarget({ payment, paid })}
                onVoid={(payment) => setDialog({ type: "reason", action: "void", targetId: asNumber(payment.id), label: "Void payment" })}
              />
            ) : detail?.kind === "parent" ? (
              <ParentView
                detail={detail}
                onEdit={() => setDialog({ type: "edit-parent" })}
                onLink={() => setDialog({ type: "link-child" })}
                onUnlink={(student) => setDialog({ type: "reason", action: "unlink", targetId: asNumber(student.id), label: `Unlink ${asText(student.full_name)}` })}
                onLifecycle={(active) => setDialog({ type: "reason", action: active ? "reactivate-parent" : "deactivate-parent", label: active ? "Reactivate parent" : "Deactivate parent" })}
              />
            ) : !selectedId ? <EmptyState title="Select a student or parent" detail="Search and open a record to view account, family, academic, and payment details." icon={<UsersRound className="h-5 w-5" />} /> : null}
          </section>
        </div>
      </div>

      {dialog?.type === "create-student" ? (
        <Modal title="Create student" subtitle="Creates the canonical student and login without changing Academic enrollment." onClose={() => setDialog(null)} size="md" mobileMode="fullscreen">
          <form onSubmit={submitCreateStudent} className="contents">
            <ModalBody><div className="space-y-4"><div><Label htmlFor="create-name">Full name</Label><input id="create-name" name="fullName" required minLength={2} className={inputClass} autoFocus /></div><div><Label htmlFor="create-school">School</Label><select id="create-school" name="schoolId" required className={inputClass} defaultValue={schoolId || ""}><option value="" disabled>Select school</option>{context?.schools.map((school) => <option key={school.id} value={school.id}>{school.school_name}</option>)}</select></div><div><Label htmlFor="create-phone">Phone</Label><input id="create-phone" name="phone" type="tel" className={inputClass} /></div><div><Label htmlFor="create-photo">Photo URL</Label><input id="create-photo" name="photoUrl" type="url" className={inputClass} /></div><div><Label htmlFor="create-description">Profile description</Label><textarea id="create-description" name="profileDescription" rows={4} className={`${inputClass} py-3`} /></div><p className="rounded-lg bg-primary/8 p-3 text-xs font-semibold leading-5 text-foreground">Academic subjects and groups are intentionally assigned by Academic Department after account creation.</p></div></ModalBody>
            <ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButton} onClick={() => setDialog(null)}>Cancel</button><button type="submit" disabled={saving} className={primaryButton}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}Create student</button></div></ModalFooter>
          </form>
        </Modal>
      ) : null}

      {dialog?.type === "edit-student" && detail?.kind === "student" ? (
        <Modal title="Edit student profile" onClose={() => setDialog(null)} size="md" mobileMode="fullscreen"><form onSubmit={submitEditRecord} className="contents"><ModalBody><div className="space-y-4"><div><Label htmlFor="student-name">Full name</Label><input id="student-name" name="fullName" required defaultValue={asText(detail.profile.full_name)} className={inputClass} /></div><div><Label htmlFor="student-school">School</Label><select id="student-school" name="schoolId" defaultValue={asText(detail.profile.school_id)} className={inputClass}>{context?.schools.map((school) => <option key={school.id} value={school.id}>{school.school_name}</option>)}</select><p className="mt-1 text-xs font-semibold text-muted-foreground">School changes are blocked while active enrollments exist.</p></div><div><Label htmlFor="student-phone">Phone</Label><input id="student-phone" name="phone" type="tel" defaultValue={asText(detail.profile.phone)} className={inputClass} /></div><div><Label htmlFor="student-photo">Photo URL</Label><input id="student-photo" name="photoUrl" type="url" defaultValue={asText(detail.profile.photo_url)} className={inputClass} /></div><div><Label htmlFor="student-status">Access status</Label><select id="student-status" name="status" defaultValue={asText(detail.profile.status)} className={inputClass}><option value="active">Active</option><option value="disabled">Disabled</option></select></div><div><Label htmlFor="student-description">Profile description</Label><textarea id="student-description" name="profileDescription" defaultValue={asText(detail.profile.profile_description)} rows={4} className={`${inputClass} py-3`} /></div></div></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" onClick={() => setDialog(null)} className={secondaryButton}>Cancel</button><button type="submit" disabled={saving} className={primaryButton}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}Save changes</button></div></ModalFooter></form></Modal>
      ) : null}

      {dialog?.type === "edit-parent" && detail?.kind === "parent" ? (
        <Modal title="Edit parent profile" onClose={() => setDialog(null)} size="md" mobileMode="fullscreen"><form onSubmit={submitEditRecord} className="contents"><ModalBody><div className="space-y-4"><div><Label htmlFor="parent-name">Full name</Label><input id="parent-name" name="displayName" required defaultValue={asText(detail.profile.display_name)} className={inputClass} /></div><div><Label htmlFor="parent-phone">Phone</Label><input id="parent-phone" name="phone" type="tel" defaultValue={asText(detail.profile.phone)} className={inputClass} /></div><div><Label htmlFor="parent-telegram">Telegram username</Label><input id="parent-telegram" name="telegramUsername" defaultValue={asText(detail.profile.telegram_username)} className={inputClass} /></div><div><Label htmlFor="parent-language">Preferred language</Label><select id="parent-language" name="preferredLanguage" defaultValue={asText(detail.profile.preferred_language) || "ru"} className={inputClass}><option value="uz">Uzbek</option><option value="ru">Russian</option><option value="en">English</option></select></div></div></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" onClick={() => setDialog(null)} className={secondaryButton}>Cancel</button><button type="submit" disabled={saving} className={primaryButton}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}Save changes</button></div></ModalFooter></form></Modal>
      ) : null}

      {dialog?.type === "reason" ? (
        <Modal title={dialog.label} subtitle="This action is audited and requires a reason." onClose={() => setDialog(null)} size="sm"><form onSubmit={submitReason} className="contents"><ModalBody><div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold leading-6 text-amber-900"><AlertTriangle className="mr-2 inline h-4 w-4" />Confirm the record and explain why this change is needed.</div><div className="mt-4"><Label htmlFor="action-reason">Reason</Label><textarea id="action-reason" name="reason" required minLength={2} rows={4} className={`${inputClass} py-3`} autoFocus /></div></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" onClick={() => setDialog(null)} className={secondaryButton}>Cancel</button><button type="submit" disabled={saving} className={dialog.action === "reactivate" || dialog.action === "reactivate-parent" ? primaryButton : dangerButton}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}Proceed</button></div></ModalFooter></form></Modal>
      ) : null}

      {dialog?.type === "credentials" ? (
        <Modal title={dialog.title} subtitle="Sensitive access details are shown only in this window." onClose={() => setDialog(null)} size="sm" closeOnOutsideClick={false}><ModalBody><div className="rounded-lg border border-amber-200 bg-amber-50 p-3"><p className="text-xs font-black uppercase tracking-wide text-amber-900">Shown once</p>{dialog.inviteUrl ? <div className="mt-3"><Label htmlFor="generated-invite">Invitation link</Label><div className="flex gap-2"><input id="generated-invite" readOnly value={dialog.inviteUrl} className={`${inputClass} font-mono text-sm`} /><button type="button" className={secondaryButton} onClick={() => copy(dialog.inviteUrl || "", "Invitation link")} aria-label="Copy invitation link"><Copy className="h-4 w-4" /></button></div></div> : <><div className="mt-3"><Label htmlFor="generated-login">Login</Label><div className="flex gap-2"><input id="generated-login" readOnly value={dialog.login} className={`${inputClass} font-mono`} /><button type="button" className={secondaryButton} onClick={() => copy(dialog.login, "Login")} aria-label="Copy login"><Copy className="h-4 w-4" /></button></div></div><div className="mt-3"><Label htmlFor="generated-password">Temporary password</Label><div className="flex gap-2"><input id="generated-password" readOnly value={dialog.password} className={`${inputClass} font-mono`} /><button type="button" className={secondaryButton} onClick={() => copy(dialog.password, "Password")} aria-label="Copy temporary password"><Copy className="h-4 w-4" /></button></div></div></>}</div></ModalBody><ModalFooter><button type="button" className={`${primaryButton} w-full`} onClick={() => setDialog(null)}>I have saved it</button></ModalFooter></Modal>
      ) : null}

      {dialog?.type === "payment" && detail?.kind === "student" ? (
        <Modal title={dialog.payment ? "Edit payment" : "Add payment"} subtitle="All financial changes are written to the audit history." onClose={() => setDialog(null)} size="md" mobileMode="fullscreen"><form onSubmit={submitPayment} className="contents"><ModalBody><div className="space-y-4">{!dialog.payment ? <div><Label htmlFor="payment-subject">Subject</Label><select id="payment-subject" name="subjectId" required className={inputClass} defaultValue=""><option value="" disabled>Select active subject</option>{activeSubjects.map((subject) => <option key={asText(subject.subject_id)} value={asText(subject.subject_id)}>{asText(subject.subject_name)} · {asText(subject.group_name)}</option>)}</select>{!activeSubjects.length ? <p className="mt-1 text-xs font-bold text-destructive">Payment cannot be added until Academic Department enrolls this student.</p> : null}</div> : null}<div className="grid gap-4 sm:grid-cols-2"><div><Label htmlFor="payment-month">Label / month</Label><input id="payment-month" name="monthLabel" defaultValue={asText(dialog.payment?.month_label)} className={inputClass} /></div><div><Label htmlFor="payment-amount">Amount</Label><input id="payment-amount" name="amount" type="number" min="0.01" step="0.01" required defaultValue={asText(dialog.payment?.amount)} className={inputClass} /></div></div><div className="grid gap-4 sm:grid-cols-2"><div><Label htmlFor="payment-currency">Currency</Label><input id="payment-currency" name="currency" minLength={3} maxLength={3} required defaultValue={asText(dialog.payment?.currency) || "UZS"} className={inputClass} /></div><div><Label htmlFor="payment-due">Due date</Label><input id="payment-due" name="dueDate" type="date" defaultValue={asText(dialog.payment?.due_date).slice(0, 10)} className={inputClass} /></div></div>{!dialog.payment ? <div><Label htmlFor="payment-paid">Paid date (optional)</Label><input id="payment-paid" name="paidAt" type="date" className={inputClass} /></div> : null}<div><Label htmlFor="payment-notes">Notes</Label><textarea id="payment-notes" name="notes" rows={4} defaultValue={asText(dialog.payment?.notes)} className={`${inputClass} py-3`} /></div></div></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButton} onClick={() => setDialog(null)}>Cancel</button><button type="submit" disabled={saving || (!dialog.payment && !activeSubjects.length)} className={primaryButton}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}{dialog.payment ? "Save payment" : "Add payment"}</button></div></ModalFooter></form></Modal>
      ) : null}

      {dialog?.type === "link-child" && detail?.kind === "parent" ? (
        <LinkChildModal excludedIds={detail.children.map((child) => asNumber(child.id))} saving={saving} onClose={() => setDialog(null)} onLink={(studentId) => void linkChild(studentId)} />
      ) : null}

      {settlementTarget ? (
        <Modal title={settlementTarget.paid ? "Mark payment as paid?" : "Mark payment as unpaid?"} subtitle="The settlement status and audit history will be updated." onClose={() => setSettlementTarget(null)} size="sm"><ModalBody><div className="rounded-lg border border-border bg-muted p-4"><p className="font-black text-foreground">{asText(settlementTarget.payment.subject)} · {asText(settlementTarget.payment.month_label) || "Payment"}</p><p className="mt-1 text-sm font-semibold text-muted-foreground">{money(settlementTarget.payment.amount, asText(settlementTarget.payment.currency))}</p></div></ModalBody><ModalFooter><div className="flex justify-end gap-2"><button type="button" className={secondaryButton} onClick={() => setSettlementTarget(null)}>Cancel</button><button type="button" disabled={saving} className={primaryButton} onClick={() => void confirmSettlement()}>{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Banknote className="h-4 w-4" />}Confirm</button></div></ModalFooter></Modal>
      ) : null}

      <FloatingToast toast={toast} onClose={clearToast} />
    </RoleWorkspaceShell>
  );
}
