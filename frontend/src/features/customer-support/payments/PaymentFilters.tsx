import { Filter, Search } from "lucide-react";
import { type FormEvent, type ReactNode, useRef, useState } from "react";
import type { SupportSchool } from "@/features/customer-support/model";
import { inputClass, secondaryButton } from "@/features/customer-support/shared/ui";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";

export type PaymentView = "accounts" | "invoices";

export type AccountFilters = {
  schoolId: string;
  accountType: string;
  scheduleStatus: string;
  attention: string;
  access: string;
};

export type InvoiceFilters = {
  schoolId: string;
  status: string;
  origin: string;
  billingPeriod: string;
  access: string;
};

type Props = {
  view: PaymentView;
  searchInput: string;
  schools: SupportSchool[];
  accountFilters: AccountFilters;
  invoiceFilters: InvoiceFilters;
  onSearchInputChange: (value: string) => void;
  onSearch: () => void;
  onAccountFiltersChange: (value: AccountFilters) => void;
  onInvoiceFiltersChange: (value: InvoiceFilters) => void;
};

const PANEL_CLASS = [
  "absolute right-2 top-[calc(100%+0.5rem)] z-30",
  "w-[min(24rem,calc(100vw-2rem))] rounded-lg border border-border",
  "bg-card p-3 shadow-card-hover",
].join(" ");

