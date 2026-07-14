import { useEffect, useMemo, useState, type ReactNode } from "react";
import { UserRound } from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { Pagination } from "@/shared/ui/Pagination";
import { asNumber, asString } from "@/shared/lib/workspace";
import {
  type ParentFilters,
  type ParentRow,
  collectGroupOptions,
  countActiveFilters,
  defaultParentFilters,
  filterParents,
  parentAccountId,
  parentChildren,
  parentDisplayName,
} from "./types";
import { type ParentHandlers } from "./actions";
import { ParentSummaryCards } from "./ParentSummaryCards";
import { ParentToolbar } from "./ParentToolbar";
import { ParentTable } from "./ParentTable";
import { ParentDrawer } from "./ParentDrawer";
import { LinkStudentModal } from "./LinkStudentModal";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";

type ConfirmKind = "unlink" | "delete";
type ConfirmState = { kind: ConfirmKind; parent: ParentRow; child?: ParentRow } | null;

const PAGE_DESCRIPTION = "Manage parent accounts, contact details, linked students, and support tickets.";
const PARENTS_PAGE_SIZE = 9;

function HeaderBar() {
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
  const [linkParentId, setLinkParentId] = useState<number | null>(null);
  const [linkSaving, setLinkSaving] = useState(false);
  const [linkError, setLinkError] = useState("");
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const { toast, showToast } = useFloatingToast();
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => filterParents(parents, filters), [parents, filters]);
  const groupOptions = useMemo(() => collectGroupOptions(parents), [parents]);
  const activeCount = countActiveFilters(filters);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PARENTS_PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedParents = filtered.slice(
    (currentPage - 1) * PARENTS_PAGE_SIZE,
    currentPage * PARENTS_PAGE_SIZE,
  );

  const drawerParent = drawerParentId != null ? parents.find((p) => parentAccountId(p) === drawerParentId) || null : null;
  const linkParent = linkParentId != null ? parents.find((p) => parentAccountId(p) === linkParentId) || null : null;

  useEffect(() => {
    setPage(1);
  }, [filters]);

  function setParents(updater: (current: ParentRow[]) => ParentRow[]) {
    if (typeof state.setParentAccounts === "function") {
      state.setParentAccounts(updater);
    }
  }

  function applyFilters(patch: Partial<ParentFilters>) {
    setFilters((current) => ({ ...current, ...patch }));
  }

  async function request(method: string, url: string, body?: unknown) {
    const response = await fetch(url, {
      method,
      headers: jsonCsrfHeaders(csrf),
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    const json = await response.json().catch(() => ({}));
    if (!apiSucceeded(response, json)) {
      throw new Error(apiErrorMessage(json, "Something went wrong. Please try again."));
    }
    return apiData<Record<string, unknown>>(json);
  }

  async function linkStudent(parent: ParentRow, studentRowId: number) {
    if (linkSaving) return;
    setLinkSaving(true);
    setLinkError("");
    try {
      const id = parentAccountId(parent);
      if (id <= 0) throw new Error("Parent account is required.");
      const json = await request("POST", routes.adminParentChildrenFor(id), { student_row_id: studentRowId });
      const child = (json.child || {}) as ParentRow;
      setParents((current) =>
        current.map((p) =>
          parentAccountId(p) === id ? { ...p, children: [...parentChildren(p), child] } : p,
        ),
      );
      setLinkParentId(null);
      showToast("Student linked.");
    } catch (error) {
      setLinkError(error instanceof Error ? error.message : "Unable to link student.");
    } finally {
      setLinkSaving(false);
    }
  }

  async function unlinkChild(parent: ParentRow, child: ParentRow) {
    const id = parentAccountId(parent);
    if (id <= 0) throw new Error("Parent account is required.");
    const studentRowId = asNumber(child.student_row_id ?? child.id);
    await request("DELETE", routes.adminParentChildFor(id, studentRowId));
    setParents((current) =>
      current.map((p) =>
        parentAccountId(p) === id
          ? { ...p, children: parentChildren(p).filter((c) => asNumber(c.student_row_id ?? c.id) !== studentRowId) }
          : p,
      ),
    );
    showToast("Student unlinked.");
  }

  async function deleteParent(parent: ParentRow) {
    const id = parentAccountId(parent);
    if (id <= 0) throw new Error("Parent account is required.");
    await request("DELETE", routes.adminParentAccount(id));
    setParents((current) => current.filter((p) => parentAccountId(p) !== id));
    if (drawerParentId === id) setDrawerParentId(null);
    if (linkParentId === id) setLinkParentId(null);
    showToast("Parent deleted.");
  }

  function openTickets(parent: ParentRow) {
    const id = parentAccountId(parent);
    if (typeof state.setActiveParentId === "function") {
      state.setActiveParentId(id);
    }
    if (typeof state.switchAdminTab === "function") {
      state.switchAdminTab("complaints");
    }
  }

  async function runConfirm() {
    if (!confirm || confirmBusy) return;
    setConfirmBusy(true);
    try {
      if (confirm.kind === "unlink" && confirm.child) {
        await unlinkChild(confirm.parent, confirm.child);
      } else if (confirm.kind === "delete") {
        await deleteParent(confirm.parent);
      }
      setConfirm(null);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Action failed.", "danger");
      setConfirm(null);
    } finally {
      setConfirmBusy(false);
    }
  }

  const handlers: ParentHandlers = {
    onView: (parent) => {
      const id = parentAccountId(parent);
      if (id <= 0) {
        showToast("Parent account is required.", "danger");
        return;
      }
      setDrawerParentId(id);
    },
    onLinkStudent: (parent) => {
      setLinkError("");
      const id = parentAccountId(parent);
      if (id <= 0) {
        showToast("Parent account is required.", "danger");
        return;
      }
      setLinkParentId(id);
    },
    onUnlinkStudent: (parent) => {
      const kids = parentChildren(parent);
      if (kids.length === 1) {
        setConfirm({ kind: "unlink", parent, child: kids[0] });
      } else if (kids.length > 1) {
        const id = parentAccountId(parent);
        if (id <= 0) {
          showToast("Parent account is required.", "danger");
          return;
        }
        setDrawerParentId(id);
      }
    },
    onUnlinkChild: (parent, child) => setConfirm({ kind: "unlink", parent, child }),
    onOpenTickets: openTickets,
    onDeleteParent: (parent) => setConfirm({ kind: "delete", parent }),
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
    delete: {
      title: "Delete parent",
      message: confirm
        ? `Delete ${parentDisplayName(confirm.parent)}? This only works when the parent has no linked students, tickets, or payment history.`
        : "Delete this parent?",
      confirmLabel: "Delete",
      danger: true,
    },
  };

  const onlySearch = filters.search.trim() && activeCount === 1;

  return (
    <div className="workspace-fit flex flex-col gap-3 sm:gap-3 lg:h-full lg:min-h-0">
      <FloatingToast toast={toast} />
      <HeaderBar />

      <ParentSummaryCards parents={parents} filters={filters} onApply={applyFilters} />

      <ParentToolbar
        filters={filters}
        groupOptions={groupOptions}
        activeCount={activeCount}
        onChange={applyFilters}
        onClear={() => setFilters(defaultParentFilters)}
      />

      <div className="flex min-h-[22rem] flex-1 flex-col gap-3 lg:min-h-0">
        {loading ? (
          <TableSkeleton />
        ) : parents.length === 0 ? (
          <EmptyState
            title="No parents yet"
            hint="Parents appear here once they register through their Telegram invite link."
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
            <ParentTable parents={pagedParents} handlers={handlers} className="min-h-0 flex-1" />
            <Pagination
              page={currentPage}
              totalPages={totalPages}
              onPageChange={setPage}
              label={`Showing ${pagedParents.length} of ${filtered.length} parents`}
            />
          </>
        )}
      </div>

      <ParentDrawer
        parent={drawerParent}
        handlers={handlers}
        currentSchool={currentSchool}
        onClose={() => setDrawerParentId(null)}
      />

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
    </div>
  );
}
