import { useMemo, useState, type ReactNode } from "react";
import { AlertCircle, CheckCircle2, Plus, UserRound, X } from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { asNumber, asString } from "../shared";
import {
  type ParentFilters,
  type ParentRow,
  collectGroupOptions,
  countActiveFilters,
  defaultParentFilters,
  filterParents,
  isDisabled,
  parentChildren,
  parentDisplayName,
} from "./parents/types";
import { type ParentHandlers } from "./parents/actions";
import { ParentSummaryCards } from "./parents/ParentSummaryCards";
import { ParentToolbar } from "./parents/ParentToolbar";
import { ParentTable } from "./parents/ParentTable";
import { ParentDrawer } from "./parents/ParentDrawer";
import { ParentFormModal, type ParentProfilePayload } from "./parents/ParentFormModal";
import { LinkStudentModal } from "./parents/LinkStudentModal";

type Banner = { kind: "error" | "success"; text: string } | null;

type ConfirmKind = "unlink" | "disable" | "delete" | "reset";
type ConfirmState = { kind: ConfirmKind; parent: ParentRow; child?: ParentRow } | null;

const PAGE_DESCRIPTION = "Manage parent accounts, contact details, linked students, and support tickets.";

function HeaderBar({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex min-w-0 items-start gap-2.5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-info">
          <UserRound className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <h1 className="font-display text-lg font-bold leading-tight">Parents</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">{PAGE_DESCRIPTION}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onAdd}
        className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-bold text-primary-foreground hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-foreground/30"
      >
        <Plus className="h-4 w-4" />
        Add parent
      </button>
    </div>
  );
}

function EmptyState({ title, hint, action }: { title: string; hint: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-12 text-center">
      <p className="text-sm font-bold">{title}</p>
      <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">{hint}</p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-2" aria-hidden>
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="h-14 animate-pulse rounded-lg border border-foreground/10 bg-muted/40" />
      ))}
    </div>
  );
}

