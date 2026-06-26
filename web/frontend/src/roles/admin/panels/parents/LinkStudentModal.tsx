import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { type ParentRow, parentChildren, parentDisplayName, parentInitials } from "./types";
import { asNumber, asString, getStudentCode, getStudentRowId } from "../../shared";

export function LinkStudentModal({
  parent,
  students,
  saving,
  error,
  onClose,
  onLink,
}: {
  parent: ParentRow;
  students: ParentRow[];
  saving: boolean;
  error: string;
  onClose: () => void;
  onLink: (studentRowId: number) => void;
}) {
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    searchRef.current?.focus();
  }, []);

  const linkedIds = useMemo(
    () => new Set(parentChildren(parent).map((child) => asNumber(child.student_row_id ?? child.id))),
    [parent],
  );

  const available = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return students
      .filter((student) => !linkedIds.has(getStudentRowId(student)))
      .filter((student) => {
        if (!normalized) return true;
        const haystack = [
          asString(student.full_name),
          getStudentCode(student),
          asString(student.subjects),
          asString(student.school_name),
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalized);
      })
      .slice(0, 60);
  }, [students, linkedIds, query]);

  return (
    <div className="fixed inset-0 z-[75] flex items-center justify-center bg-foreground/60 p-4" onClick={onClose}>
      <div
        className="flex max-h-[85dvh] w-full max-w-md flex-col overflow-hidden rounded-xl bg-surface shadow-card-hover"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-foreground/8 px-4 py-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold">
              {parentInitials(parentDisplayName(parent))}
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-sm font-bold">Link a student</h3>
              <p className="truncate text-xs text-muted-foreground">to {parentDisplayName(parent)}</p>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="shrink-0 border-b border-foreground/8 p-3">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              ref={searchRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by name, code, or subject"
              aria-label="Search students"
              className="h-10 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
            />
          </label>
          {error ? <p className="mt-2 text-xs font-semibold text-destructive">{error}</p> : null}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {available.length ? (
            <ul className="space-y-1.5">
              {available.map((student) => {
                const rowId = getStudentRowId(student);
                return (
                  <li key={rowId || getStudentCode(student)}>
                    <button
                      type="button"
                      disabled={saving || rowId <= 0}
                      onClick={() => onLink(rowId)}
                      className="flex w-full items-center gap-3 rounded-lg border border-foreground/10 bg-background px-3 py-2 text-left transition-colors hover:bg-muted disabled:opacity-50"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-bold">
                        {parentInitials(asString(student.full_name))}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-bold">{asString(student.full_name) || "Student"}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          Code {getStudentCode(student) || "—"}
                          {asString(student.school_name) ? ` · ${asString(student.school_name)}` : ""}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="rounded-lg border border-dashed border-foreground/15 bg-background px-4 py-10 text-center">
              <p className="text-sm font-bold">No students found</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {query ? "Try a different search." : "Every student is already linked."}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