export function PaymentFilters({
  view,
  searchInput,
  schools,
  accountFilters,
  invoiceFilters,
  onSearchInputChange,
  onSearch,
  onAccountFiltersChange,
  onInvoiceFiltersChange,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const activeFilters = view === "accounts"
    ? Object.values(accountFilters).filter((value) => value && value !== "all").length
    : Object.values(invoiceFilters).filter((value) => value && value !== "all").length;

  useDismissibleLayer<HTMLDivElement>({
    enabled: isOpen,
    refs: [buttonRef, panelRef],
    onDismiss: (event) => {
      setIsOpen(false);
      if (event instanceof KeyboardEvent) buttonRef.current?.focus();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch();
  }

  function reset() {
    if (view === "accounts") {
      onAccountFiltersChange({
        schoolId: "",
        accountType: "all",
        scheduleStatus: "all",
        attention: "all",
        access: "all",
      });
    } else {
      onInvoiceFiltersChange({
        schoolId: "",
        status: "all",
        origin: "all",
        billingPeriod: "",
        access: "all",
      });
    }
  }

  return (
    <form
      role="search"
      aria-label={`Search and filter billing ${view}`}
      onSubmit={submit}
      className="relative flex items-center gap-2 rounded-lg border border-border bg-card p-2 shadow-sm"
    >
      <label className="relative min-w-0 flex-1">
        <span className="sr-only">Search billing {view}</span>
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          type="search"
          value={searchInput}
          onChange={(event) => onSearchInputChange(event.target.value)}
          className={`${inputClass} pl-10`}
          placeholder={view === "accounts"
            ? "Student, parent, code, or school"
            : "Invoice, student, parent, or code"}
          maxLength={200}
        />
      </label>
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={isOpen}
        aria-controls="payment-filter-popover"
        aria-haspopup="dialog"
        onClick={() => setIsOpen((current) => !current)}
        className={`${secondaryButton} relative shrink-0 px-3 sm:px-4 ${
          isOpen || activeFilters ? "border-primary/40 bg-primary/10 text-primary" : ""
        }`}
      >
        <Filter className="h-4 w-4" aria-hidden="true" />
        <span>Filter</span>
        {activeFilters ? (
          <span className="min-w-5 rounded-full bg-primary px-1.5 py-0.5 text-center text-[0.625rem] font-black leading-4 text-primary-foreground">
            {activeFilters}
          </span>
        ) : null}
      </button>
      {isOpen ? (
        <div
          ref={panelRef}
          id="payment-filter-popover"
          role="dialog"
          aria-label={`${view === "accounts" ? "Billing account" : "Invoice"} filters`}
          className={PANEL_CLASS}
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
              onClick={reset}
              disabled={!activeFilters}
              className="min-h-11 rounded-md px-2 text-xs font-black text-primary hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-40"
            >
              Reset
            </button>
          </div>
          {view === "accounts" ? (
            <AccountFilterFields
              filters={accountFilters}
              schools={schools}
              onChange={onAccountFiltersChange}
            />
          ) : (
            <InvoiceFilterFields
              filters={invoiceFilters}
              schools={schools}
              onChange={onInvoiceFiltersChange}
            />
          )}
          <button
            type="button"
            onClick={() => {
              setIsOpen(false);
              buttonRef.current?.focus();
            }}
            className="mt-3 min-h-11 w-full rounded-lg bg-primary px-3 text-sm font-black text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
          >
            Done
          </button>
        </div>
      ) : null}
    </form>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="text-[0.6875rem] font-black uppercase tracking-wide text-muted-foreground">
      {label}
      <span className="mt-1 block">{children}</span>
    </label>
  );
}

function SchoolField({
  value,
  schools,
  onChange,
}: {
  value: string;
  schools: SupportSchool[];
  onChange: (value: string) => void;
}) {
  return (
    <Field label="School">
      <select className={inputClass} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All assigned schools</option>
        {schools.map((school) => (
          <option key={school.id} value={school.id}>{school.school_name}</option>
        ))}
      </select>
    </Field>
  );
}

function AccountFilterFields({
  filters,
  schools,
  onChange,
}: {
  filters: AccountFilters;
  schools: SupportSchool[];
  onChange: (value: AccountFilters) => void;
}) {
  const update = (key: keyof AccountFilters, value: string) => {
    onChange({ ...filters, [key]: value });
  };
  return (
    <div className="mt-3 grid grid-cols-2 gap-2">
      <SchoolField
        value={filters.schoolId}
        schools={schools}
        onChange={(value) => update("schoolId", value)}
      />
      <Field label="Account">
        <select className={inputClass} value={filters.accountType} onChange={(event) => update("accountType", event.target.value)}>
          <option value="all">All accounts</option>
          <option value="student">Students</option>
          <option value="admission">Admissions</option>
        </select>
      </Field>
      <Field label="Schedule">
        <select className={inputClass} value={filters.scheduleStatus} onChange={(event) => update("scheduleStatus", event.target.value)}>
          <option value="all">All schedules</option>
          <option value="missing">Missing</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="ended">Ended</option>
        </select>
      </Field>
      <Field label="Attention">
        <select className={inputClass} value={filters.attention} onChange={(event) => update("attention", event.target.value)}>
          <option value="all">All attention states</option>
          <option value="payment_only">Payment-only</option>
          <option value="overdue">Overdue</option>
          <option value="due_without_invoice">Due without invoice</option>
          <option value="missing_schedule">Missing schedule</option>
          <option value="enforcement_missing">Enforcement missing</option>
        </select>
      </Field>
      <Field label="Access">
        <select className={inputClass} value={filters.access} onChange={(event) => update("access", event.target.value)}>
          <option value="all">All access states</option>
          <option value="normal">Normal</option>
          <option value="countdown">Countdown</option>
          <option value="payment_only">Payment-only</option>
        </select>
      </Field>
    </div>
  );
}

function InvoiceFilterFields({
  filters,
  schools,
  onChange,
}: {
  filters: InvoiceFilters;
  schools: SupportSchool[];
  onChange: (value: InvoiceFilters) => void;
}) {
  const update = (key: keyof InvoiceFilters, value: string) => {
    onChange({ ...filters, [key]: value });
  };
  return (
    <div className="mt-3 grid grid-cols-2 gap-2">
      <SchoolField
        value={filters.schoolId}
        schools={schools}
        onChange={(value) => update("schoolId", value)}
      />
      <Field label="Status">
        <select className={inputClass} value={filters.status} onChange={(event) => update("status", event.target.value)}>
          <option value="all">All statuses</option>
          {["issued", "partially_paid", "overdue", "paid", "voided"].map((value) => (
            <option key={value} value={value}>{value.replace(/_/g, " ")}</option>
          ))}
        </select>
      </Field>
      <Field label="Source">
        <select className={inputClass} value={filters.origin} onChange={(event) => update("origin", event.target.value)}>
          <option value="all">All sources</option>
          <option value="student_billing">Student billing</option>
          <option value="admission">Admission</option>
          <option value="legacy_migration">Migrated</option>
        </select>
      </Field>
      <Field label="Billing period">
        <input
          type="month"
          className={inputClass}
          value={filters.billingPeriod}
          onChange={(event) => update("billingPeriod", event.target.value)}
        />
      </Field>
      <Field label="Access">
        <select className={inputClass} value={filters.access} onChange={(event) => update("access", event.target.value)}>
          <option value="all">All access states</option>
          <option value="countdown">Countdown</option>
          <option value="held">Payment-only</option>
          <option value="cleared">Restored</option>
          <option value="not_scheduled">Not scheduled</option>
        </select>
      </Field>
    </div>
  );
}
