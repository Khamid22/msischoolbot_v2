// Shared types, constants, and pure helpers for the Overview panel.
import { asString } from "@/shared/lib/workspace";

export type ZoneKey = "red" | "yellow" | "green";

export type MonthlyGroupRow = {
  label: string;
  students: number;
  current: number | null;
  previous: number | null;
  delta: number | null;
  ar: number | null;
  monthly_ar: number | null;
  display_ar: number | null;
  zone: string;
};

export type ExamClassOption = { shortName: string; label: string; average: number | null; rows: Array<{ label: string; average: number | null }> };
export type GraphMetric = "academic" | "exam";
export type GraphLineSeries = {
  key: string;
  dataKey: string;
  name: string;
  yAxisId: "aap" | "score";
  color: string;
};
export type AcademicBarRow = {
  label: string;
  aapAverage: number | null;
  arAverage: number | null;
  sortAverage: number | null;
};
export type MonthOption = {
  index: number;
  key: string;
  label: string;
  month: number;
  year: number;
  academicYear: string;
  academicYearLabel: string;
};

export const lineColors = ["#8b5cf6", "#2563eb", "#10b981", "#f59e0b", "#ef4444", "#14b8a6", "#ec4899", "#64748b"];
export const scoreAxisTicks = [1, 2, 3, 4, 5, 6, 7, 8, 9];
export const groupNameCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

export function safeSvgId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

export function numericGraphValue(value: unknown): number | null {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
}

export function averageGraphValue(values: unknown[]): number | null {
  const nums = values
    .map((value) => numericGraphValue(value))
    .filter((value): value is number => value != null);
  if (!nums.length) return null;
  return nums.reduce((sum, value) => sum + value, 0) / nums.length;
}

export function normalizedAcademicAverage(aapValues: unknown[], arValues: unknown[]): number | null {
  const normalized = [
    ...aapValues
      .map((value) => numericGraphValue(value))
      .filter((value): value is number => value != null)
      .map((value) => value / 9),
    ...arValues
      .map((value) => numericGraphValue(value))
      .filter((value): value is number => value != null)
      .map((value) => value / 100),
  ];
  if (!normalized.length) return null;
  return normalized.reduce((sum, value) => sum + value, 0) / normalized.length;
}

export function compareAverageRowsDesc<T extends { label: string; average: number | null }>(left: T, right: T): number {
  const leftAverage = left.average ?? Number.NEGATIVE_INFINITY;
  const rightAverage = right.average ?? Number.NEGATIVE_INFINITY;
  if (leftAverage !== rightAverage) return rightAverage - leftAverage;
  return groupNameCollator.compare(right.label, left.label);
}

export function compareAcademicRowsDesc<T extends { label: string; sortAverage: number | null }>(left: T, right: T): number {
  const leftAverage = left.sortAverage ?? Number.NEGATIVE_INFINITY;
  const rightAverage = right.sortAverage ?? Number.NEGATIVE_INFINITY;
  if (leftAverage !== rightAverage) return rightAverage - leftAverage;
  return groupNameCollator.compare(right.label, left.label);
}

export function compareZoneGroupRowsDesc(left: Record<string, unknown>, right: Record<string, unknown>): number {
  const groupCompare = groupNameCollator.compare(asString(right.group_name), asString(left.group_name));
  if (groupCompare !== 0) return groupCompare;
  return groupNameCollator.compare(asString(right.subject_name), asString(left.subject_name));
}

export function lineRowAverage(row: Record<string, unknown>, labels: string[]): number | null {
  return averageGraphValue(labels.map((label) => row[label]));
}

export function compareLineRowsDesc(labels: string[]) {
  return (left: Record<string, unknown>, right: Record<string, unknown>) => {
    const leftAverage = lineRowAverage(left, labels) ?? Number.NEGATIVE_INFINITY;
    const rightAverage = lineRowAverage(right, labels) ?? Number.NEGATIVE_INFINITY;
    if (leftAverage !== rightAverage) return rightAverage - leftAverage;
    const leftLabel = asString(left.shortName) || asString(left.label);
    const rightLabel = asString(right.shortName) || asString(right.label);
    return groupNameCollator.compare(rightLabel, leftLabel);
  };
}

export function compareLineLabelsDesc(data: Array<Record<string, unknown>>) {
  return (left: string, right: string) => {
    const leftAverage = averageGraphValue(data.map((row) => row[left])) ?? Number.NEGATIVE_INFINITY;
    const rightAverage = averageGraphValue(data.map((row) => row[right])) ?? Number.NEGATIVE_INFINITY;
    if (leftAverage !== rightAverage) return rightAverage - leftAverage;
    return groupNameCollator.compare(right, left);
  };
}

export const zoneStyles: Record<ZoneKey, { soft: string; text: string; ring: string; dot: string }> = {
  red: {
    soft: "bg-rose-50",
    text: "text-rose-700",
    ring: "border-rose-200",
    dot: "bg-rose-500",
  },
  yellow: {
    soft: "bg-amber-50",
    text: "text-amber-700",
    ring: "border-amber-200",
    dot: "bg-amber-500",
  },
  green: {
    soft: "bg-emerald-50",
    text: "text-emerald-700",
    ring: "border-emerald-200",
    dot: "bg-emerald-500",
  },
};

export function metricAverage(values: Array<number | null>): number | null {
  const nums = values.filter((v): v is number => v != null);
  if (!nums.length) return null;
  return Math.round((nums.reduce((a, b) => a + b, 0) / nums.length) * 10) / 10;
}

export function academicMonthOption(row: Record<string, unknown>, index: number): MonthOption | null {
  const key = asString(row.month);
  const label = asString(row.monthLabel) || key;
  const match = key.match(/^(\d{4})-(\d{1,2})$/);
  if (!match) {
    return {
      index,
      key,
      label,
      month: 0,
      year: 0,
      academicYear: "unknown",
      academicYearLabel: "Other",
    };
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!Number.isFinite(year) || !Number.isFinite(month)) return null;
  if (month < 1 || month > 12) return null;
  if (month >= 6 && month <= 8) return null;

  const academicYearStart = month >= 9 ? year : year - 1;
  return {
    index,
    key,
    label,
    month,
    year,
    academicYear: String(academicYearStart),
    academicYearLabel: `${academicYearStart}-${String((academicYearStart + 1) % 100).padStart(2, "0")}`,
  };
}

export function previousAcademicValue(
  values: unknown[],
  monthOptions: MonthOption[],
  activeMonth: MonthOption,
): number | null {
  const activePosition = monthOptions.findIndex((month) => month.key === activeMonth.key);
  for (let i = activePosition - 1; i >= 0; i--) {
    const value = values[monthOptions[i].index];
    if (value != null && Number.isFinite(Number(value))) return Number(value);
  }
  return null;
}

export function deltaClass(delta: number | null): string {
  if (delta == null) return "text-muted-foreground";
  if (delta > 0) return "text-success";
  if (delta < 0) return "text-destructive";
  return "text-muted-foreground";
}

export function deltaLabel(delta: number | null): string {
  if (delta == null) return "No previous data";
  if (delta > 0) return `▲ ${delta.toFixed(1)}`;
  if (delta < 0) return `▼ ${Math.abs(delta).toFixed(1)}`;
  return "No change";
}

export function zoneForGroup(aap: number | null): string {
  if (aap == null) return "No data";
  if (aap >= 7) return "Green";
  if (aap >= 5) return "Yellow";
  return "Red";
}
