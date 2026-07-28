import { Filter, Search } from "lucide-react";
import { type FormEvent, type ReactNode, useRef, useState } from "react";
import type {
  SupportSchool,
  SupportTicketPriority,
  SupportTicketSlaState,
  SupportTicketStatus,
} from "@/features/customer-support/model";
import { inputClass, secondaryButton } from "@/features/customer-support/shared/ui";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";

const TICKET_STATUSES: Array<{ value: "" | SupportTicketStatus; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "new", label: "New" },
  { value: "in_progress", label: "In progress" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
];

const TICKET_CATEGORIES = [
  "complaint",
  "direct_contact",
  "payment",
  "teacher",
  "lesson_quality",
  "schedule",
  "attendance",
  "technical",
  "account",
  "other",
] as const;

const FILTER_PANEL_CLASS = [
  "absolute right-2 top-[calc(100%+0.5rem)] z-30",
  "w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-border",
  "bg-card p-3 shadow-card-hover",
].join(" ");

const RESET_BUTTON_CLASS = [
  "min-h-11 rounded-md px-2 text-xs font-black text-primary",
  "hover:bg-primary/10 focus:outline-none focus-visible:ring-2",
  "focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-40",
].join(" ");

const DONE_BUTTON_CLASS = [
  "mt-3 min-h-11 w-full rounded-lg bg-primary px-3",
  "text-sm font-black text-primary-foreground focus:outline-none",
  "focus-visible:ring-2 focus-visible:ring-primary/35",
].join(" ");

export type TicketQueueFilterValues = {
  status: "" | SupportTicketStatus;
  schoolId: string;
  category: string;
  priority: "" | SupportTicketPriority;
  slaState: "" | SupportTicketSlaState;
  assignment: "" | "mine" | "unassigned";
};

type TicketQueueFiltersProps = {
  searchInput: string;
  filters: TicketQueueFilterValues;
  schools: SupportSchool[];
  isSchoolLoading: boolean;
  onSearchInputChange: (value: string) => void;
  onSearch: () => void;
  onFiltersChange: (filters: TicketQueueFilterValues) => void;
};

function CompactFilterField({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label
      className={`min-w-0 text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground ${className}`}
    >
      {label}
      <span className="mt-1 block">{children}</span>
    </label>
  );
}

export function TicketQueueFilters({
  searchInput,
  filters,
  schools,
  isSchoolLoading,
  onSearchInputChange,
  onSearch,
  onFiltersChange,
}: TicketQueueFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);
  const filterButtonRef = useRef<HTMLButtonElement>(null);
  const filterPanelRef = useRef<HTMLDivElement>(null);
  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  useDismissibleLayer<HTMLDivElement>({
    enabled: isOpen,
    refs: [filterButtonRef, filterPanelRef],
    onDismiss: (event) => {
      setIsOpen(false);
      if (event instanceof KeyboardEvent) filterButtonRef.current?.focus();
    },
  });

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch();
  }

  function update<K extends keyof TicketQueueFilterValues>(
    key: K,
    value: TicketQueueFilterValues[K],
  ) {
    onFiltersChange({ ...filters, [key]: value });
  }

  function clearFilters() {
    onFiltersChange({
      status: "",
      schoolId: "",
      category: "",
      priority: "",
      slaState: "",
      assignment: "",
    });
  }

  return (
    <form
      role="search"
      aria-label="Search and filter support tickets"
      onSubmit={submitSearch}
      className="relative flex items-center gap-2 rounded-lg border border-border bg-card p-2 shadow-sm"
    >
      <label className="relative min-w-0 flex-1">
        <span className="sr-only">Search parent name or ticket topic</span>
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          type="search"
          value={searchInput}
          onChange={(event) => onSearchInputChange(event.target.value)}
          className={`${inputClass} pl-10`}
          placeholder="Search parent or ticket topic"
          maxLength={200}
        />
      </label>
      <button
        ref={filterButtonRef}
        type="button"
        aria-expanded={isOpen}
        aria-controls="ticket-filter-popover"
        aria-haspopup="dialog"
        onClick={() => setIsOpen((current) => !current)}
        className={`${secondaryButton} relative shrink-0 px-3 sm:px-4 ${
          isOpen || activeFilterCount ? "border-primary/40 bg-primary/10 text-primary" : ""
        }`}
      >
        <Filter className="h-4 w-4" aria-hidden="true" />
        <span>Filter</span>
        {activeFilterCount ? (
          <span
            className={[
              "min-w-5 rounded-full bg-primary px-1.5 py-0.5 text-center",
              "text-[0.625rem] font-black leading-4 text-primary-foreground",
            ].join(" ")}
            aria-label={`${activeFilterCount} active filters`}
          >
            {activeFilterCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div
          ref={filterPanelRef}
          id="ticket-filter-popover"
          role="dialog"
          aria-label="Ticket filters"
          className={FILTER_PANEL_CLASS}
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-black text-foreground">Filters</h2>
              <p className="text-xs font-semibold text-muted-foreground">
                Results update immediately.
              </p>
            </div>
            <button
              type="button"
              onClick={clearFilters}
              disabled={!activeFilterCount}
              className={RESET_BUTTON_CLASS}
            >
              Reset
            </button>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2">
            <CompactFilterField label="Status">
              <select
                value={filters.status}
                onChange={(event) => update(
                  "status",
                  event.target.value as TicketQueueFilterValues["status"],
                )}
                className={inputClass}
              >
                {TICKET_STATUSES.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </CompactFilterField>
            <CompactFilterField label="Priority">
              <select
                value={filters.priority}
                onChange={(event) => update(
                  "priority",
                  event.target.value as TicketQueueFilterValues["priority"],
                )}
                className={inputClass}
              >
                <option value="">All priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </CompactFilterField>
            <CompactFilterField label="Category">
              <select
                value={filters.category}
                onChange={(event) => update("category", event.target.value)}
                className={inputClass}
              >
                <option value="">All categories</option>
                {TICKET_CATEGORIES.map((value) => (
                  <option key={value} value={value}>
                    {value.split("_").join(" ")}
                  </option>
                ))}
              </select>
            </CompactFilterField>
            <CompactFilterField label="SLA">
              <select
                value={filters.slaState}
                onChange={(event) => update(
                  "slaState",
                  event.target.value as TicketQueueFilterValues["slaState"],
                )}
                className={inputClass}
              >
                <option value="">All SLA states</option>
                <option value="breached">Breached</option>
                <option value="due_soon">Due soon</option>
                <option value="paused">Waiting on parent</option>
                <option value="on_track">On track</option>
              </select>
            </CompactFilterField>
            <CompactFilterField label="School" className="col-span-2">
              <select
                value={filters.schoolId}
                onChange={(event) => update("schoolId", event.target.value)}
                className={inputClass}
                disabled={isSchoolLoading}
              >
                <option value="">All assigned schools</option>
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.school_name}
                  </option>
                ))}
              </select>
            </CompactFilterField>
            <CompactFilterField label="Assignment" className="col-span-2">
              <select
                value={filters.assignment}
                onChange={(event) => update(
                  "assignment",
                  event.target.value as TicketQueueFilterValues["assignment"],
                )}
                className={inputClass}
              >
                <option value="">Any assignment</option>
                <option value="mine">Assigned to me</option>
                <option value="unassigned">Unassigned</option>
              </select>
            </CompactFilterField>
          </div>

          <button
            type="button"
            onClick={() => {
              setIsOpen(false);
              filterButtonRef.current?.focus();
            }}
            className={DONE_BUTTON_CLASS}
          >
            Done
          </button>
        </div>
      ) : null}
    </form>
  );
}
