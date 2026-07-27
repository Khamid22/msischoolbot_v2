import { Search } from "lucide-react";
import type { SupportContext } from "@/features/customer-support/model";
import { inputClass, Label } from "@/features/customer-support/shared/ui";

export function TeacherFilters({
  context,
  loadingContext,
  query,
  status,
  schoolId,
  onQueryChange,
  onStatusChange,
  onSchoolChange,
}: {
  context: SupportContext | null;
  loadingContext: boolean;
  query: string;
  status: string;
  schoolId: string;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onSchoolChange: (value: string) => void;
}) {
  return (
    <section
      className="sticky top-0 z-20 rounded-lg border border-border bg-card/95 p-3 shadow-card backdrop-blur sm:p-4"
      aria-label="Teacher search filters"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(18rem,1fr)_12rem_14rem] lg:items-end">
        <div>
          <Label htmlFor="teacher-support-search">Search teachers</Label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              id="teacher-support-search"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              className={`${inputClass} pl-10`}
              placeholder="Name, login, contact, subject, group…"
              autoComplete="off"
            />
          </div>
        </div>
        <div>
          <Label htmlFor="teacher-support-status">Status</Label>
          <select
            id="teacher-support-status"
            value={status}
            onChange={(event) => onStatusChange(event.target.value)}
            className={inputClass}
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="disabled">Disabled</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div>
          <Label htmlFor="teacher-support-school">School</Label>
          <select
            id="teacher-support-school"
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
      </div>
    </section>
  );
}
