import { Search } from "lucide-react";
import type { ReactNode } from "react";
import type { SupportContext, SupportRecordKind } from "@/features/customer-support/model";
import { inputClass, Label } from "@/features/customer-support/shared/ui";

export function RecordsSearchBar({
  kind,
  context,
  loadingContext,
  query,
  status,
  schoolId,
  fixedSchoolLabel,
  onQueryChange,
  onStatusChange,
  onSchoolChange,
  action,
}: {
  kind: SupportRecordKind;
  context: SupportContext | null;
  loadingContext: boolean;
  query: string;
  status: string;
  schoolId: string;
  fixedSchoolLabel?: string;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onSchoolChange: (value: string) => void;
  action?: ReactNode;
}) {
  const searchId = `${kind}-records-search`;
  const statusId = `${kind}-record-status`;
  const schoolIdValue = `${kind}-record-school`;

  return (
    <section className="sticky top-0 z-20 rounded-lg border border-border bg-card/95 p-3 shadow-card backdrop-blur sm:p-4" aria-label={`${kind} search filters`}>
      <div className={`grid gap-3 ${action ? "lg:grid-cols-[minmax(18rem,1fr)_12rem_14rem_auto]" : "lg:grid-cols-[minmax(18rem,1fr)_12rem_14rem]"} lg:items-end`}>
        <div>
          <Label htmlFor={searchId}>Search {kind === "student" ? "students" : "parents"}</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <input
              id={searchId}
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              className={`${inputClass} pl-10`}
              placeholder={kind === "student" ? "Name, code, phone, Telegram…" : "Name, contact, student, school…"}
              autoComplete="off"
            />
          </div>
        </div>
        <div>
          <Label htmlFor={statusId}>Status</Label>
          <select id={statusId} value={status} onChange={(event) => onStatusChange(event.target.value)} className={inputClass}>
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="disabled">Disabled</option>
            {kind === "student" ? <option value="archived">Archived</option> : null}
          </select>
        </div>
        {fixedSchoolLabel ? (
          <div>
            <p className="mb-1.5 text-xs font-black uppercase tracking-wide text-muted-foreground">School</p>
            <div className="flex min-h-11 items-center rounded-lg border border-primary/20 bg-primary/8 px-3 text-sm font-black text-primary">
              {fixedSchoolLabel} only
            </div>
          </div>
        ) : (
          <div>
            <Label htmlFor={schoolIdValue}>School</Label>
            <select
              id={schoolIdValue}
              value={schoolId}
              onChange={(event) => onSchoolChange(event.target.value)}
              className={inputClass}
              disabled={loadingContext}
            >
              <option value="">All allowed schools</option>
              {context?.schools.map((school) => (
                <option key={school.id} value={school.id}>{school.school_name}</option>
              ))}
            </select>
          </div>
        )}
        {action}
      </div>
    </section>
  );
}