export default function ParentsPanel({ state }: { state: any }) {
  const csrf = asString(state.props?.csrfToken);
  const currentSchool = asString(state.currentSchool || state.props?.adminSchool) || "all";
  const parents: ParentRow[] = Array.isArray(state.parentAccounts)
    ? state.parentAccounts
    : Array.isArray(state.props?.adminParents)
      ? state.props.adminParents
      : [];
  const students: ParentRow[] = Array.isArray(state.students) && state.students.length
    ? state.students
    : Array.isArray(state.props?.adminStudents)
      ? state.props.adminStudents
      : [];
  const loading = !Array.isArray(state.parentAccounts) && !Array.isArray(state.props?.adminParents);

  const [filters, setFilters] = useState<ParentFilters>(defaultParentFilters);
  const [drawerParentId, setDrawerParentId] = useState<number | null>(null);
  const [form, setForm] = useState<{ mode: "create" | "edit"; parent: ParentRow | null } | null>(null);
  const [formSaving, setFormSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [linkParentId, setLinkParentId] = useState<number | null>(null);
  const [linkSaving, setLinkSaving] = useState(false);
  const [linkError, setLinkError] = useState("");
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [banner, setBanner] = useState<Banner>(null);
  const [resetResult, setResetResult] = useState<{ name: string; password: string } | null>(null);

  const filtered = useMemo(() => filterParents(parents, filters), [parents, filters]);
  const groupOptions = useMemo(() => collectGroupOptions(parents), [parents]);
  const activeCount = countActiveFilters(filters);

  const drawerParent = drawerParentId != null ? parents.find((p) => asNumber(p.id) === drawerParentId) || null : null;
  const linkParent = linkParentId != null ? parents.find((p) => asNumber(p.id) === linkParentId) || null : null;

  function setParents(updater: (current: ParentRow[]) => ParentRow[]) {
    if (typeof state.setParentAccounts === "function") {
      state.setParentAccounts(updater);
    }
  }

  function patchParent(id: number, next: ParentRow) {
    setParents((current) => current.map((p) => (asNumber(p.id) === id ? next : p)));
  }

  function applyFilters(patch: Partial<ParentFilters>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  async function request(method: string, url: string, body?: unknown) {
    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
        "X-Requested-With": "XMLHttpRequest",
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    const json = await response.json().catch(() => ({}));
    if (!response.ok || !json.ok) {
      throw new Error(asString(json.message) || "Something went wrong. Please try again.");
    }
    return json as Record<string, unknown>;
  }

  // ── Create / edit ──────────────────────────────────────────────────────────
  async function submitForm(payload: ParentProfilePayload) {
    if (!form || formSaving) return;
    setFormSaving(true);
    setFormError("");
    try {
      if (form.mode === "create") {
        const json = await request("POST", routes.adminParents, payload);
        const parent = (json.parent || {}) as ParentRow;
        setParents((current) =>
          [...current, parent].sort((a, b) => asString(a.login).localeCompare(asString(b.login))),
        );
        setBanner({ kind: "success", text: `Added ${parentDisplayName(parent)}.` });
      } else if (form.parent) {
        const id = asNumber(form.parent.id);
        const json = await request("PATCH", routes.adminParent(id), payload);
        patchParent(id, (json.parent || {}) as ParentRow);
        setBanner({ kind: "success", text: "Parent profile updated." });
      }
      setForm(null);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to save.");
    } finally {
      setFormSaving(false);
    }
  }

  // ── Link / unlink ──────────────────────────────────────────────────────────
  async function linkStudent(parent: ParentRow, studentRowId: number) {
    if (linkSaving) return;
    setLinkSaving(true);
    setLinkError("");
    try {
      const id = asNumber(parent.id);
      const json = await request("POST", routes.adminParentChildrenFor(id), { student_row_id: studentRowId });
      const child = (json.child || {}) as ParentRow;
      setParents((current) =>
        current.map((p) =>
          asNumber(p.id) === id ? { ...p, children: [...parentChildren(p), child] } : p,
        ),
      );
      setLinkParentId(null);
      setBanner({ kind: "success", text: "Student linked." });
    } catch (error) {
      setLinkError(error instanceof Error ? error.message : "Unable to link student.");
    } finally {
      setLinkSaving(false);
    }
  }

  async function unlinkChild(parent: ParentRow, child: ParentRow) {
    const id = asNumber(parent.id);
    const studentRowId = asNumber(child.student_row_id ?? child.id);
    await request("DELETE", routes.adminParentChildFor(id, studentRowId));
    setParents((current) =>
      current.map((p) =>
        asNumber(p.id) === id
          ? { ...p, children: parentChildren(p).filter((c) => asNumber(c.student_row_id ?? c.id) !== studentRowId) }
          : p,
      ),
    );
    setBanner({ kind: "success", text: "Student unlinked." });
  }

  // ── Account actions ────────────────────────────────────────────────────────
  async function resetPassword(parent: ParentRow) {
    const id = asNumber(parent.id);
    const json = await request("POST", routes.adminParentResetPassword(id), {});
    patchParent(id, (json.parent || parent) as ParentRow);
    setResetResult({ name: parentDisplayName(parent), password: asString(json.temporary_password) });
  }

  async function toggleDisabled(parent: ParentRow, disabled: boolean) {
    const id = asNumber(parent.id);
    const json = await request("POST", routes.adminParentStatus(id), { disabled });
    patchParent(id, (json.parent || parent) as ParentRow);
    setBanner({ kind: "success", text: disabled ? "Account disabled." : "Account enabled." });
  }

  async function deleteParent(parent: ParentRow) {
    const id = asNumber(parent.id);
    await request("DELETE", routes.adminParent(id));
    setParents((current) => current.filter((p) => asNumber(p.id) !== id));
    if (drawerParentId === id) setDrawerParentId(null);
    setBanner({ kind: "success", text: `Deleted ${parentDisplayName(parent)}.` });
  }

  function openTickets(parent: ParentRow) {
    if (typeof state.setActiveParentId === "function") {
      state.setActiveParentId(asNumber(parent.id));
    }
    if (typeof state.switchAdminTab === "function") {
      state.switchAdminTab("complaints");
    }
  }

  // ── Confirm-gated dispatch ──────────────────────────────────────────────────
  async function runConfirm() {
    if (!confirm || confirmBusy) return;
    setConfirmBusy(true);
    try {
      if (confirm.kind === "unlink" && confirm.child) {
        await unlinkChild(confirm.parent, confirm.child);
      } else if (confirm.kind === "disable") {
        await toggleDisabled(confirm.parent, true);
      } else if (confirm.kind === "delete") {
        await deleteParent(confirm.parent);
      } else if (confirm.kind === "reset") {
        await resetPassword(confirm.parent);
      }
      setConfirm(null);
    } catch (error) {
      setBanner({ kind: "error", text: error instanceof Error ? error.message : "Action failed." });
      setConfirm(null);
    } finally {
      setConfirmBusy(false);
    }
  }

  const handlers: ParentHandlers = {
    onView: (parent) => setDrawerParentId(asNumber(parent.id)),
    onEdit: (parent) => setForm({ mode: "edit", parent }),
    onLinkStudent: (parent) => {
      setLinkError("");
      setLinkParentId(asNumber(parent.id));
    },
    onUnlinkStudent: (parent) => {
      const kids = parentChildren(parent);
      if (kids.length === 1) {
        setConfirm({ kind: "unlink", parent, child: kids[0] });
      } else if (kids.length > 1) {
        setDrawerParentId(asNumber(parent.id));
      }
    },
    onUnlinkChild: (parent, child) => setConfirm({ kind: "unlink", parent, child }),
    onResetPassword: (parent) => setConfirm({ kind: "reset", parent }),
    onToggleDisabled: (parent) => {
      if (isDisabled(parent)) {
        void toggleDisabled(parent, false).catch((error) =>
          setBanner({ kind: "error", text: error instanceof Error ? error.message : "Action failed." }),
        );
      } else {
        setConfirm({ kind: "disable", parent });
      }
    },
    onDelete: (parent) => setConfirm({ kind: "delete", parent }),
    onOpenTickets: openTickets,
  };

  const confirmConfig: Record<ConfirmKind, { title: string; message: string; confirmLabel: string; danger: boolean }> = {
    unlink: {
      title: "Unlink student",
      message: confirm?.child
        ? `Remove ${asString(confirm.child.full_name) || "this student"} from ${parentDisplayName(confirm.parent)}? The parent will lose access to this student.`
        : "Remove this student?",
      confirmLabel: "Unlink",
      danger: true,
    },
    disable: {
      title: "Disable account",
      message: confirm ? `${parentDisplayName(confirm.parent)} will be blocked from signing in until re-enabled. Their data is kept.` : "",
      confirmLabel: "Disable",
      danger: true,
    },
    delete: {
      title: "Delete account",
      message: confirm ? `Permanently delete ${parentDisplayName(confirm.parent)} and all student links. This cannot be undone.` : "",
      confirmLabel: "Delete",
      danger: true,
    },
    reset: {
      title: "Reset password",
      message: confirm ? `Generate a new temporary password for ${parentDisplayName(confirm.parent)}? Their current password will stop working.` : "",
      confirmLabel: "Reset password",
      danger: false,
    },
  };

  const onlySearch = filters.search.trim() && activeCount === 1;

  return (
    <div className="flex min-h-[calc(100dvh-var(--app-top-inset)-2rem)] flex-col gap-4">
      <HeaderBar onAdd={() => { setFormError(""); setForm({ mode: "create", parent: null }); }} />

      {banner ? (
        <div
          role="status"
          className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm font-semibold ${
            banner.kind === "error"
              ? "border-destructive/20 bg-destructive/10 text-destructive"
              : "border-emerald-200 bg-emerald-50 text-emerald-700"
          }`}
        >
          {banner.kind === "error" ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />}
          <span className="min-w-0 flex-1 break-words">{banner.text}</span>
          <button type="button" onClick={() => setBanner(null)} aria-label="Dismiss" className="shrink-0 rounded p-0.5 hover:bg-foreground/10">
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : null}

      <ParentSummaryCards parents={parents} filters={filters} onApply={applyFilters} />

      <ParentToolbar
        filters={filters}
        groupOptions={groupOptions}
        activeCount={activeCount}
        onChange={applyFilters}
        onClear={() => setFilters(defaultParentFilters)}
      />

      <div className="flex min-h-[22rem] flex-1 flex-col gap-3">
        {loading ? (
          <TableSkeleton />
        ) : parents.length === 0 ? (
          <EmptyState
            title="No parents yet"
            hint="Add a parent account to start linking students and managing support."
            action={
              <button
                type="button"
                onClick={() => setForm({ mode: "create", parent: null })}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-bold text-primary-foreground"
              >
                <Plus className="h-4 w-4" />
                Add parent
              </button>
            }
          />
        ) : filtered.length === 0 ? (
          <EmptyState
            title={onlySearch ? "No parents found" : "No parents match the selected filters"}
            hint="Try changing your search or clearing the filters."
            action={
              <button
                type="button"
                onClick={() => setFilters(defaultParentFilters)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-foreground/10 bg-background px-3.5 text-sm font-bold hover:bg-muted"
              >
                Clear filters
              </button>
            }
          />
        ) : (
          <>
            <p className="shrink-0 text-xs font-semibold text-muted-foreground">
              Showing {filtered.length} of {parents.length} parents
            </p>
            <ParentTable parents={filtered} handlers={handlers} className="min-h-0 flex-1" />
          </>
        )}
      </div>

      <ParentDrawer
        parent={drawerParent}
        handlers={handlers}
        currentSchool={currentSchool}
        onClose={() => setDrawerParentId(null)}
      />

      {form ? (
        <ParentFormModal
          mode={form.mode}
          parent={form.parent}
          saving={formSaving}
          error={formError}
          onClose={() => setForm(null)}
          onSubmit={submitForm}
        />
      ) : null}

      {linkParent ? (
        <LinkStudentModal
          parent={linkParent}
          students={students}
          saving={linkSaving}
          error={linkError}
          onClose={() => setLinkParentId(null)}
          onLink={(studentRowId) => linkStudent(linkParent, studentRowId)}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm ? confirmConfig[confirm.kind].title : ""}
        message={confirm ? confirmConfig[confirm.kind].message : ""}
        confirmLabel={confirm ? confirmConfig[confirm.kind].confirmLabel : "Confirm"}
        danger={confirm ? confirmConfig[confirm.kind].danger : false}
        busy={confirmBusy}
        onConfirm={runConfirm}
        onCancel={() => setConfirm(null)}
      />

      {resetResult ? (
        <ResetPasswordDialog
          name={resetResult.name}
          password={resetResult.password}
          onClose={() => setResetResult(null)}
        />
      ) : null}
    </div>
  );
}

function ResetPasswordDialog({ name, password, onClose }: { name: string; password: string; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-foreground/60 p-4" onClick={onClose}>
      <div className="w-full max-w-sm overflow-hidden rounded-xl bg-surface shadow-card-hover" onClick={(e) => e.stopPropagation()}>
        <div className="px-5 pt-5">
          <h3 className="text-sm font-bold">Temporary password</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Share this password with {name}. It only shows once — they should change it after signing in.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 truncate rounded-lg border border-foreground/10 bg-background px-3 py-2 font-mono text-sm font-bold">
              {password || "—"}
            </code>
            <button
              type="button"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(password);
                  setCopied(true);
                } catch {
                  setCopied(false);
                }
              }}
              className="h-9 shrink-0 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-bold hover:bg-muted"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
        <div className="mt-5 px-5 pb-5">
          <button type="button" onClick={onClose} className="h-10 w-full rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
