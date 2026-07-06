import {
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  UserRoundCheck,
  UsersRound,
} from "lucide-react";
import { AcademicDirectorPageShell } from "@/roles/common/components/AcademicDirectorShell";
import { EmptyState } from "@/shared/ui/EmptyState";
import { MetricCard } from "@/shared/ui/MetricCard";
import { MobileCardList } from "@/shared/ui/MobileCardList";
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

type HeadOfDepartmentsProps = {
  authLogin?: string;
  authRole?: string;
  csrfToken?: string;
  headOfDepartments?: HeadOfDepartmentAccount[];
  warning?: string;
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

function statusTone(value: unknown) {
  return asText(value).toLowerCase() === "active" ? "success" : "warning";
}

function DepartmentCard({ account }: { account: HeadOfDepartmentAccount }) {
  const name = asText(account.display_name) || asText(account.login) || "Head of Department";
  const subject = asText(account.subject_name) || "Not assigned";

  return (
    <article className="rounded-xl border border-border bg-surface p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <UserRoundCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-base font-black text-foreground">{name}</h2>
            <p className="mt-1 truncate text-xs font-bold text-muted-foreground">
              {asText(account.login) || "-"} - {roleLabel(account.role)}
            </p>
          </div>
        </div>
        <StatusBadge tone={statusTone(account.status)} icon={<CheckCircle2 className="h-3.5 w-3.5" />} className="text-xs">
          {asText(account.status) || "active"}
        </StatusBadge>
      </div>

      <dl className="mt-4 grid gap-3 text-xs sm:grid-cols-2">
        <div>
          <dt className="font-bold uppercase tracking-wide text-muted-foreground">Account Login</dt>
          <dd className="mt-1 truncate font-mono font-black text-foreground">{asText(account.login) || "-"}</dd>
        </div>
        <div>
          <dt className="font-bold uppercase tracking-wide text-muted-foreground">Subject</dt>
          <dd className="mt-1 break-words font-black text-foreground">{subject}</dd>
        </div>
        <div>
          <dt className="font-bold uppercase tracking-wide text-muted-foreground">Scope</dt>
          <dd className="mt-1 break-words font-black text-foreground">{asText(account.scope_type) || "head_of_department"}</dd>
        </div>
        <div>
          <dt className="font-bold uppercase tracking-wide text-muted-foreground">Created</dt>
          <dd className="mt-1 font-black text-foreground">{dateLabel(account.created_at)}</dd>
        </div>
        <div>
          <dt className="font-bold uppercase tracking-wide text-muted-foreground">Updated</dt>
          <dd className="mt-1 font-black text-foreground">{dateLabel(account.updated_at)}</dd>
        </div>
      </dl>

      <div className="mt-4 rounded-lg border border-border bg-muted px-3 py-2 text-xs font-bold leading-5 text-muted-foreground">
        Read-only account record
      </div>
    </article>
  );
}

export default function HeadOfDepartmentsPage({
  authLogin = "",
  csrfToken = "",
  headOfDepartments = [],
  warning = "",
}: HeadOfDepartmentsProps) {
  const activeAccounts = headOfDepartments.filter((account) => asText(account.status).toLowerCase() === "active");
  const scopedSubjects = new Set(
    headOfDepartments.map((account) => asText(account.subject_name)).filter((subject) => subject && subject !== "Not assigned"),
  );

  return (
    <AcademicDirectorPageShell
      authLogin={authLogin}
      csrfToken={csrfToken}
      active="departments"
    >
          <header className="rounded-xl border border-border bg-surface p-5 shadow-card">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="flex min-w-0 items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <UsersRound className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                    Academic Director
                  </p>
                  <h1 className="mt-1 break-words text-2xl font-black text-foreground">Head of Departments</h1>
                  <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
                    Manage subject department heads and their Teacher Academy access.
                  </p>
                </div>
              </div>
              {authLogin ? (
                <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-border bg-muted px-3 py-2 text-xs font-bold text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <span className="truncate">{authLogin}</span>
                </div>
              ) : null}
            </div>
          </header>

          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 md:gap-3">
            <MetricCard label="Accounts" value={headOfDepartments.length} detail="department heads" />
            <MetricCard label="Active" value={activeAccounts.length} detail="usable accounts" tone="success" />
            <MetricCard label="Subjects" value={scopedSubjects.size} detail="assigned scopes" tone="info" />
          </div>

          {warning ? (
            <section className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <p className="text-sm font-semibold leading-6">{warning}</p>
            </section>
          ) : null}

          {headOfDepartments.length ? (
            <>
              <MobileCardList hideAt="md">
                {headOfDepartments.map((account, index) => (
                  <DepartmentCard key={accountKey(account, index)} account={account} />
                ))}
              </MobileCardList>

              <section className="hidden overflow-hidden rounded-xl border border-border bg-surface shadow-card md:block">
                <ResponsiveTable showAt="md">
                  <table className="w-full min-w-[760px] table-fixed divide-y divide-border text-left text-sm">
                    <colgroup>
                      <col className="w-[20%]" />
                      <col className="w-[14%]" />
                      <col className="w-[18%]" />
                      <col className="w-[22%]" />
                      <col className="w-[10%]" />
                      <col className="w-[10%]" />
                      <col className="w-[6%]" />
                    </colgroup>
                    <thead className="bg-muted/60 text-xs font-black uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3">Name</th>
                        <th className="px-4 py-3">Login</th>
                        <th className="px-4 py-3">Role</th>
                        <th className="px-4 py-3">Subject Scope</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Updated</th>
                        <th className="px-4 py-3 text-right">Record</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {headOfDepartments.map((account, index) => (
                        <tr key={accountKey(account, index)}>
                          <td className="px-4 py-3">
                            <p className="max-w-[14rem] truncate font-black text-foreground">
                              {asText(account.display_name) || asText(account.login) || "Head of Department"}
                            </p>
                          </td>
                          <td className="px-4 py-3 font-semibold text-muted-foreground">
                            <span className="block truncate font-mono text-xs font-black text-foreground">{asText(account.login) || "-"}</span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-muted-foreground">
                            {roleLabel(account.role)}
                          </td>
                          <td className="px-4 py-3">
                            <p className="max-w-[14rem] truncate font-black text-foreground">{asText(account.subject_name) || "Not assigned"}</p>
                            <p className="mt-0.5 text-xs font-semibold text-muted-foreground">
                              {asText(account.scope_type) || "head_of_department"}
                            </p>
                          </td>
                          <td className="px-4 py-3">
                            <StatusBadge tone={statusTone(account.status)} icon={<CheckCircle2 className="h-3.5 w-3.5" />} className="text-[10px]">
                              {asText(account.status) || "active"}
                            </StatusBadge>
                          </td>
                          <td className="px-4 py-3 font-semibold text-muted-foreground">
                            {dateLabel(account.updated_at || account.created_at)}
                          </td>
                          <td className="px-4 py-3">
                            <span className="inline-flex min-h-9 items-center justify-center rounded-lg border border-border bg-muted px-3 text-xs font-black text-muted-foreground">
                              Read-only
                            </span>
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
              detail="Created Head of Department accounts will appear here with their subject scope after reload."
            />
          )}
    </AcademicDirectorPageShell>
  );
}
