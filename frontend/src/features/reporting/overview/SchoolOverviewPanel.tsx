import { useMemo, useState } from "react";
import { BarChart3 } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/shared/ui/ChartCard";
import { asNumber, asString, findPreferredMathSubject } from "@/shared/lib/workspace";
import { ZoneKey, MonthlyGroupRow, ExamClassOption, GraphMetric, GraphLineSeries, AcademicBarRow, MonthOption, lineColors, scoreAxisTicks, groupNameCollator, safeSvgId, averageGraphValue, normalizedAcademicAverage, compareAverageRowsDesc, compareAcademicRowsDesc, compareZoneGroupRowsDesc, compareLineLabelsDesc, metricAverage, academicMonthOption, previousAcademicValue, deltaLabel, zoneForGroup } from "./shared";
import { Indicator, ZonesDrawer } from "./cards";

export function SchoolOverviewPanel({ state }: { state: any }) {
  const {
    selectedOverviewSchool,
    setSelectedOverviewSchool,
    setSelectedSehriyoGrade,
    subjectInfo,
    setSelectedSubjectName,
    availableSubjectSchools,
    selectedSubjectName,
    schoolSubjectRows,
    selectedSubjectRow,
    availableOverviewGrades,
    activeOverviewGrade,
    selectedGroupRows,
    filteredExamSeries,
    filteredMonthlyArSeries,
    monthlyChartData,
    monthlySeries,
    props,
  } = state;

  const [selectedExam, setSelectedExam] = useState("");
  const [selectedTrendMonth, setSelectedTrendMonth] = useState("all");
  const [selectedAcademicYear, setSelectedAcademicYear] = useState("");
  const [graphMetric, setGraphMetric] = useState<GraphMetric>("academic");
  const [zonesOpen, setZonesOpen] = useState(false);
  const [zonesTab, setZonesTab] = useState<ZoneKey>("green");

  const monthOptions = useMemo<MonthOption[]>(
    () =>
      monthlyChartData
        .map((row: Record<string, unknown>, index: number) => academicMonthOption(row, index))
        .filter((option: MonthOption | null): option is MonthOption => option !== null),
    [monthlyChartData],
  );
  const academicYearOptions = useMemo(() => {
    const years = new Map<string, { key: string; label: string; startYear: number }>();
    for (const month of monthOptions) {
      const startYear = Number(month.academicYear);
      if (!years.has(month.academicYear)) {
        years.set(month.academicYear, {
          key: month.academicYear,
          label: month.academicYearLabel,
          startYear: Number.isFinite(startYear) ? startYear : -1,
        });
      }
    }
    return Array.from(years.values()).sort((left, right) => right.startYear - left.startYear);
  }, [monthOptions]);
  const selectedAcademicYearKey =
    selectedAcademicYear && academicYearOptions.some((year) => year.key === selectedAcademicYear)
      ? selectedAcademicYear
      : academicYearOptions[0]?.key || "";
  const selectedAcademicYearLabel =
    academicYearOptions.find((year) => year.key === selectedAcademicYearKey)?.label || "Academic Year";
  const visibleMonthOptions = selectedAcademicYearKey
    ? monthOptions.filter((month) => month.academicYear === selectedAcademicYearKey)
    : monthOptions;

  const activeMonth =
    (selectedTrendMonth !== "all"
      ? visibleMonthOptions.find((m: MonthOption) => m.key === selectedTrendMonth)
      : null) ||
    visibleMonthOptions[visibleMonthOptions.length - 1];

  const monthlyRows = useMemo(() => {
    if (!activeMonth) return [];
    return monthlySeries
      .map((seriesRow: Record<string, unknown>) => {
        const label = asString(seriesRow.label);
        const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
        const currentRaw = values[activeMonth.index];
        const current = currentRaw == null || !Number.isFinite(Number(currentRaw)) ? null : Number(currentRaw);
        const previous = previousAcademicValue(values, visibleMonthOptions, activeMonth);
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
  }, [activeMonth, monthlySeries, selectedGroupRows, filteredMonthlyArSeries, visibleMonthOptions]);

  const monthAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.current));
  const previousAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.previous));
  const monthDelta = monthAverage != null && previousAverage != null ? monthAverage - previousAverage : null;
  const weakestRows = monthlyRows.filter((row: MonthlyGroupRow) => row.current != null).slice(0, 3);
  const monthArAverage = metricAverage(monthlyRows.map((row: MonthlyGroupRow) => row.monthly_ar));
  const prevMonthArAverage = useMemo(() => {
    if (!activeMonth) return null;
    const prevValues = (filteredMonthlyArSeries as Array<Record<string, unknown>>).map((seriesRow) => {
      const values = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      return previousAcademicValue(values, visibleMonthOptions, activeMonth);
    });
    return metricAverage(prevValues);
  }, [activeMonth, filteredMonthlyArSeries, visibleMonthOptions]);
  const monthArDelta = monthArAverage != null && prevMonthArAverage != null ? monthArAverage - prevMonthArAverage : null;

  const zoneRows = {
    red: Array.isArray(props.adminGroupZones?.red)
      ? [...props.adminGroupZones.red].sort(compareZoneGroupRowsDesc)
      : [],
    yellow: Array.isArray(props.adminGroupZones?.yellow)
      ? [...props.adminGroupZones.yellow].sort(compareZoneGroupRowsDesc)
      : [],
    green: Array.isArray(props.adminGroupZones?.green)
      ? [...props.adminGroupZones.green].sort(compareZoneGroupRowsDesc)
      : [],
  } as Record<ZoneKey, Array<Record<string, unknown>>>;

  const examLabels = Array.isArray(selectedSubjectRow?.exam_labels)
    ? (selectedSubjectRow.exam_labels as unknown[]).map((label) => asString(label)).filter(Boolean)
    : [];
  const examSeries = filteredExamSeries as Array<Record<string, unknown>>;
  const EXAM_SHORT: Record<string, string> = {
    "Half-term Test 1": "HT1",
    "End-of-term Test 1": "ET1",
    "Half-term Test 2": "HT2",
    "End-of-term Test 2": "ET2",
    "Half-term Test 3": "HT3",
    "End-of-term Test 3": "ET3",
    "Half-term Test 4": "HT4",
  };
  const EXAM_ORDER = ["HT1", "ET1", "HT2", "ET2", "HT3", "ET3", "HT4"];
  const shortExamName = (label: string) => {
    const normalized = label.replace(/\s+/g, " ").trim();
    const compact = normalized.replace(/[\s_-]+/g, "").toUpperCase();
    const compactMatch = compact.match(/^(HFT|HT|ET)(\d+)$/);
    if (compactMatch) return `${compactMatch[1] === "ET" ? "ET" : "HT"}${compactMatch[2]}`;
    return EXAM_SHORT[normalized] ?? normalized;
  };
  const examAverageBuckets = new Map<string, { labels: string[]; values: number[]; classValues: Map<string, number[]> }>();
  examLabels.forEach((examLabel, index) => {
    const shortName = shortExamName(examLabel);
    const bucket = examAverageBuckets.get(shortName) ?? { labels: [], values: [], classValues: new Map<string, number[]>() };
    if (!bucket.labels.includes(examLabel)) bucket.labels.push(examLabel);
    examSeries.forEach((seriesRow) => {
      const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      const value = rawValues[index];
      if (value != null && Number.isFinite(Number(value))) {
        const numericValue = Number(value);
        const classLabel = asString(seriesRow.label);
        bucket.values.push(numericValue);
        if (classLabel) {
          const classValues = bucket.classValues.get(classLabel) ?? [];
          classValues.push(numericValue);
          bucket.classValues.set(classLabel, classValues);
        }
      }
    });
    examAverageBuckets.set(shortName, bucket);
  });
  const examClassOptions: ExamClassOption[] = Array.from(examAverageBuckets.entries()).map(([shortName, bucket]) => ({
    label: bucket.labels.join(" / "),
    shortName,
    average: metricAverage(bucket.values),
    rows: Array.from(bucket.classValues.entries())
      .map(([label, values]) => ({ label, average: metricAverage(values) }))
      .filter((row) => row.average != null)
      .sort(compareAverageRowsDesc),
  })).sort((a, b) => {
    const ai = EXAM_ORDER.indexOf(a.shortName || "");
    const bi = EXAM_ORDER.indexOf(b.shortName || "");
    if (ai === -1 && bi === -1) return (a.shortName || a.label).localeCompare(b.shortName || b.label);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
  const examView = selectedExam || "all";
  const activeExamOption =
    examView === "all"
      ? null
      : examClassOptions.find((option) => option.shortName === examView) ||
        examClassOptions[examClassOptions.length - 1];
  const examSelectValue = examView === "all" ? "all" : activeExamOption?.shortName || "all";
  const examClassLineData = examClassOptions.map((option) => {
    const row: Record<string, string | number | null> = {
      label: option.label,
      shortName: option.shortName,
    };
    option.rows.forEach((classRow) => {
      row[classRow.label] = classRow.average;
    });
    return row;
  });
  const examClassLineLabels = Array.from(
    new Set(examClassOptions.flatMap((option) => option.rows.map((row) => row.label))),
  );

  const activeTrendMonth =
    selectedTrendMonth === "all"
      ? null
      : visibleMonthOptions.find((month: MonthOption) => month.key === selectedTrendMonth) ||
        visibleMonthOptions[visibleMonthOptions.length - 1];
  const trendMonthRows: Array<{ label: string; average: number | null }> = activeTrendMonth
    ? monthlySeries
        .map((seriesRow: Record<string, unknown>) => {
          const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
          const value = rawValues[activeTrendMonth.index];
          return {
            label: asString(seriesRow.label),
            average: value == null || !Number.isFinite(Number(value)) ? null : Number(value),
          };
        })
        .filter(
          (row: { label: string; average: number | null }) =>
            row.label && row.average != null,
        )
        .sort(
          (
            a: { label: string; average: number | null },
            b: { label: string; average: number | null },
          ) => compareAverageRowsDesc(a, b),
        )
    : [];
  const monthlyClassLineLabels = (monthlySeries as Array<Record<string, unknown>>)
    .map((seriesRow) => asString(seriesRow.label))
    .filter(Boolean);
  const academicAapKey = (label: string) => `${label} AAP`;
  const academicClassLineData = visibleMonthOptions.map((monthOption: MonthOption) => {
    const point: Record<string, string | number | null> = {
      label: monthOption.label,
    };
    monthlySeries.forEach((seriesRow: Record<string, unknown>) => {
      const classLabel = asString(seriesRow.label);
      const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
      const value = rawValues[monthOption.index];
      if (classLabel) {
        point[academicAapKey(classLabel)] = value == null || !Number.isFinite(Number(value)) ? null : Number(value);
      }
    });
    return point;
  });
  const academicClassLineLabels = [...monthlyClassLineLabels].sort((left, right) => {
    const leftAverage = averageGraphValue(academicClassLineData.map((row) => row[academicAapKey(left)])) ?? Number.NEGATIVE_INFINITY;
    const rightAverage = averageGraphValue(academicClassLineData.map((row) => row[academicAapKey(right)])) ?? Number.NEGATIVE_INFINITY;
    if (leftAverage !== rightAverage) return rightAverage - leftAverage;
    return groupNameCollator.compare(right, left);
  });
  const academicClassLineSeries = academicClassLineLabels.map((label, index): GraphLineSeries => {
    const color = lineColors[index % lineColors.length];
    return {
      key: `aap-${label}`,
      dataKey: academicAapKey(label),
      name: label,
      yAxisId: "aap",
      color,
    };
  });
  const attendanceMonthRows: Array<{ label: string; average: number | null }> = activeTrendMonth
    ? (filteredMonthlyArSeries as Array<Record<string, unknown>>)
        .map((seriesRow) => {
          const rawValues = Array.isArray(seriesRow.values) ? (seriesRow.values as unknown[]) : [];
          const value = rawValues[activeTrendMonth.index];
          return {
            label: asString(seriesRow.label),
            average: value == null || !Number.isFinite(Number(value)) ? null : Number(value),
          };
        })
        .filter((row) => row.label && row.average != null)
        .sort(compareAverageRowsDesc)
    : [];
  const graphViewValue = graphMetric === "exam" ? examSelectValue : selectedTrendMonth;
  const examGraphLineLabels = [...examClassLineLabels].sort(compareLineLabelsDesc(examClassLineData));
  const examGraphLineSeries = examGraphLineLabels.map((label, index): GraphLineSeries => ({
    key: label,
    dataKey: label,
    name: label,
    yAxisId: "score",
    color: lineColors[index % lineColors.length],
  }));
  // Data points keep their natural x-axis order: months chronologically,
  // exams in HT1..HT4 order. Only the series/legend order is ranked.
  const graphLineData = graphMetric === "exam" ? examClassLineData : academicClassLineData;
  const graphLineSeries = graphMetric === "exam" ? examGraphLineSeries : academicClassLineSeries;
  const academicBarRows: AcademicBarRow[] = activeTrendMonth
    ? Array.from(new Set([...trendMonthRows.map((row) => row.label), ...attendanceMonthRows.map((row) => row.label)]))
        .map((label) => {
          const aapAverage = trendMonthRows.find((row) => row.label === label)?.average ?? null;
          const arAverage = attendanceMonthRows.find((row) => row.label === label)?.average ?? null;
          return {
            label,
            aapAverage,
            arAverage,
            sortAverage: normalizedAcademicAverage([aapAverage], [arAverage]),
          };
        })
        .filter((row) => row.aapAverage != null || row.arAverage != null)
        .sort(compareAcademicRowsDesc)
    : [];
  const graphBarRows =
    graphMetric === "exam"
      ? [...(activeExamOption?.rows || [])].sort(compareAverageRowsDesc)
      : academicBarRows;
  const graphIsAll = graphViewValue === "all";
  const graphLineMinWidth = Math.max(
    360,
    graphLineData.length * (graphMetric === "exam" ? 88 : 72),
  );
  const graphBarMinWidth = Math.max(360, graphBarRows.length * (graphMetric === "academic" ? 96 : 76));
  const graphDomain: [number, number] = [1, 9];
  const graphStroke = graphMetric === "exam" ? "#4a5d7e" : "#1e2d4a";
  const graphGridStroke = "#e2e8f0";
  const graphBorderClass = "border-border bg-surface shadow-card relative overflow-visible w-full";
  const graphTitle =
    graphMetric === "exam"
      ? graphIsAll
        ? "Class scores across all exams."
        : "Class averages for the selected exam."
      : graphIsAll
        ? "Class AAP across all months."
        : "Class AAP and AR for the selected month.";
  const formatAapValue = (value: unknown) => {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "-";
    return numericValue.toFixed(1);
  };
  const formatArValue = (value: unknown) => {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "-";
    return `${numericValue.toFixed(1)}%`;
  };
  const formatGraphValue = (value: unknown, name?: unknown) => {
    if (graphMetric === "academic" && asString(name).endsWith(" AR")) return formatArValue(value);
    return formatAapValue(value);
  };
  const openZonesDrawer = () => {
    setZonesTab(zoneRows.red.length ? "red" : zoneRows.yellow.length ? "yellow" : "green");
    setZonesOpen(true);
  };

  return (
    <div className="flex min-h-full flex-col gap-3">
      {zonesOpen && (
        <ZonesDrawer
          zoneRows={zoneRows}
          activeTab={zonesTab}
          onTabChange={setZonesTab}
          onClose={() => setZonesOpen(false)}
        />
      )}

      <ChartCard
        title="Subject Performance"
        icon={<BarChart3 className="h-4 w-4 text-info" />}
        className="flex min-h-0 flex-1 flex-col"
        bodyClassName="flex min-h-0 flex-1 flex-col"
      >
        {selectedSubjectRow ? (
          <div className="flex min-h-0 flex-1 flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-foreground/8 bg-background/60 px-2.5 py-2">
              <span className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Scope</span>
              <select
                value={selectedOverviewSchool}
                onChange={(event) => {
                  const nextSchool = event.target.value;
                  setSelectedOverviewSchool(nextSchool);
                  setSelectedSehriyoGrade("");
                  setSelectedExam("");
                  setSelectedAcademicYear("");
                  setSelectedTrendMonth("all");
                  const nextRows = subjectInfo.filter(
                    (row: Record<string, unknown>) => asString(row.school_key).toLowerCase() === nextSchool,
                  );
                  setSelectedSubjectName(
                    findPreferredMathSubject(nextRows.map((row: Record<string, unknown>) => asString(row.subject_name))),
                  );
                }}
                className="h-8 rounded-md border border-foreground/10 bg-surface px-2 text-xs font-semibold text-foreground outline-none focus:border-foreground/30"
                aria-label="School"
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
                  setSelectedExam("");
                  setSelectedAcademicYear("");
                  setSelectedTrendMonth("all");
                }}
                className="h-8 rounded-md border border-foreground/10 bg-surface px-2 text-xs font-semibold text-foreground outline-none focus:border-foreground/30"
                aria-label="Subject"
              >
                {schoolSubjectRows.map((row: Record<string, unknown>) => (
                  <option key={asString(row.subject_name)} value={asString(row.subject_name)}>
                    {asString(row.subject_name)}
                  </option>
                ))}
              </select>
              {Array.isArray(availableOverviewGrades) && availableOverviewGrades.length > 1 ? (
                <select
                  value={activeOverviewGrade || availableOverviewGrades[0]}
                  onChange={(event) => {
                    setSelectedSehriyoGrade(event.target.value as "7" | "8");
                    setSelectedExam("");
                    setSelectedAcademicYear("");
                    setSelectedTrendMonth("all");
                  }}
                  className="h-8 rounded-md border border-foreground/10 bg-surface px-2 text-xs font-semibold text-foreground outline-none focus:border-foreground/30"
                  aria-label="Class"
                >
                  {availableOverviewGrades.map((grade: "7" | "8") => (
                    <option key={grade} value={grade}>
                      Grade {grade}
                    </option>
                  ))}
                </select>
              ) : null}
              {graphMetric !== "exam" && academicYearOptions.length > 1 ? (
                <select
                  value={selectedAcademicYearKey}
                  onChange={(event) => {
                    setSelectedAcademicYear(event.target.value);
                    setSelectedTrendMonth("all");
                  }}
                  className="h-8 rounded-md border border-foreground/10 bg-surface px-2 text-xs font-semibold text-foreground outline-none focus:border-foreground/30"
                  aria-label="Academic year"
                >
                  {academicYearOptions.map((year) => (
                    <option key={year.key} value={year.key}>
                      {year.label}
                    </option>
                  ))}
                </select>
              ) : null}
            </div>

            <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
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
                label="AR"
                value={monthArAverage == null ? "-" : `${monthArAverage.toFixed(1)}%`}
                tone={monthArAverage == null ? "neutral" : monthArAverage >= 85 ? "good" : monthArAverage >= 70 ? "warn" : "bad"}
                detail={
                  monthArAverage == null
                    ? "No AR data"
                    : monthArDelta == null
                      ? "No previous data"
                      : `${deltaLabel(monthArDelta)} from previous`
                }
              />
              <Indicator
                label="Needs Attention"
                value={zoneRows.red.length + zoneRows.yellow.length}
                tone={zoneRows.red.length ? "bad" : zoneRows.yellow.length ? "warn" : "good"}
                detail={weakestRows.length ? `${weakestRows[0].label} lowest` : "No flagged groups"}
                onClick={openZonesDrawer}
              />
            </div>

            <div className={`flex min-h-[24rem] flex-1 flex-col rounded-xl border p-2 animate-in fade-in slide-in-from-bottom-1 duration-300 transition-[box-shadow,border-color] hover:border-foreground/15 hover:shadow-card-hover motion-reduce:animate-none motion-reduce:transition-none sm:p-3 ${graphBorderClass}`}>
              <div className="mb-2 flex shrink-0 flex-col gap-2 sm:mb-3 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
                <div>
                  <p className="text-sm font-bold">Performance Graph</p>
                  <p className="text-xs text-muted-foreground">{graphTitle}</p>
                </div>
                <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
                  <div className="inline-flex max-w-full items-center overflow-x-auto rounded-lg border border-foreground/10 bg-muted/50 p-0.5">
                    {([
                      { key: "academic", label: "Academic Indicators" },
                      { key: "exam", label: "Exam Performance" },
                    ] as const).map((option) => {
                      const active = graphMetric === option.key;
                      return (
                        <button
                          key={option.key}
                          type="button"
                          onClick={() => {
                            setGraphMetric(option.key);
                            if (option.key === "exam") {
                              setSelectedExam("");
                            } else {
                              setSelectedTrendMonth("all");
                            }
                          }}
                          className={`whitespace-nowrap rounded-md px-2 py-1 text-[11px] font-bold transition-[transform,background-color,color,box-shadow] hover:-translate-y-px motion-reduce:transition-none motion-reduce:hover:translate-y-0 sm:px-2.5 sm:text-xs ${
                            active ? "bg-surface text-foreground shadow-card" : "text-muted-foreground hover:bg-surface/70 hover:text-foreground"
                          }`}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                  {graphMetric === "exam" ? (
                    <select
                      value={examSelectValue}
                      onChange={(event) => setSelectedExam(event.target.value)}
                      className="h-8 min-w-0 flex-1 rounded-md border border-violet-200 bg-white/85 px-2 text-xs font-bold text-violet-700 outline-none sm:flex-none"
                    >
                      <option value="all">All</option>
                      {examClassOptions.map((option) => (
                        <option key={option.shortName} value={option.shortName}>
                          {option.shortName}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <select
                      value={
                        selectedTrendMonth === "all" ||
                        visibleMonthOptions.some((month) => month.key === selectedTrendMonth)
                          ? selectedTrendMonth
                          : "all"
                      }
                      onChange={(event) => setSelectedTrendMonth(event.target.value)}
                      className="h-8 min-w-0 flex-1 rounded-md border border-sky-200 bg-white/85 px-2 text-xs font-bold text-sky-700 outline-none sm:flex-none"
                      aria-label="Month"
                    >
                      <option value="all">All {selectedAcademicYearLabel}</option>
                      {visibleMonthOptions.map((month: MonthOption) => (
                        <option key={month.key || month.index} value={month.key}>
                          {month.label}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              {graphIsAll && graphLineSeries.length ? (
                <div className="-mx-1 min-h-0 flex-1 overflow-x-auto pb-1 sm:mx-0 sm:pb-0">
                  <div className="h-full min-h-[19rem] min-w-full" style={{ minWidth: graphLineMinWidth }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={graphLineData} margin={{ top: 6, right: 12, left: -6, bottom: 4 }}>
                        <CartesianGrid vertical={false} stroke={graphGridStroke} strokeDasharray="4 4" />
                        <XAxis dataKey={graphMetric === "exam" ? "shortName" : "label"} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={8} />
                        <YAxis yAxisId={graphMetric === "exam" ? "score" : "aap"} domain={graphDomain} ticks={scoreAxisTicks} tick={{ fontSize: 11 }} width={34} tickMargin={4} axisLine={false} tickLine={false} />
                        <Tooltip
                          allowEscapeViewBox={{ x: true, y: true }}
                          contentStyle={{ background: "rgba(255,255,255,0.96)", border: `1px solid ${graphGridStroke}`, borderRadius: 10, boxShadow: "0 10px 24px rgba(15, 23, 42, 0.10)", fontSize: 12 }}
                          formatter={(value, name) => [formatGraphValue(value, name), asString(name)]}
                          labelFormatter={(label) =>
                            graphMetric === "exam"
                              ? examClassOptions.find((point) => point.shortName === label)?.label || asString(label)
                              : asString(label)
                          }
                          wrapperStyle={{ zIndex: 40 }}
                        />
                        <Legend iconSize={10} height={20} wrapperStyle={{ fontSize: 12, fontWeight: 700, lineHeight: "16px", paddingTop: 0 }} />
                        <defs>
                          {graphLineSeries.map((series) => (
                            <linearGradient key={series.key} id={`overviewArea-${safeSvgId(series.key)}`} x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor={series.color} stopOpacity={0.28} />
                              <stop offset="100%" stopColor={series.color} stopOpacity={0.04} />
                            </linearGradient>
                          ))}
                        </defs>
                        {graphLineSeries.map((series, index) => (
                          <Area
                            key={series.key}
                            yAxisId={series.yAxisId}
                            type="monotone"
                            dataKey={series.dataKey}
                            name={series.name}
                            stroke={series.color}
                            fill={`url(#overviewArea-${safeSvgId(series.key)})`}
                            strokeWidth={2.75}
                            dot={{ r: 3.5, fill: series.color, strokeWidth: 0 }}
                            activeDot={{ r: 6, strokeWidth: 0 }}
                            connectNulls
                            isAnimationActive
                            animationBegin={index * 70}
                            animationDuration={700}
                            animationEasing="ease-out"
                          />
                        ))}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : graphBarRows.length ? (
                <div className="-mx-1 min-h-0 flex-1 overflow-x-auto pb-1 sm:mx-0 sm:pb-0">
                  <div className="h-full min-h-[19rem] min-w-full" style={{ minWidth: graphBarMinWidth }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={graphBarRows} margin={{ top: 16, right: graphMetric === "academic" ? 8 : 12, left: -6, bottom: 4 }}>
                        <CartesianGrid vertical={false} stroke={graphGridStroke} strokeDasharray="4 4" />
                        <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} axisLine={false} tickLine={false} minTickGap={6} />
                        <YAxis yAxisId={graphMetric === "exam" ? "score" : "aap"} domain={graphDomain} ticks={scoreAxisTicks} tick={{ fontSize: 11 }} width={34} tickMargin={4} axisLine={false} tickLine={false} />
                        {graphMetric === "academic" ? (
                          <YAxis
                            yAxisId="ar"
                            orientation="right"
                            domain={[0, 100]}
                            tick={{ fontSize: 11 }}
                            width={42}
                            tickMargin={4}
                            axisLine={false}
                            tickLine={false}
                            tickFormatter={(value) => `${value}%`}
                          />
                        ) : null}
                        <Tooltip
                          allowEscapeViewBox={{ x: true, y: true }}
                          contentStyle={{ background: "rgba(255,255,255,0.96)", border: `1px solid ${graphGridStroke}`, borderRadius: 10, boxShadow: "0 10px 24px rgba(15, 23, 42, 0.10)", fontSize: 12 }}
                          formatter={(value, name) => {
                            const label = asString(name);
                            return [label === "AR" ? formatArValue(value) : formatAapValue(value), label];
                          }}
                          labelFormatter={(label) => asString(label)}
                          wrapperStyle={{ zIndex: 40 }}
                        />
                        {graphMetric === "exam" ? (
                          <Bar yAxisId="score" dataKey="average" name="Exam score" fill={graphStroke} radius={[6, 6, 0, 0]} maxBarSize={48} isAnimationActive animationDuration={650} animationEasing="ease-out">
                            <LabelList dataKey="average" position="top" fontSize={12} fontWeight={700} fill={graphStroke} formatter={(value: number) => formatAapValue(value)} />
                          </Bar>
                        ) : (
                          <>
                            <Legend iconSize={10} height={20} wrapperStyle={{ fontSize: 12, fontWeight: 700, lineHeight: "16px", paddingTop: 0 }} />
                            <Bar yAxisId="aap" dataKey="aapAverage" name="AAP" fill="#1e2d4a" radius={[6, 6, 0, 0]} maxBarSize={38} isAnimationActive animationDuration={650} animationEasing="ease-out">
                              <LabelList dataKey="aapAverage" position="top" fontSize={12} fontWeight={700} fill="#1e2d4a" formatter={(value: number) => formatAapValue(value)} />
                            </Bar>
                            <Bar yAxisId="ar" dataKey="arAverage" name="AR" fill="#059669" radius={[6, 6, 0, 0]} maxBarSize={38} isAnimationActive animationBegin={90} animationDuration={650} animationEasing="ease-out">
                              <LabelList dataKey="arAverage" position="top" fontSize={12} fontWeight={700} fill="#059669" formatter={(value: number) => formatArValue(value)} />
                            </Bar>
                          </>
                        )}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-[19rem] flex-1 items-center justify-center rounded-lg border border-dashed border-foreground/15 bg-white/60 text-sm text-muted-foreground">
                  {graphMetric === "exam" ? "No exam performance data yet." : "No graph data for this selection yet."}
                </div>
              )}
            </div>

          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No subject statistics available.</p>
        )}
      </ChartCard>
    </div>
  );
}
