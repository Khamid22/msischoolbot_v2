import { useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Copy,
  Eye,
  Plus,
  ShieldCheck,
  UserRoundCheck,
  UsersRound,
} from "lucide-react";
import { AcademicDirectorPageShell } from "@/features/academic_workspace/AcademicDirectorShell";
import { postForm } from "@/features/management/teachers/shared";
import { routes } from "@/shared/lib/routes";
import { EmptyState } from "@/shared/ui/EmptyState";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { IconButton } from "@/shared/ui/IconButton";
import { MetricCard } from "@/shared/ui/MetricCard";
import { MetricGrid } from "@/shared/ui/MetricGrid";
import { MobileCardList } from "@/shared/ui/MobileCardList";
import { BottomSheet, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { PageHeader } from "@/shared/ui/PageHeader";
import { ResponsiveTable } from "@/shared/ui/ResponsiveTable";
import { StatusBadge } from "@/shared/ui/StatusBadge";

type HeadOfDepartmentAccount = {
  account_id?: number | string;
  login?: string;
  display_name?: string;
  role?: string;
  status?: string;
  subject_id?: number | string;
  subject_name?: string;
  scope_type?: string;
  created_at?: string;
  updated_at?: string;
};

type SubjectOption = {
  id?: number | string;
  name?: string;
};

type HeadOfDepartmentsProps = {
  authLogin?: string;
  authRole?: string;
  csrfToken?: string;
  headOfDepartments?: HeadOfDepartmentAccount[];
  subjectOptions?: SubjectOption[];
  warning?: string;
};

type GeneratedHodCredentials = {
  login?: string;
  temporary_password?: string;
  display_name?: string;
  subject_name?: string;
};

function asText(value: unknown) {
  return String(value ?? "").trim();
}

function dateLabel(value: unknown) {
  const raw = asText(value);
  if (!raw) return "-";
  const parsed = Date.parse(raw);
  if (!Number.isFinite(parsed)) return raw.replace("T", " ").slice(0, 16);
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(new Date(parsed));
}

function roleLabel(value: unknown) {
  return asText(value || "head_of_department")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function accountKey(account: HeadOfDepartmentAccount, index: number) {
  return asText(account.account_id) || asText(account.login) || `hod-${index}`;
}

function accountName(account: HeadOfDepartmentAccount) {
  return asText(account.display_name) || asText(account.login) || "Head of Department";
}

function subjectLabel(account: HeadOfDepartmentAccount) {
  return asText(account.subject_name) || "Not assigned";
}

function DepartmentCard({
  account,
  onView,
}: {
  account: HeadOfDepartmentAccount;
  onView: () => void;
}) {
  return (
    <article className="rounded-xl border border-border bg-surface p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <UserRoundCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-base font-black text-foreground">{accountName(account)}</h2>
            <p className="mt-1 truncate text-xs font-bold text-muted-foreground">
              <span className="font-mono">{asText(account.login) || "-"}</span> · {roleLabel(account.role)}
            </p>
          </div>
        </div>
        <StatusBadge status={asText(account.status) || "active"} className="text-xs" />
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div className="min-w-0">
          <dt className="font-bold uppercase tracking-wide text-muted-foreground">Subject Scope</dt>
          <dd className="mt-1 break-words font-black text-foreground">{subjectLabel(account)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="font-bold uppercase tracking-wide text-muted-foreground">Updated</dt>
          <dd className="mt-1 font-black text-foreground">{dateLabel(account.updated_at || account.created_at)}</dd>
        </div>
      </dl>

      <button
        type="button"
        onClick={onView}
        className="mt-3 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-border bg-background text-sm font-black text-foreground transition-colors duration-150 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30 motion-reduce:transition-none"
      >
        <Eye className="h-4 w-4" />
        View
      </button>
    </article>
  );
}

function AccountDetailSheet({
  account,
  onClose,
}: {
  account: HeadOfDepartmentAccount;
  onClose: () => void;
}) {
  const fields: Array<[string, string]> = [
    ["Name", accountName(account)],
    ["Account Login", asText(account.login) || "-"],
    ["Role", roleLabel(account.role)],
    ["Subject Scope", subjectLabel(account)],
    ["Scope Type", asText(account.scope_type) || "head_of_department"],
    ["Status", asText(account.status) || "active"],
    ["Created", dateLabel(account.created_at)],
    ["Updated", dateLabel(account.updated_at)],
  ];

  return (
    <BottomSheet title={accountName(account)} subtitle="Head of Department account" onClose={onClose}>
      <ModalBody>
        <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          {fields.map(([label, value]) => (
            <div key={label} className="min-w-0 rounded-lg border border-border bg-background px-3 py-2">
              <dt className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</dt>
              <dd className="mt-0.5 break-words font-black text-foreground">
                {label === "Status" ? <StatusBadge status={value} className="text-[10px]" /> : value}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 rounded-lg border border-border bg-muted px-3 py-2 text-xs font-bold leading-5 text-muted-foreground">
          Read-only account record. Access changes are managed by the system administrators.
        </p>
      </ModalBody>
    </BottomSheet>
  );
}

function NewHodSheet({
  subjects,
  submitting,
  error,
  onSubmit,
  onClose,
}: {
  subjects: SubjectOption[];
  submitting: boolean;
  error: string;
  onSubmit: (fields: Record<string, string>) => void;
  onClose: () => void;
}) {
  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const fields: Record<string, string> = {};
    data.forEach((value, key) => {
      fields[key] = String(value);
    });
    onSubmit(fields);
  }

  return (
    <BottomSheet title="New Head of Department" subtitle="Create subject-scoped Teacher Academy access." onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted-foreground">Display Name</span>
            <input
              name="hod_display_name"
              className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none focus-visible:border-primary/50"
              placeholder="Head of Math Department"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-muted-foreground">Subject Scope</span>
            <select
              name="hod_subject_id"
              required
              defaultValue=""
              disabled={!subjects.length}
              className="w-full rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2.5 text-sm outline-none focus-visible:border-primary/50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <option value="" disabled>
                {subjects.length ? "Select subject" : "No active subjects available"}
              </option>
              {subjects.map((subject, index) => (
                <option key={asText(subject.id) || index} value={asText(subject.id)}>
                  {asText(subject.name) || `Subject ${asText(subject.id)}`}
                </option>
              ))}
            </select>
          </label>
          <div className="rounded-lg border border-primary/10 bg-primary/5 px-3 py-2 text-xs font-semibold text-primary">
            Login and temporary password will be generated automatically in HOD0001 format.
          </div>
          {error ? (
            <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p>
          ) : null}
        </ModalBody>
        <ModalFooter className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex min-h-10 w-full items-center justify-center rounded-lg border border-border bg-background px-4 text-sm font-black text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30 sm:w-auto"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !subjects.length}
            className="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-sm font-black text-primary-foreground transition-transform duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none motion-reduce:active:scale-100 sm:w-auto"
          >
            {submitting ? "Creating..." : "Create HOD"}
          </button>
        </ModalFooter>
      </form>
    </BottomSheet>
  );
}

function CredentialsSheet({
  credentials,
  onCopy,
  onClose,
}: {
  credentials: GeneratedHodCredentials;
  onCopy: (value: string, label: string) => void;
  onClose: () => void;
}) {
  const rows: Array<[string, string]> = [
    ["Login", asText(credentials.login)],
    ["Temporary Password", asText(credentials.temporary_password)],
  ];

  return (
    <BottomSheet
      title="Head of Department created"
      subtitle={`${asText(credentials.display_name) || "New account"} · ${asText(credentials.subject_name) || "subject scope"}`}
      onClose={onClose}
      closeOnOutsideClick={false}
    >
      <ModalBody>
        <p className="text-sm font-semibold leading-6 text-muted-foreground">
          Share these credentials now — the temporary password is only shown once.
        </p>
        <dl className="mt-3 space-y-2">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-center justify-between gap-2 rounded-lg border border-border bg-background px-3 py-2">
              <div className="min-w-0">
                <dt className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</dt>
                <dd className="mt-0.5 break-all font-mono text-sm font-black text-foreground">{value || "-"}</dd>
              </div>
              <IconButton label={`Copy ${label.toLowerCase()}`} onClick={() => onCopy(value, label)}>
                <Copy className="h-4 w-4" />
              </IconButton>
            </div>
          ))}
        </dl>
      </ModalBody>
    </BottomSheet>
  );
}

function SubjectCoverage({
  accounts,
  subjects,
}: {
  accounts: HeadOfDepartmentAccount[];
  subjects: SubjectOption[];
}) {
  const coverage = new Map<string, string[]>();
  accounts.forEach((account) => {
    const subject = asText(account.subject_name);
    if (!subject) return;
    const owners = coverage.get(subject) || [];
    owners.push(accountName(account));
    coverage.set(subject, owners);
  });

  const subjectNames = subjects.length
    ? subjects.map((subject) => asText(subject.name)).filter(Boolean)
    : [...coverage.keys()];
  const unassignedAccounts = accounts.filter((account) => !asText(account.subject_name));

  return (
    <section className="rounded-2xl border border-border bg-surface p-4 shadow-card sm:p-5">
      <div className="flex items-center gap-2">
        <BookOpen className="h-4 w-4 shrink-0 text-primary" />
        <h2 className="text-base font-black text-foreground">Subject Coverage</h2>
      </div>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">
        Which subjects have a Head of Department assigned.
      </p>

      {subjectNames.length ? (
        <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {subjectNames.map((subject) => {
            const owners = coverage.get(subject) || [];
            return (
              <li key={subject} className="flex items-center justify-between gap-2 rounded-lg border border-border bg-background px-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-black text-foreground">{subject}</p>
                  <p className="truncate text-xs font-semibold text-muted-foreground">
                    {owners.length ? owners.join(", ") : "No HOD assigned"}
                  </p>
                </div>
                {owners.length ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" aria-label="Covered" />
                ) : (
                  <StatusBadge status="missing" className="shrink-0 text-[10px]" />
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="mt-3 rounded-lg border border-dashed border-border bg-background px-3 py-2 text-sm font-semibold text-muted-foreground">
          No subject records available yet.
        </p>
      )}

      {unassignedAccounts.length ? (
        <p className="mt-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold leading-5 text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {unassignedAccounts.length} account{unassignedAccounts.length === 1 ? "" : "s"} without a subject scope:{" "}
          {unassignedAccounts.map(accountName).join(", ")}
        </p>
      ) : null}
    </section>
  );
}

export default function HeadOfDepartmentsPage({
  authLogin = "",
  authRole = "",
  csrfToken = "",
  headOfDepartments = [],
  subjectOptions = [],
  warning = "",
}: HeadOfDepartmentsProps) {
  const [accounts, setAccounts] = useState<HeadOfDepartmentAccount[]>(headOfDepartments);
  const [detailAccount, setDetailAccount] = useState<HeadOfDepartmentAccount | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");
  const [credentials, setCredentials] = useState<GeneratedHodCredentials | null>(null);
  const { toast, showToast, clearToast } = useFloatingToast();

  const isDirector = asText(authRole).toLowerCase().replace(/-/g, "_") === "academic_director";
  const activeAccounts = accounts.filter((account) => asText(account.status).toLowerCase() === "active");
  const scopedSubjects = new Set(
    accounts.map((account) => asText(account.subject_name)).filter(Boolean),
  );
  const unassignedCount = accounts.filter((account) => !asText(account.subject_name)).length;

  async function handleCreate(fields: Record<string, string>) {
    setSubmitting(true);
    setCreateError("");
    const result = await postForm(routes.academicDirectorHeadOfDepartmentCreate, fields, csrfToken);
    setSubmitting(false);
    if (!result.ok) {
      setCreateError(asText(result.data.message) || "Unable to create Head of Department.");
      return;
    }
    const created = (result.data.headOfDepartment || {}) as HeadOfDepartmentAccount;
    setAccounts((current) => [{ ...created, updated_at: new Date().toISOString() }, ...current]);
    setCreateOpen(false);
    if (result.data.credentials && typeof result.data.credentials === "object") {
      setCredentials(result.data.credentials as GeneratedHodCredentials);
    }
    showToast("Head of Department account created.", "success");
  }

  function copyCredential(value: string, label: string) {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText && value) {
      void navigator.clipboard.writeText(value).catch(() => {});
      showToast(`${label} copied.`, "info");
    }
  }

  const newHodButton = isDirector ? (
    <button
      type="button"
      onClick={() => {
        setCreateError("");
        setCreateOpen(true);
      }}
      className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-black text-primary-foreground transition-transform duration-150 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transition-none motion-reduce:active:scale-100"
    >
      <Plus className="h-4 w-4" />
      New HOD
    </button>
  ) : null;

  return (
    <AcademicDirectorPageShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active="departments"
    >
      <PageHeader
        title="Head of Departments"
        subtitle="Manage subject department heads and their Teacher Academy access."
        badge={
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-black uppercase tracking-wide text-primary">
            Academic Director
          </span>
        }
        actions={
          <>
            {authLogin ? (
              <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-border bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
                <span className="truncate">{authLogin}</span>
              </div>
            ) : null}
            {newHodButton}
          </>
        }
      />

      <MetricGrid>
        <MetricCard label="Accounts" value={accounts.length} detail="department heads" />
        <MetricCard label="Active" value={activeAccounts.length} detail="usable accounts" tone="success" />
        <MetricCard label="Subjects" value={scopedSubjects.size} detail="covered scopes" tone="info" />
        <MetricCard
          label="Unassigned"
          value={unassignedCount}
          detail="accounts without scope"
          tone={unassignedCount ? "warning" : "default"}
        />
      </MetricGrid>

      {warning ? (
        <section className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <p className="text-sm font-semibold leading-6">{warning}</p>
        </section>
      ) : null}

      {accounts.length ? (
        <>
          <MobileCardList hideAt="md">
            {accounts.map((account, index) => (
              <DepartmentCard
                key={accountKey(account, index)}
                account={account}
                onView={() => setDetailAccount(account)}
              />
            ))}
          </MobileCardList>

          <section className="hidden rounded-xl border border-border bg-surface shadow-card md:block">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
              <h2 className="text-sm font-black text-foreground">Accounts</h2>
              <StatusBadge tone="neutral" className="text-[10px]">
                Read-only records
              </StatusBadge>
            </div>
            <ResponsiveTable showAt="md" className="rounded-b-xl">
              <table className="w-full min-w-[720px] divide-y divide-border text-left text-sm">
                <thead className="bg-muted/60 text-xs font-black uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">Account Login</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Subject Scope</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Updated</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {accounts.map((account, index) => (
                    <tr key={accountKey(account, index)} className="transition-colors duration-150 hover:bg-muted/40 motion-reduce:transition-none">
                      <td className="max-w-[16rem] px-4 py-3">
                        <p className="truncate font-black text-foreground">{accountName(account)}</p>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <span className="font-mono text-xs font-black text-foreground">{asText(account.login) || "-"}</span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-semibold text-muted-foreground">
                        {roleLabel(account.role)}
                      </td>
                      <td className="max-w-[16rem] px-4 py-3">
                        <p className="truncate font-black text-foreground">{subjectLabel(account)}</p>
                        <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">
                          {asText(account.scope_type) || "head_of_department"}
                        </p>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <StatusBadge status={asText(account.status) || "active"} className="text-[10px]" />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-semibold text-muted-foreground">
                        {dateLabel(account.updated_at || account.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => setDetailAccount(account)}
                          className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-black text-foreground transition-colors duration-150 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30 motion-reduce:transition-none"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ResponsiveTable>
          </section>
        </>
      ) : (
        <EmptyState
          icon={<UsersRound className="h-6 w-6" />}
          title="No Head of Department accounts yet"
          detail="Create the first Head of Department to give a subject its own Teacher Academy manager."
          action={newHodButton}
        />
      )}

      <SubjectCoverage accounts={accounts} subjects={subjectOptions} />

      {detailAccount ? (
        <AccountDetailSheet account={detailAccount} onClose={() => setDetailAccount(null)} />
      ) : null}
      {createOpen ? (
        <NewHodSheet
          subjects={subjectOptions}
          submitting={submitting}
          error={createError}
          onSubmit={handleCreate}
          onClose={() => {
            setCreateError("");
            setCreateOpen(false);
          }}
        />
      ) : null}
      {credentials ? (
        <CredentialsSheet
          credentials={credentials}
          onCopy={copyCredential}
          onClose={() => setCredentials(null)}
        />
      ) : null}

      <FloatingToast toast={toast} onClose={clearToast} />
    </AcademicDirectorPageShell>
  );
}
