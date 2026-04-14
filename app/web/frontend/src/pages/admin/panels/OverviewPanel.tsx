import {
  AlertCircle,
  AlertTriangle,
  BarChart3,
  BookOpen,
  GraduationCap,
  School,
  Trophy,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/ChartCard";
import { StatCard } from "@/components/StatCard";
import { OverviewGrade, asNumber, asString } from "../shared";

export default function OverviewPanel({ state }: { state: any }) {
  const {
    quickStats,
    schoolInfo,
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
    monthlyChartData,
    monthlySeries,
    props,
  } = state;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          title="Students"
          value={String(asNumber(quickStats.total_students))}
          icon={<Users className="h-3.5 w-3.5" />}
        />
        <StatCard
          title="Schools"
          value={String(asNumber(quickStats.total_schools))}
          icon={<School className="h-3.5 w-3.5" />}
        />
        <StatCard
          title="Teachers"
          value={String(asNumber(quickStats.total_teachers))}
          icon={<GraduationCap className="h-3.5 w-3.5" />}
        />
        <StatCard
          title="Subjects"
          value={String(asNumber(quickStats.total_subjects))}
          icon={<BookOpen className="h-3.5 w-3.5" />}
        />
      </div>

      <ChartCard title="School Info" icon={<School className="h-4 w-4 text-info" />}>
        <ul className="space-y-3">
          {schoolInfo.length ? (
            schoolInfo.map((row: Record<string, unknown>) => (
              <li key={asString(row.school_name)} className="rounded-lg border border-foreground/5 p-3">
                <p className="text-sm font-bold">{asString(row.school_name)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {asNumber(row.total_students)} students · {asNumber(row.total_subjects)} subjects ·{" "}
                  {asNumber(row.total_groups)} groups · AAP{" "}
                  {row.avg_aap == null ? "-" : asNumber(row.avg_aap).toFixed(1)} · AR{" "}
                  {row.avg_ar == null ? "-" : asNumber(row.avg_ar).toFixed(1)}%
                </p>
              </li>
            ))
          ) : (
            <li className="text-sm text-muted-foreground">No school statistics available.</li>
          )}
        </ul>
      </ChartCard>

      <ChartCard
        title="Subject Overview"
        icon={<BarChart3 className="h-4 w-4 text-info" />}
        headerActions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedOverviewSchool}
              onChange={(event) => {
                const nextSchool = event.target.value;
                setSelectedOverviewSchool(nextSchool);
                setSelectedSehriyoGrade("");
                const nextRows = subjectInfo.filter(
                  (row: Record<string, unknown>) => asString(row.school_key).toLowerCase() === nextSchool
                );
                setSelectedSubjectName(asString(nextRows[0]?.subject_name));
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
                      onClick={() => {
                        if (enabled) {
                          setSelectedSehriyoGrade(grade);
                        }
                      }}
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
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={selectedGroupRows} margin={{ top: 8, right: 8, left: -6, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--foreground) / 0.06)" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis yAxisId="aap" domain={[0, 9]} tick={{ fontSize: 10 }} width={30} tickMargin={4} />
                    <YAxis
                      yAxisId="ar"
                      orientation="right"
                      domain={[0, 100]}
                      tick={{ fontSize: 10 }}
                      tickFormatter={(value) => `${value}%`}
                      width={40}
                      tickMargin={4}
                    />
                    <Tooltip
                      formatter={(value, name) => {
                        const numericValue = asNumber(value);
                        if (name === "AR %") {
                          return [`${numericValue.toFixed(1)}%`, name];
                        }
                        return [numericValue.toFixed(1), name];
                      }}
                    />
                    <Legend />
                    <Bar yAxisId="aap" dataKey="avg_aap" name="AAP" fill="hsl(var(--info))" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="ar" dataKey="avg_ar" name="AR %" fill="hsl(var(--success))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[320px] text-left">
                  <thead>
                    <tr className="border-b border-foreground/5">
                      {["Group", "Students", "AAP", "AR"].map((heading) => (
                        <th key={heading} className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {selectedGroupRows.map((row: Record<string, unknown>) => (
                      <tr key={asString(row.label)} className="border-b border-foreground/5">
                        <td className="px-3 py-2.5 text-xs font-medium">{asString(row.label)}</td>
                        <td className="px-3 py-2.5 text-xs">{asNumber(row.students_count)}</td>
                        <td className="px-3 py-2.5 text-xs">{row.avg_aap == null ? "-" : asNumber(row.avg_aap).toFixed(1)}</td>
                        <td className="px-3 py-2.5 text-xs">{row.avg_ar == null ? "-" : `${asNumber(row.avg_ar).toFixed(1)}%`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={monthlyChartData} margin={{ top: 8, right: 8, left: -6, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--foreground) / 0.06)" />
                  <XAxis dataKey="monthLabel" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 9]} tick={{ fontSize: 10 }} width={30} tickMargin={4} />
                  <Tooltip labelFormatter={(value) => asString(value)} />
                  <Legend />
                  {monthlySeries.map((seriesRow: Record<string, unknown>, index: number) => {
                    const seriesLabel = asString(seriesRow.label);
                    return (
                      <Line
                        key={seriesLabel || `series-${index}`}
                        type="monotone"
                        dataKey={seriesLabel}
                        connectNulls
                        stroke={["#2563eb", "#f59e0b", "#1d4ed8", "#16a34a", "#7c3aed"][index % 5]}
                        strokeWidth={2}
                        dot={{ r: 3 }}
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No subject statistics available.</p>
        )}
      </ChartCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {[
          { label: "Green Zone", key: "green", icon: <Trophy className="h-4 w-4 text-success" /> },
          { label: "Yellow Zone", key: "yellow", icon: <AlertTriangle className="h-4 w-4 text-warning" /> },
          { label: "Red Zone", key: "red", icon: <AlertCircle className="h-4 w-4 text-destructive" /> },
        ].map((zone) => {
          const rows = Array.isArray(props.adminGroupZones?.[zone.key as keyof typeof props.adminGroupZones])
            ? (props.adminGroupZones?.[zone.key as keyof typeof props.adminGroupZones] as Array<Record<string, unknown>>)
            : [];
          return (
            <ChartCard key={zone.key} title={zone.label} icon={zone.icon}>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[240px] text-left">
                  <thead>
                    <tr className="border-b border-foreground/5">
                      {["Group", "Subject", "AAP", "AR"].map((heading) => (
                        <th key={heading} className="px-2 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.length ? (
                      rows.map((row, index) => (
                        <tr key={`${zone.key}-${index}`} className="border-b border-foreground/5">
                          <td className="px-2 py-2 text-xs font-medium">{asString(row.group_name)}</td>
                          <td className="px-2 py-2 text-xs">{asString(row.subject_name)}</td>
                          <td className="px-2 py-2 text-xs">{row.aap == null ? "-" : asNumber(row.aap).toFixed(1)}</td>
                          <td className="px-2 py-2 text-xs">{row.ar == null ? "-" : asNumber(row.ar).toFixed(1)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} className="px-2 py-4 text-sm text-muted-foreground">
                          No groups in this zone.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          );
        })}
      </div>
    </div>
  );
}
