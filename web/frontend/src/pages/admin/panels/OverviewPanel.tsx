import { useMemo, useState, type ReactNode } from "react";
import {
  AlertCircle,
  AlertTriangle,
  BarChart3,
  BookOpen,
  CalendarDays,
  GraduationCap,
  School,
  Trophy,
  Users,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { OverviewGrade, asNumber, asString, findPreferredMathSubject } from "../shared";

type ZoneKey = "red" | "yellow" | "green";

type MonthlyGroupRow = {
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

type ExamPoint = Record<string, string | number | null>;
type MonthOption = { index: number; key: string; label: string };

const lineColors = ["#3b82f6", "#f59e0b", "#10b981", "#8b5cf6", "#f43f5e", "#06b6d4", "#84cc16"];

function metricAverage(values: Array<number | null>): number | null {
  const nums = values.filter((v): v is number => v != null);
  if (!nums.length) return null;
  return Math.round((nums.reduce((a, b) => a + b, 0) / nums.length) * 10) / 10;
}

function previousValue(values: unknown[], index: number): number | null {
  for (let i = index - 1; i >= 0; i--) {
    const v = values[i];
    if (v != null && Number.isFinite(Number(v))) return Number(v);
  }
  return null;
}

function deltaClass(delta: number | null): string {
  if (delta == null) return "text-muted-foreground";
  if (delta > 0) return "text-success";
  if (delta < 0) return "text-destructive";
  return "text-muted-foreground";
}

function deltaLabel(delta: number | null): string {
  if (delta == null) return "No previous data";
  if (delta > 0) return `▲ ${delta.toFixed(1)}`;
  if (delta < 0) return `▼ ${Math.abs(delta).toFixed(1)}`;
  return "No change";
}

function zoneForGroup(aap: number | null): string {
  if (aap == null) return "No data";
  if (aap >= 7) return "Green";
  if (aap >= 5) return "Yellow";
  return "Red";
}

function Indicator({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  const toneClass =
    tone === "good"
      ? "text-success"
      : tone === "warn"
        ? "text-warning"
        : tone === "bad"
          ? "text-destructive"
          : "text-foreground";
  return (
    <div className="min-w-0 rounded-lg border border-foreground/8 bg-background px-3 py-2">
      <p className="truncate text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 truncate text-xl font-bold leading-none ${toneClass}`}>{value}</p>
      {detail ? <p className="mt-1 truncate text-[11px] font-semibold text-muted-foreground">{detail}</p> : null}
    </div>
  );
}

function ZonesDrawer({
  zoneRows,
  activeTab,
  onTabChange,
  onClose,
}: {
  zoneRows: Record<ZoneKey, Array<Record<string, unknown>>>;
  activeTab: ZoneKey;
  onTabChange: (tab: ZoneKey) => void;
  onClose: () => void;
}) {
  const tabs: { key: ZoneKey; label: string; icon: ReactNode; color: string }[] = [
    { key: "green",  label: "Green",  icon: <Trophy className="h-3.5 w-3.5" />,         color: "text-success" },
    { key: "yellow", label: "Yellow", icon: <AlertTriangle className="h-3.5 w-3.5" />,  color: "text-warning" },
    { key: "red",    label: "Red",    icon: <AlertCircle className="h-3.5 w-3.5" />,    color: "text-destructive" },
  ];
  const rows = zoneRows[activeTab];
  const activeColor = tabs.find((t) => t.key === activeTab)?.color ?? "";

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-96 flex-col border-l border-foreground/10 bg-surface shadow-xl">
      <div className="flex shrink-0 items-center justify-between border-b border-foreground/8 px-5 py-3.5">
        <p className="text-sm font-bold">Performance Zones</p>
        <button type="button" onClick={onClose} className="rounded-md p-1 hover:bg-foreground/5">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex shrink-0 gap-0.5 border-b border-foreground/8 px-4 pt-2">
        {tabs.map(({ key, label, icon, color }) => {
          const count = zoneRows[key].length;
          const isActive = key === activeTab;
          return (
            <button
              key={key}
              type="button"
              onClick={() => onTabChange(key)}
              className={`flex items-center gap-1.5 rounded-t-md px-3 py-2 text-xs font-semibold transition-colors ${
                isActive
                  ? `border border-b-0 border-foreground/10 bg-background ${color}`
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span>{icon}</span>
              {label}
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${isActive ? "bg-foreground/8" : "bg-foreground/5"}`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>
      <div className="flex-1 overflow-y-auto">
        {rows.length ? (
          <table className="w-full text-left">
            <thead className="sticky top-0 bg-surface">
              <tr className="border-b border-foreground/8">
                {["Group", "Subject", "AAP", "AR"].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-foreground/5 hover:bg-foreground/2">
                  <td className="px-4 py-2.5 text-xs font-semibold">{asString(row.group_name)}</td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{asString(row.subject_name)}</td>
                  <td className={`px-4 py-2.5 text-xs font-bold ${activeColor}`}>
                    {row.aap == null ? "-" : asNumber(row.aap).toFixed(1)}
                  </td>
                  <td className="px-4 py-2.5 text-xs">
                    {row.ar == null ? "-" : `${asNumber(row.ar).toFixed(1)}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="px-4 py-6 text-sm text-muted-foreground">No groups in this zone.</p>
        )}
      </div>
    </div>
  );
}

export default function OverviewPanel({ state }: { state: any }) {
  const {
    quickStats,
    selectedOverviewSchool,
    setSelectedOverviewSchool,
    setSelectedSehriyoGrade,
    subjectInfo,
    setSelectedSubjectName,
    availableSubjectSchools,
    selectedSubjectName,
    schoolSubjectRows,
    isSehriyoOverview,
    availableOverviewGrades,
    activeOverviewGrade,
    selectedSubjectRow,
    selectedGroupRows,
    filteredExamSeries,
    filteredMonthlyArSeries,
    monthlyChartData,
    monthlySeries,
    props,
  } = state;

  const [selectedMonth, setSelectedMonth] = useState("");
  const [zonesOpen, setZonesOpen] = useState(false);
  const [zonesTab, setZonesTab] = useState<ZoneKey>("green");

  const monthOptions = useMemo<MonthOption[]>(
    () =>
      monthlyChartData.map((row: Record<string, unknown>, index: number) => ({
        index,
        key: asString(row.month),
        label: asString(row.monthLabel) || asString(row.month),
      })),
    [monthlyChartData],
  );

  const activeMonth =
    monthOptions.find((m: MonthOption) => m.key === selectedMonth) ||
    monthOptions[monthOptions.length - 1];

  const monthlyRows = useMemo(() => {
    if (!activeMonth) return [];
    return monthlySeries
      .map((seriesRow: Record<string, unknown>) => {
        const label = asString(seriesRow.label);
        const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
        const currentRaw = values[activeMonth.index];
        const current = currentRaw == null || !Number.isFinite(Number(currentRaw)) ? null : Number(currentRaw);
        const previous = previousValue(values, activeMonth.index);
        const groupRow = selectedGroupRows.find((row: Record<string, unknown>) => asString(row.label) === label);
        const delta = current != null && previous != null ? current - previous : null;
        const arSeriesRow = (filteredMonthlyArSeries as Array<Record<string, unknown>>).find(
          (row) => asString(row.label) === label,
        );
        const arValues = Array.isArray(arSeriesRow?.values) ? (arSeriesRow.values as unknown[]) : [];
        const arRaw = arValues[activeMonth.index];
        const monthly_ar = arRaw == null || !Number.isFinite(Number(arRaw)) ? null : Number(arRaw);
        const overall_ar = groupRow?.avg_ar == null ? null : asNumber(groupRow.avg_ar);
        return {
          label,
          students: asNumber(groupRow?.students_count),
          current,
          previous,
          delta,
          ar: overall_ar,
          monthly_ar,
          display_ar: monthly_ar ?? overall_ar,
          zone: zoneForGroup(current),
        };
      })
      .sort((left: MonthlyGroupRow, right: MonthlyGroupRow) => {
        return (left.current ?? -1) - (right.current ?? -1);
      });
  }, [activeMonth, monthlySeries, selectedGroupRows, filteredMonthlyArSeries]);

  const monthAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.current));
  const previousAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.previous));
  const monthDelta = monthAverage != null && previousAverage != null ? monthAverage - previousAverage : null;
  const groupsWithData = monthlyRows.filter((row: MonthlyGroupRow) => row.current != null).length;
  const weakestRows = monthlyRows.filter((row: MonthlyGroupRow) => row.current != null).slice(0, 3);
  const monthArAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.monthly_ar));
  const prevMonthArAverage = useMemo(() => {
    if (!activeMonth) return null;
    const prevValues = (filteredMonthlyArSeries as Array<Record<string, unknown>>).map((seriesRow) => {
      const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      return previousValue(values, activeMonth.index);
    });
    return metricAverage(prevValues);
  }, [activeMonth, filteredMonthlyArSeries]);
  const monthArDelta = monthArAverage != null && prevMonthArAverage != null ? monthArAverage - prevMonthArAverage : null;

  const zoneRows = {
    red:    Array.isArray(props.adminGroupZones?.red)    ? props.adminGroupZones.red    : [],
    yellow: Array.isArray(props.adminGroupZones?.yellow) ? props.adminGroupZones.yellow : [],
    green:  Array.isArray(props.adminGroupZones?.green)  ? props.adminGroupZones.green  : [],
  } as Record<ZoneKey, Array<Record<string, unknown>>>;

  const examLabels = Array.isArray(selectedSubjectRow?.exam_labels)
    ? (selectedSubjectRow.exam_labels as unknown[]).map((label) => asString(label)).filter(Boolean)
    : [];
  const examSeries = filteredExamSeries as Array<Record<string, unknown>>;
  const EXAM_SHORT: Record<string, string> = {
    "Half-term Test 1": "HT 1",
    "End-of-term Test 1": "ET 1",
    "Half-term Test 2": "HT 2",
    "End-of-term Test 2": "ET 2",
    "Half-term Test 3": "HT 3",
  };
  const examChartData = examLabels.map((examLabel, index) => {
    const row: ExamPoint = { examLabel, shortName: EXAM_SHORT[examLabel] ?? examLabel };
    for (const seriesRow of examSeries) {
      const label = asString(seriesRow.label);
      const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      const value = values[index];
      row[label] = value == null || !Number.isFinite(Number(value)) ? null : Number(value);
    }
    return row;
  });

  return (
    <div className="space-y-3">
      {zonesOpen && (
        <ZonesDrawer
          zoneRows={zoneRows}
          activeTab={zonesTab}
          onTabChange={setZonesTab}
          onClose={() => setZonesOpen(false)}
        />
      )}

      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-foreground/8 bg-surface px-3 py-2 shadow-card">
        {[
          { label: "Students", value: asNumber(quickStats.total_students), icon: <Users className="h-3.5 w-3.5" /> },
          { label: "Schools", value: asNumber(quickStats.total_schools), icon: <School className="h-3.5 w-3.5" /> },
          { label: "Teachers", value: asNumber(quickStats.total_teachers), icon: <GraduationCap className="h-3.5 w-3.5" /> },
          { label: "Subjects", value: asNumber(quickStats.total_subjects), icon: <BookOpen className="h-3.5 w-3.5" /> },
        ].map((item) => (
          <span key={item.label} className="inline-flex items-center gap-1.5 rounded-md bg-background px-2.5 py-1.5 text-xs font-semibold text-muted-foreground">
            {item.icon}
            <span className="font-bold text-foreground">{item.value}</span>
            {item.label}
          </span>
        ))}
        <span className="hidden h-5 w-px bg-foreground/10 sm:inline-block" />
        {([
          { key: "red" as ZoneKey, label: "Red", icon: <AlertCircle className="h-3.5 w-3.5" />, color: "text-destructive bg-destructive/10" },
          { key: "yellow" as ZoneKey, label: "Yellow", icon: <AlertTriangle className="h-3.5 w-3.5" />, color: "text-warning bg-warning/10" },
          { key: "green" as ZoneKey, label: "Green", icon: <Trophy className="h-3.5 w-3.5" />, color: "text-success bg-success/10" },
        ]).map(({ key, label, icon, color }) => (
          <button
            key={key}
            type="button"
            onClick={() => { setZonesTab(key); setZonesOpen(true); }}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-bold transition-opacity hover:opacity-75 ${color}`}
          >
            {icon}
            {zoneRows[key].length}
            <span className="font-semibold opacity-75">{label}</span>
          </button>
        ))}
      </div>

      <ChartCard
        title="Subject Performance"
        icon={<BarChart3 className="h-4 w-4 text-info" />}
        headerActions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedOverviewSchool}
              onChange={(event) => {
                const nextSchool = event.target.value;
                setSelectedOverviewSchool(nextSchool);
                setSelectedSehriyoGrade("");
                setSelectedMonth("");
                const nextRows = subjectInfo.filter(
                  (row: Record<string, unknown>) => asString(row.school_key).toLowerCase() === nextSchool,
                );
                setSelectedSubjectName(
                  findPreferredMathSubject(nextRows.map((row: Record<string, unknown>) => asString(row.subject_name))),
                );
              }}
              className="rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-xs font-medium outline-none"
            >
              {availableSubjectSchools.map((option: { code: string; label: string }) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={selectedSubjectName}
              onChange={(event) => {
                setSelectedSubjectName(event.target.value);
                setSelectedSehriyoGrade("");
                setSelectedMonth("");
              }}
              className="rounded-lg border-2 border-foreground/10 bg-surface px-3 py-2 text-xs font-medium outline-none"
            >
              {schoolSubjectRows.map((row: Record<string, unknown>) => (
                <option key={asString(row.subject_name)} value={asString(row.subject_name)}>
                  {asString(row.subject_name)}
                </option>
              ))}
            </select>
            {isSehriyoOverview && availableOverviewGrades.length ? (
              <div className="flex items-center rounded-lg border border-foreground/10 bg-muted p-0.5">
                {(["7", "8"] as OverviewGrade[]).map((grade) => {
                  const enabled = availableOverviewGrades.includes(grade);
                  return (
                    <button
                      key={grade}
                      type="button"
                      disabled={!enabled}
                      onClick={() => { if (enabled) setSelectedSehriyoGrade(grade); }}
                      className={`rounded-md px-3 py-1.5 text-[11px] font-bold transition-colors ${
                        enabled && activeOverviewGrade === grade
                          ? "bg-surface text-foreground shadow-sm"
                          : "text-muted-foreground"
                      } ${!enabled ? "cursor-not-allowed opacity-40" : ""}`}
                    >
                      {grade} Graders
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
        }
      >
        {selectedSubjectRow ? (
          <div className="space-y-3">
            <div className="grid gap-2 md:grid-cols-[minmax(10rem,0.85fr)_repeat(4,minmax(0,1fr))]">
              <div className="rounded-lg border border-foreground/8 bg-background px-3 py-2">
                <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                  <CalendarDays className="h-3.5 w-3.5" />
                  Month
                </p>
                <select
                  value={activeMonth?.key || ""}
                  onChange={(event) => setSelectedMonth(event.target.value)}
                  className="mt-1.5 h-8 w-full rounded-md border border-foreground/10 bg-surface px-2 text-xs font-bold outline-none"
                >
                  {monthOptions.map((month: MonthOption) => (
                    <option key={month.key || month.index} value={month.key}>
                      {month.label}
                    </option>
                  ))}
                </select>
              </div>
              <Indicator
                label="AAP"
                value={monthAverage == null ? "-" : monthAverage.toFixed(1)}
                tone={monthAverage == null ? "neutral" : monthAverage >= 7 ? "good" : monthAverage >= 5 ? "warn" : "bad"}
                detail={
                  monthAverage == null
                    ? "No data"
                    : monthDelta == null
                      ? "No previous data"
                      : `${deltaLabel(monthDelta)} from previous`
                }
              />
              <Indicator
                label="Attendance"
                value={monthArAverage == null ? "-" : `${monthArAverage.toFixed(1)}%`}
                tone={monthArAverage == null ? "neutral" : monthArAverage >= 85 ? "good" : monthArAverage >= 70 ? "warn" : "bad"}
                detail={
                  monthArAverage == null
                    ? "No attendance data"
                    : monthArDelta == null
                      ? "No previous data"
                      : `${deltaLabel(monthArDelta)} from previous`
                }
              />
              <Indicator
                label="Coverage"
                value={`${groupsWithData}/${monthlyRows.length}`}
                detail="groups with data"
              />
              <Indicator
                label="Needs Attention"
                value={zoneRows.red.length + zoneRows.yellow.length}
                tone={zoneRows.red.length ? "bad" : zoneRows.yellow.length ? "warn" : "good"}
                detail={weakestRows.length ? `${weakestRows[0].label} lowest` : "No flagged groups"}
              />
            </div>

            <div className="grid gap-3 xl:grid-cols-[minmax(0,1.45fr)_minmax(19rem,0.55fr)]">
              <div className="h-72 lg:h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={monthlyRows} margin={{ top: 20, right: 40, left: -6, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="hsl(var(--foreground) / 0.06)" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="aap" domain={[0, 9]} tick={{ fontSize: 10 }} width={30} tickMargin={4} axisLine={false} tickLine={false} />
                    <YAxis yAxisId="ar" orientation="right" domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} width={40} tickMargin={4} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--foreground)/0.08)", borderRadius: 8, fontSize: 12 }}
                      formatter={(value, name, tooltipProps) => {
                        const numericValue = asNumber(value);
                        if (name === "AR %") return [`${numericValue.toFixed(1)}%`, name];
                        const delta = (tooltipProps.payload as MonthlyGroupRow)?.delta;
                        const deltaStr = delta == null ? "" : delta >= 0 ? ` ▲${delta.toFixed(1)}` : ` ▼${Math.abs(delta).toFixed(1)}`;
                        return [`${numericValue.toFixed(1)}${deltaStr}`, name];
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar yAxisId="aap" dataKey="current" name="AAP" fill="hsl(var(--info))" radius={[4, 4, 0, 0]}>
                      <LabelList
                        dataKey="delta"
                        position="top"
                        fontSize={9}
                        fill="#888"
                        formatter={(delta: number | null) => {
                          if (delta == null) return "";
                          return delta >= 0 ? `▲${delta.toFixed(1)}` : `▼${Math.abs(delta).toFixed(1)}`;
                        }}
                      />
                    </Bar>
                    <Bar yAxisId="ar" dataKey="display_ar" name="AR %" fill="hsl(var(--success))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="rounded-lg border border-foreground/8 bg-background p-3">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-bold">Attention</p>
                    <p className="text-xs text-muted-foreground">Lowest groups this month.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => { setZonesTab(zoneRows.red.length ? "red" : "yellow"); setZonesOpen(true); }}
                    className="rounded-md bg-muted px-2.5 py-1.5 text-[11px] font-bold text-muted-foreground hover:bg-foreground/10"
                  >
                    View zones
                  </button>
                </div>
                <div className="mb-3 grid grid-cols-3 gap-2">
                  {([
                    { key: "red" as ZoneKey, label: "Red", color: "text-destructive bg-destructive/10" },
                    { key: "yellow" as ZoneKey, label: "Yellow", color: "text-warning bg-warning/10" },
                    { key: "green" as ZoneKey, label: "Green", color: "text-success bg-success/10" },
                  ]).map(({ key, label, color }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => { setZonesTab(key); setZonesOpen(true); }}
                      className={`rounded-md px-2 py-2 text-left ${color}`}
                    >
                      <span className="block text-lg font-bold leading-none">{zoneRows[key].length}</span>
                      <span className="text-[10px] font-bold uppercase tracking-wide opacity-75">{label}</span>
                    </button>
                  ))}
                </div>
                <div className="space-y-2">
                  {weakestRows.length ? (
                    weakestRows.map((row: MonthlyGroupRow) => (
                      <div key={row.label} className="rounded-md border border-foreground/8 bg-surface px-3 py-2">
                        <div className="flex items-center justify-between gap-3">
                          <p className="truncate text-sm font-bold">{row.label}</p>
                          <span className={`shrink-0 text-xs font-bold ${deltaClass(row.delta)}`}>
                            {deltaLabel(row.delta)}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                          <span>AAP <strong className="text-foreground">{row.current == null ? "-" : row.current.toFixed(1)}</strong></span>
                          <span>AR <strong className="text-foreground">{(row.monthly_ar ?? row.ar) == null ? "-" : `${(row.monthly_ar ?? row.ar)!.toFixed(1)}%`}</strong></span>
                          <span>{row.zone}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="rounded-md border border-dashed border-foreground/15 px-3 py-4 text-sm text-muted-foreground">
                      No monthly performance data available.
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="grid gap-3 xl:grid-cols-2">
              <div className="rounded-lg border border-foreground/8 bg-background p-3">
                <div className="mb-2">
                  <p className="text-sm font-bold">Exam Performance</p>
                  <p className="text-xs text-muted-foreground">Average score by group and exam.</p>
                </div>
                {examChartData.length && examSeries.length ? (
                  <div className="h-52">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={examChartData} margin={{ top: 8, right: 8, left: -6, bottom: 0 }}>
                        <CartesianGrid vertical={false} stroke="hsl(var(--foreground) / 0.06)" />
                        <XAxis dataKey="shortName" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                        <YAxis domain={[0, 9]} tick={{ fontSize: 10 }} width={30} tickMargin={4} axisLine={false} tickLine={false} />
                        <Tooltip
                          contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--foreground)/0.08)", borderRadius: 8, fontSize: 12 }}
                          formatter={(value, name) => [Number(value).toFixed(1), asString(name)]}
                          labelFormatter={(label) => {
                            const found = examChartData.find((d) => d.shortName === label);
                            return found ? asString(found.examLabel) : asString(label);
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        {examSeries.map((seriesRow: Record<string, unknown>, index: number) => {
                          const label = asString(seriesRow.label);
                          return (
                            <Line
                              key={label || `exam-series-${index}`}
                              type="monotone"
                              dataKey={label}
                              stroke={lineColors[index % lineColors.length]}
                              strokeWidth={2.5}
                              dot={false}
                              activeDot={{ r: 4, strokeWidth: 0 }}
                              connectNulls
                            />
                          );
                        })}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="flex h-56 items-center justify-center rounded-lg border border-dashed border-foreground/15 text-sm text-muted-foreground">
                    No exam data for this subject yet.
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-foreground/8 bg-background p-3">
                <div className="mb-2">
                  <p className="text-sm font-bold">Long-Term Trend</p>
                  <p className="text-xs text-muted-foreground">Supporting context for monthly AAP.</p>
                </div>
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={monthlyChartData} margin={{ top: 8, right: 8, left: -6, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="hsl(var(--foreground) / 0.06)" />
                      <XAxis dataKey="monthLabel" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 9]} tick={{ fontSize: 10 }} width={30} tickMargin={4} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--foreground)/0.08)", borderRadius: 8, fontSize: 12 }}
                        labelFormatter={(value) => asString(value)}
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      {monthlySeries.map((seriesRow: Record<string, unknown>, index: number) => {
                        const seriesLabel = asString(seriesRow.label);
                        return (
                          <Line
                            key={seriesLabel || `series-${index}`}
                            type="monotone"
                            dataKey={seriesLabel}
                            connectNulls
                            stroke={lineColors[index % lineColors.length]}
                            strokeWidth={2.5}
                            dot={false}
                            activeDot={{ r: 4, strokeWidth: 0 }}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No subject statistics available.</p>
        )}
      </ChartCard>
    </div>
  );
}
