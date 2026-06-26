import { Search, SlidersHorizontal, X } from "lucide-react";
import { type ParentFilters } from "./types";

const selectClass =
  "h-9 rounded-lg border border-foreground/10 bg-background px-2.5 text-xs font-semibold text-foreground outline-none focus:border-foreground/30";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

export function ParentToolbar({
  filters,
  groupOptions,
  activeCount,
  onChange,
  onClear,
}: {
  filters: ParentFilters;
  groupOptions: string[];
  activeCount: number;
  onChange: (patch: Partial<ParentFilters>) => void;
  onClear: () => void;
}) {
  return (
    <div className="space-y-3 rounded-lg border border-foreground/10 bg-surface p-3 shadow-card">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
        <label className="relative block flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={filters.search}
            onChange={(event) => onChange({ search: event.target.value })}
            placeholder="Search by name, phone, Telegram, login, or student"
            aria-label="Search parents"
            className="h-9 w-full rounded-lg border border-foreground/10 bg-background pl-9 pr-3 text-sm outline-none focus:border-foreground/30"
          />
        </label>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-muted px-2.5 py-1.5 text-[11px] font-bold text-muted-foreground">
            <SlidersHorizontal className="h-3.5 w-3.5" />
            {activeCount} active {activeCount === 1 ? "filter" : "filters"}
          </span>
          {activeCount > 0 ? (
            <button
              type="button"
              onClick={onClear}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground/10 bg-background px-2.5 text-[11px] font-bold hover:bg-muted"
            >
              <X className="h-3.5 w-3.5" />
              Clear filters
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
        <Field label="Account">
          <select
            value={filters.account}
            onChange={(event) => onChange({ account: event.target.value as ParentFilters["account"] })}
            className={selectClass}
          >
            <option value="all">All accounts</option>
            <option value="active">Active</option>
            <option value="disabled">Disabled</option>
            <option value="invite">Registered from link</option>
          </select>
        </Field>
        <Field label="Student link">
          <select
            value={filters.link}
            onChange={(event) => onChange({ link: event.target.value as ParentFilters["link"] })}
            className={selectClass}
          >
            <option value="all">All</option>
            <option value="linked">Linked</option>
            <option value="unlinked">Not linked</option>
          </select>
        </Field>
        <Field label="Contact">
          <select
            value={filters.contact}
            onChange={(event) => onChange({ contact: event.target.value as ParentFilters["contact"] })}
            className={selectClass}
          >
            <option value="all">All</option>
            <option value="phone">Phone available</option>
            <option value="no_phone">Missing phone</option>
            <option value="tg">Telegram connected</option>
            <option value="no_tg">Telegram not connected</option>
          </select>
        </Field>
        <Field label="Group / class">
          <select
            value={filters.groupClass}
            onChange={(event) => onChange({ groupClass: event.target.value })}
            className={selectClass}
          >
            <option value="all">All groups</option>
            {groupOptions.map((group) => (
              <option key={group} value={group}>
                {group}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Tickets">
          <select
            value={filters.tickets}
            onChange={(event) => onChange({ tickets: event.target.value as ParentFilters["tickets"] })}
            className={selectClass}
          >
            <option value="all">All</option>
            <option value="open">Has open tickets</option>
            <option value="none">No open tickets</option>
          </select>
        </Field>
      </div>
    </div>
  );
}
