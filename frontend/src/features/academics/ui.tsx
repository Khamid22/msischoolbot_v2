import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { BarChart3 as BarChartIcon, Filter, Table2 } from "lucide-react";
import { motion } from "@/shared/lib/motion";
import { asString } from "@/shared/lib/workspace";

import { collectPeriodOptions, examTypeKey, monthLabels, type ExamTypeOption } from "./gradebook/model";

export function FieldLabel({ children }: { children: string }) {
  return (
    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className="w-full rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-sm outline-none focus:border-foreground/30"
    />
  );
}

export function PeriodFilter({
  month,
  year,
  months,
  years,
  onMonthChange,
  onYearChange,
}: {
  month: string;
  year: string;
  months: string[];
  years: string[];
  onMonthChange: (value: string) => void;
  onYearChange: (value: string) => void;
}) {
  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
      <span className="inline-flex items-center gap-1.5 text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground sm:justify-end">
        <Filter className="h-3.5 w-3.5" />
        Filter
      </span>
      <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto">
        <select
          value={month}
          onChange={(event) => onMonthChange(event.target.value)}
          className="h-9 w-full min-w-0 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-semibold outline-none focus:border-foreground/30 sm:min-w-[8.5rem]"
        >
          <option value="all">All months</option>
          {months.map((value) => (
            <option key={value} value={value}>
              {monthLabels.find((item) => item.value === value)?.label || value}
            </option>
          ))}
        </select>
        <select
          value={year}
          onChange={(event) => onYearChange(event.target.value)}
          className="h-9 w-full min-w-0 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-semibold outline-none focus:border-foreground/30 sm:min-w-[6.5rem]"
        >
          <option value="all">All years</option>
          {years.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export function ExamTypeFilter({
  value,
  options,
  onChange,
}: {
  value: string;
  options: ExamTypeOption[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
      <span className="inline-flex items-center gap-1.5 text-[0.6875rem] font-bold uppercase tracking-wide text-muted-foreground sm:justify-end">
        <Filter className="h-3.5 w-3.5" />
        Show
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full min-w-0 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-semibold outline-none focus:border-foreground/30 sm:min-w-[8.5rem]"
      >
        <option value="all">All exams</option>
        {options.map((option) => (
          <option key={option.key} value={option.key}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ExamViewSwitcher({
  value,
  onChange,
}: {
  value: "chart" | "table";
  onChange: (value: "chart" | "table") => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-foreground/10 bg-muted/50 p-0.5 shadow-sm">
      {([
        { key: "chart", label: "Chart", icon: <BarChartIcon className="h-3 w-3" /> },
        { key: "table", label: "Table", icon: <Table2 className="h-3 w-3" /> },
      ] as const).map((option) => {
        const active = value === option.key;
        return (
          <button
            key={option.key}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.key)}
            className={`inline-flex min-h-10 items-center gap-1.5 rounded-md px-2 text-[0.6875rem] font-bold transition-[transform,background-color,color,box-shadow] duration-200 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 sm:min-h-8 motion-reduce:transition-none motion-reduce:active:scale-100 ${
              active ? "bg-surface text-foreground shadow-card" : "text-muted-foreground hover:bg-surface/70 hover:text-foreground"
            }`}
          >
            {option.icon}
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

export function Pill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-6 items-center rounded-md border border-foreground/10 bg-muted px-2 text-xs font-semibold text-muted-foreground">
      {children}
    </span>
  );
}

export function MiniMetric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2">
      <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-lg font-bold leading-none">{value}</p>
    </div>
  );
}

export function CompactMetric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-[0.6875rem] font-semibold text-muted-foreground">
      {icon}
      <span className="font-bold text-foreground">{value}</span>
      {label}
    </span>
  );
}

export const subjectSwatches = [
  "bg-primary",
  "bg-info",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-cyan-500",
  "bg-violet-500",
] as const;

export function programInitials(value: unknown) {
  const first = asString(value).trim().split(/\s+/)[0] || "";
  return (first.slice(0, 2) || "—").toUpperCase();
}
