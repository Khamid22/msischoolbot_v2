import { useEffect, useRef, useMemo, useState, type FormEvent } from "react";
import { KeyRound, Plus, Search, UserMinus, UserPlus, UserRound, Users, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, formatLastSeen } from "../shared";

function initialsFor(value: unknown) {
  const parts = asString(value).split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() || "")
      .join("") || "PA"
  );
}

function studentLabel(student: Record<string, unknown>) {
  return [
    asString(student.full_name),
    asString(student.student_id),
    asString(student.school_name),
  ]
    .filter(Boolean)
    .join(" · ");
}

function parentChildren(parent: Record<string, unknown> | undefined) {
  return Array.isArray(parent?.children)
    ? (parent.children as Array<Record<string, unknown>>)
    : [];
}

function CreateParentModal({
  csrf,
  saving,
  error,
  onClose,
  onSubmit,
}: {
  csrf: string;
  saving: boolean;
  error: string;
  onClose: () => void;
  onSubmit: (login: string, password: string) => Promise<void>;
}) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const loginRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loginRef.current?.focus();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(login, password);
    setLogin("");
    setPassword("");
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm overflow-hidden rounded-lg bg-surface shadow-card-hover"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div>
            <h3 className="flex items-center gap-1.5 text-sm font-bold">
              <KeyRound className="h-4 w-4 text-info" />
              Create Parent
            </h3>
            <p className="text-xs text-muted-foreground">Login and temporary password</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 p-4">
          {error ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
              {error}
            </div>
          ) : null}

          <label className="block">
            <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
              Login
            </span>
            <input
              ref={loginRef}
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm outline-none focus:border-foreground/30"
              placeholder="parent-login"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
              Temporary password
            </span>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm outline-none focus:border-foreground/30"
              placeholder="At least 6 characters"
            />
          </label>

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="h-10 flex-1 rounded-lg border border-foreground/10 text-sm font-bold hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !login.trim() || password.length < 6}
              className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-primary text-sm font-bold text-primary-foreground disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StudentCombobox({
  students,
  value,
  onChange,
  disabled,
}: {
  students: Array<Record<string, unknown>>;
  value: string;
  onChange: (id: string) => void;
  disabled: boolean;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = students.find((s) => String(asNumber(s.id)) === value);

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) return students.slice(0, 8);
    return students.filter((s) => studentLabel(s).toLowerCase().includes(q)).slice(0, 8);
  }, [students, query]);

  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  if (selected) {
    return (
      <div className="flex h-10 items-center gap-2 rounded-lg border border-foreground/10 bg-surface px-3">
        <span className="min-w-0 flex-1 truncate text-sm font-semibold">
          {asString(selected.full_name) || asString(selected.student_id)}
        </span>
        <button
          type="button"
          disabled={disabled}
          onClick={() => {
            onChange("");
            setQuery("");
          }}
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted hover:bg-muted/80"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative">
      <label className="relative block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="search"
          value={query}
          disabled={disabled || !students.length}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder={students.length ? "Search student to link…" : "No available students"}
          className="h-10 w-full rounded-lg border border-foreground/10 bg-surface pl-9 pr-3 text-sm outline-none focus:border-foreground/30 disabled:opacity-50"
        />
      </label>

      {open && filtered.length > 0 ? (
        <div className="absolute left-0 right-0 top-full z-20 mt-1 overflow-hidden rounded-lg border border-foreground/10 bg-surface shadow-card-hover">
          {filtered.map((student) => {
            const id = String(asNumber(student.id));
            return (
              <button
                key={id}
                type="button"
                onPointerDown={(e) => {
                  e.preventDefault();
                  onChange(id);
                  setQuery("");
                  setOpen(false);
                }}
                className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted text-[10px] font-bold">
                  {initialsFor(student.full_name)}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold">
                    {asString(student.full_name) || "Student"}
                  </span>
                  <span className="block truncate text-[11px] text-muted-foreground">
                    {asString(student.student_id)} · {asString(student.school_name)}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export default function ParentsPanel({ state }: { state: any }) {
  const csrf = asString(state.props?.csrfToken);
  const currentSchool = asString(state.currentSchool) || "all";
  const students = Array.isArray(state.students)
    ? (state.students as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminStudents)
      ? (state.props.adminStudents as Array<Record<string, unknown>>)
      : [];
  const parentAccounts = Array.isArray(state.parentAccounts)
    ? (state.parentAccounts as Array<Record<string, unknown>>)
    : Array.isArray(state.props?.adminParents)
      ? (state.props.adminParents as Array<Record<string, unknown>>)
      : [];

  const [selectedParentId, setSelectedParentIdState] = useState(
    () => asNumber(state.activeParentId) || asNumber(parentAccounts[0]?.id),
  );
  const [parentSearch, setParentSearch] = useState("");
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    const nextParentId = asNumber(state.activeParentId);
    if (nextParentId > 0 && nextParentId !== selectedParentId) {
      setSelectedParentIdState(nextParentId);
    }
  }, [selectedParentId, state.activeParentId]);

  const selectedParent =
    parentAccounts.find((parent) => asNumber(parent.id) === selectedParentId) ||
    parentAccounts[0];
  const selectedParentResolvedId = asNumber(selectedParent?.id);
  const children = parentChildren(selectedParent);
  const childIds = new Set(
    children.map((child) => asNumber(child.id)).filter((id) => id > 0),
  );

  const visibleParents = useMemo(() => {
    const query = parentSearch.toLowerCase().trim();
    if (!query) return parentAccounts;
    return parentAccounts.filter((parent) =>
      asString(parent.login).toLowerCase().includes(query),
    );
  }, [parentAccounts, parentSearch]);

  const availableStudents = useMemo(
    () => students.filter((s) => !childIds.has(asNumber(s.id))),
    [students, childIds],
  );

  function selectParent(parentId: number) {
    setSelectedParentIdState(parentId);
    if (typeof state.setActiveParentId === "function") {
      state.setActiveParentId(parentId);
    }
  }

  function setParentAccounts(
    updater: (current: Array<Record<string, unknown>>) => Array<Record<string, unknown>>,
  ) {
    if (typeof state.setParentAccounts === "function") {
      state.setParentAccounts(updater);
    }
  }

  function updateParentChildren(
    parentId: number,
    updater: (children: Array<Record<string, unknown>>) => Array<Record<string, unknown>>,
  ) {
    setParentAccounts((current) =>
      current.map((parent) => {
        if (asNumber(parent.id) !== parentId) return parent;
        return { ...parent, children: updater(parentChildren(parent)) };
      }),
    );
  }

  async function createParent(login: string, password: string) {
    if (saving) return;
    setSaving(true);
    setCreateError("");
    try {
      const response = await fetch(routes.adminParents, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ login, password }),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setCreateError(asString(json.message) || "Unable to create parent.");
        return;
      }
      const parent = (json.parent || {}) as Record<string, unknown>;
      const parentId = asNumber(parent.id);
      if (!parentId) {
        setCreateError("Parent was created, but the record could not be loaded.");
        return;
      }
      setParentAccounts((current) =>
        [...current, parent].sort((a, b) =>
          asString(a.login).localeCompare(asString(b.login)),
        ),
      );
      selectParent(parentId);
      setShowCreate(false);
    } catch {
      setCreateError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function addChild(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parentId = selectedParentResolvedId;
    const studentId = asNumber(selectedStudentId);
    if (!parentId || !studentId || saving) return;

    setSaving(true);
    setError("");
    try {
      const response = await fetch(routes.adminParentChildrenFor(parentId), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ student_row_id: studentId }),
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to link student.");
        return;
      }
      const child = (json.child || {}) as Record<string, unknown>;
      const childId = asNumber(child.id);
      if (!childId) {
        setError("Student was linked, but the record could not be loaded.");
        return;
      }
      updateParentChildren(parentId, (current) => {
        const deduped = current.filter((item) => asNumber(item.id) !== childId);
        return [...deduped, child].sort((a, b) =>
          asString(a.full_name).localeCompare(asString(b.full_name)),
        );
      });
      setSelectedStudentId("");
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function removeChild(student: Record<string, unknown>) {
    const parentId = selectedParentResolvedId;
    const studentId = asNumber(student.id);
    if (!parentId || !studentId || saving) return;
    if (
      !window.confirm(
        `Remove ${asString(student.full_name) || "this student"} from this parent?`,
      )
    )
      return;

    setSaving(true);
    setError("");
    try {
      const response = await fetch(routes.adminParentChildFor(parentId, studentId), {
        method: "DELETE",
        headers: {
          "X-CSRFToken": csrf,
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      const json = await response.json().catch(() => ({}));
      if (!response.ok || !json.ok) {
        setError(asString(json.message) || "Unable to unlink student.");
        return;
      }
      updateParentChildren(parentId, (current) =>
        current.filter((child) => asNumber(child.id) !== studentId),
      );
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[minmax(18rem,0.42fr)_minmax(0,1fr)]">
        <ChartCard
          title="Parents"
          subtitle={`${parentAccounts.length} account${parentAccounts.length === 1 ? "" : "s"}`}
          icon={<UserRound className="h-4 w-4 text-info" />}
          headerActions={
            <button
              type="button"
              onClick={() => {
                setCreateError("");
                setShowCreate(true);
              }}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 bg-background px-2.5 text-xs font-bold hover:bg-muted"
            >
              <Plus className="h-3.5 w-3.5" />
              Create
            </button>
          }
        >
          <div className="space-y-3">
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="search"
                value={parentSearch}
                onChange={(e) => setParentSearch(e.target.value)}
                placeholder="Search parents"
                className="h-10 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
              />
            </label>

            <div className="space-y-1.5">
              {visibleParents.length ? (
                visibleParents.map((parent) => {
                  const parentId = asNumber(parent.id);
                  const active = parentId === selectedParentResolvedId;
                  const count = parentChildren(parent).length;
                  return (
                    <button
                      key={parentId}
                      type="button"
                      onClick={() => selectParent(parentId)}
                      className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                        active
                          ? "border-foreground/20 bg-foreground/6"
                          : "border-transparent hover:border-foreground/10 hover:bg-muted"
                      }`}
                    >
                      {active && (
                        <span className="absolute left-0 h-5 w-0.5 rounded-full bg-foreground" />
                      )}
                      <span
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                          active ? "bg-foreground text-background" : "bg-muted text-foreground"
                        }`}
                      >
                        {initialsFor(parent.login)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-bold">
                          {asString(parent.login)}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {count} linked {count === 1 ? "student" : "students"}
                        </span>
                      </span>
                      {count > 0 && (
                        <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] font-bold tabular-nums">
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })
              ) : (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  {parentSearch ? "No parents match your search." : "No parent accounts yet."}
                </p>
              )}
            </div>
          </div>
        </ChartCard>
        <ChartCard
          title={selectedParent ? asString(selectedParent.login) : "Parent Profile"}
          subtitle={
            selectedParent
              ? `${children.length} linked ${children.length === 1 ? "student" : "students"}`
              : "Select or create a parent"
          }
          icon={<Users className="h-4 w-4 text-info" />}
        >
          <div className="space-y-4">
            {error ? (
              <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm font-semibold text-destructive">
                {error}
              </div>
            ) : null}

            {selectedParent ? (
              <>
                <form
                  onSubmit={addChild}
                  className="flex items-center gap-2"
                >
                  <div className="flex-1">
                    <StudentCombobox
                      students={availableStudents}
                      value={selectedStudentId}
                      onChange={setSelectedStudentId}
                      disabled={saving}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={saving || !selectedStudentId}
                    className="inline-flex h-10 shrink-0 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground transition-opacity disabled:opacity-40"
                  >
                    <UserPlus className="h-4 w-4" />
                    Link
                  </button>
                </form>
                {children.length ? (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {children.map((child) => {
                      const studentId = asNumber(child.id);
                      const seen = formatLastSeen(child.last_seen_at);
                      return (
                        <div
                          key={studentId || asString(child.student_id)}
                          className="rounded-lg border border-foreground/10 bg-background p-3 shadow-card"
                        >
                          <div className="flex min-w-0 items-start gap-3">
                            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold">
                              {initialsFor(child.full_name)}
                            </span>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-bold">
                                {asString(child.full_name) || "Student"}
                              </p>
                              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                                {asString(child.student_id)} ·{" "}
                                {asString(child.school_name) || "School"}
                              </p>
                              <p
                                className={`mt-1.5 text-[11px] font-semibold ${
                                  seen.online ? "text-emerald-600" : "text-muted-foreground"
                                }`}
                              >
                                {seen.label}
                              </p>
                            </div>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <a
                              href={routes.adminStudentDashboard(studentId, currentSchool)}
                              className="inline-flex h-8 items-center rounded-lg border border-foreground/10 px-2.5 text-xs font-bold hover:bg-muted"
                            >
                              Dashboard
                            </a>
                            <button
                              type="button"
                              onClick={() => removeChild(child)}
                              disabled={saving}
                              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-destructive/20 bg-destructive/10 px-2.5 text-xs font-bold text-destructive hover:bg-destructive/15 disabled:opacity-50"
                            >
                              <UserMinus className="h-3.5 w-3.5" />
                              Unlink
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="py-2 text-sm text-muted-foreground">
                    No students linked to this parent yet. Search above to link one.
                  </p>
                )}
              </>
            ) : (
              <p className="py-2 text-sm text-muted-foreground">
                Select a parent from the list, or create a new one.
              </p>
            )}
          </div>
        </ChartCard>
      </div>

      {showCreate ? (
        <CreateParentModal
          csrf={csrf}
          saving={saving}
          error={createError}
          onClose={() => setShowCreate(false)}
          onSubmit={createParent}
        />
      ) : null}

    </>
  );
}
