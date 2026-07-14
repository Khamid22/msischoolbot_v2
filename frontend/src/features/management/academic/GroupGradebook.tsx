import { Fragment, useState, useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, BarChart3, BookMarked, CalendarDays, ChevronLeft, ChevronRight, Layers, LockKeyhole, Minus, Plus, Settings, Table2, Users, X } from "lucide-react";
import { BarChart, Bar, Cell, Legend, LabelList, Line, LineChart, ReferenceLine, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { routes } from "@/shared/lib/routes";
import { motion } from "@/shared/lib/motion";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "@/features/managementTypes";
import { attCls, attLabel, formatScoreOutOfNine, scoreOutOfNine } from "../gradebookFormat";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";
import { GRADEBOOK_STUDENT_COL_WIDTH, GRADEBOOK_AAP_COL_WIDTH, GRADEBOOK_ATT_COL_WIDTH, GRADEBOOK_HW_COL_WIDTH, GRADEBOOK_LESSON_COL_WIDTH, EXAM_TABLE_STUDENT_COL_WIDTH, EXAM_TABLE_SCORE_COL_WIDTH, EXAM_TABLE_MIN_WIDTH, collectExamTypeOptions, averageScore, formatBarLabel, formatPercentLabel, StudentNameTick, Select, ExamTypeFilter, ExamViewSwitcher, MiniMetric, Lesson, Enrollment, GradebookData, AcademicTrendMonth, AcademicTrendsData, ActiveCell, AttValue } from "./shared";
import { ModernGroupTimetable } from "./ModernGroupTimetable";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { lessonDurationMinutesForSchoolCode } from "./scheduleMath";
import { queryClient } from "@/shared/api/queryClient";

type AcademicGradebookRoutes = Pick<
  typeof routes,
  | "adminAcademicGradebookApi"
  | "adminAcademicGradebookTrendsApi"
  | "adminAcademicGroupTimetableApi"
  | "adminAcademicAttendanceApi"
  | "adminAcademicHomeworkApi"
  | "adminAcademicExamApi"
  | "adminAcademicEnrollmentStatusApi"
  | "adminAcademicEnrollmentGroupApi"
  | "adminAcademicLessonApi"
  | "adminAcademicLessonCancelApi"
  | "adminAcademicLessonRecoverApi"
  | "adminAcademicGroupSchedule"
  | "adminAcademicGroupStudents"
  | "adminAcademicCalendarClosuresApi"
  | "adminAcademicCalendarClosurePreview"
  | "adminAcademicCalendarClosureCreate"
  | "adminAcademicCalendarClosureUnlock"
>;

type CompactTooltipItem = {
  value?: unknown;
  dataKey?: unknown;
  color?: string;
  payload?: {
    recordedAttendance?: number;
    scheduledLessons?: number;
  };
};

type ActiveExamCell = {
  enrollmentId: number;
  examLabel: string;
  attempt: string;
};

type GradebookView = "gradebook" | "ep" | "timetable";
type GradebookDisplayMode = "table" | "chart";
type AcademicChartMode = "trends" | "students";
type GradebookLoadOptions = { view?: GradebookView; cursor?: string; anchorDate?: string; month?: string; force?: boolean };
type GroupSetupForm = {
  teacherId: string;
  startDate: string;
  weekdays: number[];
  startTime: string;
  room: string;
  changeScope: string;
  effectiveDate: string;
  changeLaunchDate: boolean;
  allowRecordedChanges: boolean;
};

function gradebookSection(view: GradebookView) {
  return view === "ep" ? "exams" : view;
}

function currentMonthKey() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
}

function offsetMonthKey(month: string, offset: number) {
  const [year, monthNumber] = month.split("-").map(Number);
  if (!year || !monthNumber) return month;
  const value = new Date(Date.UTC(year, monthNumber - 1 + offset, 1));
  return `${value.getUTCFullYear()}-${String(value.getUTCMonth() + 1).padStart(2, "0")}`;
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = (event: MediaQueryListEvent) => setReduced(event.matches);
    setReduced(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  return reduced;
}

function CompactChartTooltip({
  active,
  label,
  payload,
  percentKeys = [],
}: {
  active?: boolean;
  label?: unknown;
  payload?: CompactTooltipItem[];
  percentKeys?: string[];
}) {
  const visiblePayload = (payload ?? []).filter((item) => item.value !== null && item.value !== undefined && item.value !== "");
  if (!active || visiblePayload.length === 0) return null;
  const coverage = visiblePayload[0]?.payload;
  return (
    <div className="rounded-xl border border-foreground/10 bg-popover px-3 py-2 text-popover-foreground shadow-card-hover">
      <p className="max-w-48 truncate text-xs font-bold">{asString(label)}</p>
      <div className="mt-1.5 flex flex-wrap gap-2">
        {visiblePayload.map((item, index) => {
          const key = asString(item.dataKey);
          const value = percentKeys.includes(key) ? formatPercentLabel(item.value) : formatBarLabel(item.value);
          if (!value) return null;
          return (
            <span key={`${key}-${index}`} className="inline-flex items-center gap-1.5 text-sm font-bold">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: item.color || "hsl(var(--primary))" }}
              />
              {value}
            </span>
          );
        })}
      </div>
      {typeof coverage?.recordedAttendance === "number" && typeof coverage?.scheduledLessons === "number" ? (
        <p className="mt-1.5 text-[10px] font-medium text-muted-foreground">
          Attendance recorded for {coverage.recordedAttendance} of {coverage.scheduledLessons} lessons
        </p>
      ) : null}
    </div>
  );
}

function formatTrendMonth(month: string, format: "long" | "short" = "long") {
  const [year, monthNumber] = month.split("-").map(Number);
  if (!year || !monthNumber) return month;
  return new Intl.DateTimeFormat("en", {
    month: format,
    year: format === "short" ? undefined : "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, monthNumber - 1, 1)));
}

function MetricDelta({
  current,
  previous,
  previousMonth,
  unit = "",
}: {
  current: number | null;
  previous: number | null;
  previousMonth: string;
  unit?: string;
}) {
  if (current === null) {
    return <span className="mt-1.5 block text-[10px] font-semibold text-muted-foreground">No data for selected month</span>;
  }
  if (previous === null) {
    return <span className="mt-1.5 block text-[10px] font-semibold text-muted-foreground">No data for {formatTrendMonth(previousMonth)}</span>;
  }
  const delta = Math.round((current - previous) * 10) / 10;
  const isPositive = delta > 0;
  const isNegative = delta < 0;
  const Icon = isPositive ? ArrowUpRight : isNegative ? ArrowDownRight : Minus;
  const tone = isPositive ? "text-emerald-700" : isNegative ? "text-red-700" : "text-muted-foreground";
  const value = delta > 0 ? `+${delta}` : String(delta);
  return (
    <span className={`mt-1.5 inline-flex items-center gap-1 text-[10px] font-bold ${tone}`}>
      <Icon className="h-3 w-3" aria-hidden="true" />
      <span>{value}{unit}</span>
      <span className="font-semibold text-muted-foreground">vs {formatTrendMonth(previousMonth)}</span>
    </span>
  );
}

type AcademicTrendTooltipItem = {
  dataKey?: unknown;
  color?: string;
  value?: unknown;
  payload?: AcademicTrendMonth;
};

function AcademicTrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: AcademicTrendTooltipItem[];
}) {
  const month = payload?.[0]?.payload;
  if (!active || !month) return null;
  const values = [
    { key: "avgAAP", label: "AAP", value: month.avgAAP, color: "#2563eb", suffix: " / 9" },
    { key: "avgPerformance", label: "Performance", value: month.avgPerformance, color: "#6d28d9", suffix: " / 9" },
    { key: "avgAR", label: "Attendance", value: month.avgAR, color: "#059669", suffix: "%" },
  ];
  return (
    <div className="min-w-52 rounded-xl border border-foreground/10 bg-popover px-3 py-2.5 text-popover-foreground shadow-card-hover">
      <p className="text-xs font-bold">{formatTrendMonth(month.month)}</p>
      {month.hasClosure ? (
        <p className="mt-1 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900">
          <LockKeyhole className="h-3 w-3" />{month.closureTitles?.join(", ") || "School holiday"}
        </p>
      ) : null}
      <div className="mt-2 space-y-1.5">
        {values.map((item) => (
          <div key={item.key} className="flex items-center justify-between gap-4 text-xs">
            <span className="inline-flex items-center gap-1.5 font-semibold text-muted-foreground">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} aria-hidden="true" />
              {item.label}
            </span>
            <span className="font-bold tabular-nums">{item.value === null ? "No data" : `${item.value}${item.suffix}`}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 border-t border-foreground/8 pt-2 text-[10px] leading-4 text-muted-foreground">
        <p>{month.lessonCount} lessons · {month.studentsWithData} students with data</p>
        <p>{month.homeworkRecordCount} homework · {month.attendanceRecordCount} attendance records</p>
      </div>
    </div>
  );
}

export function GroupGradebook({
  groupId,
  csrf,
  groups,
  teachers,
  schedules,
  academicRoutes = routes,
  onClose,
}: {
  groupId: number;
  csrf: string;
  groups: Array<Record<string, unknown>>;
  teachers: Array<Record<string, unknown>>;
  schedules: Array<Record<string, unknown>>;
  academicRoutes?: AcademicGradebookRoutes;
  onClose: () => void;
}) {
  const [data, setData] = useState<GradebookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState<ActiveCell | null>(null);
  const [hwInput, setHwInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [cellError, setCellError] = useState("");
  const [statusSavingId, setStatusSavingId] = useState<number | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<Enrollment | null>(null);
  useDismissibleLayer({
    enabled: Boolean(selectedStudent),
    onDismiss: () => setSelectedStudent(null),
    dismissOnOutsidePointer: false,
  });
  const [moveGroupId, setMoveGroupId] = useState("");
  const [moveSaving, setMoveSaving] = useState(false);
  const [activeExam, setActiveExam] = useState<ActiveExamCell | null>(null);
  const [examInput, setExamInput] = useState("");
  const [examSavingKey, setExamSavingKey] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<GradebookView>("gradebook");
  const [loadedView, setLoadedView] = useState<GradebookView>("gradebook");
  const [gradebookDisplay, setGradebookDisplay] = useState<GradebookDisplayMode>("table");
  const [academicChartMode, setAcademicChartMode] = useState<AcademicChartMode>("trends");
  const [lessonMonth, setLessonMonth] = useState(currentMonthKey);
  const [setupOpen, setSetupOpen] = useState(false);
  const [setupSaving, setSetupSaving] = useState(false);
  const [setupSuccess, setSetupSuccess] = useState("");
  const [setupError, setSetupError] = useState("");
  const [setupForm, setSetupForm] = useState<GroupSetupForm>({
    teacherId: "", startDate: "", weekdays: [0, 2], startTime: "14:00",
    room: "", changeScope: "", effectiveDate: "",
    changeLaunchDate: false, allowRecordedChanges: false,
  });
  const [scheduleRows, setScheduleRows] = useState(schedules);
  const [studentOpen, setStudentOpen] = useState(false);
  const [studentName, setStudentName] = useState("");
  const [studentSaving, setStudentSaving] = useState(false);
  const [studentError, setStudentError] = useState("");
  const [createdStudent, setCreatedStudent] = useState<Record<string, unknown> | null>(null);
  const [setupInitial, setSetupInitial] = useState("");
  const [hasSavedSetup, setHasSavedSetup] = useState(false);
  const { toast: setupToast, showToast: showSetupToast } = useFloatingToast();
  const [examType, setExamType] = useState("all");
  const [examDisplay, setExamDisplay] = useState<"chart" | "table">("chart");
  const prefersReducedMotion = usePrefersReducedMotion();
  const popRef = useRef<HTMLDivElement>(null);
  const gradebookCacheRef = useRef(new Map<string, GradebookData>());
  const loadRequestRef = useRef(0);
  const gradebookScrollRef = useRef<HTMLDivElement | null>(null);
  const gradebookScrollLeftRef = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    load(groupId, controller.signal, { view: "gradebook", month: currentMonthKey(), force: true });
    return () => controller.abort();
  }, [groupId]);

  useEffect(() => {
    if (!data?.schedule) return;
    setScheduleRows((current) => [
      ...current.filter((row) => asNumber(row.group_id) !== groupId),
      data.schedule as unknown as Record<string, unknown>,
    ]);
  }, [data?.schedule, groupId]);

  useEffect(() => {
    setActiveView("gradebook");
    setLoadedView("gradebook");
    setGradebookDisplay("table");
    setAcademicChartMode("trends");
    setData(null);
    setSelectedStudent(null);
    setExamType("all");
    setExamDisplay("chart");
    setActiveExam(null);
    setExamInput("");
    setLessonMonth(currentMonthKey());
    gradebookCacheRef.current.clear();
  }, [groupId]);

  useEffect(() => {
    if (!active) return;
    const handler = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) close();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [active]);

  async function fetchGradebookData(id: number, view: GradebookView, cursor = "", anchorDate = "", month = "", signal?: AbortSignal) {
    const section = gradebookSection(view);
    const url = academicRoutes.adminAcademicGradebookApi(id, {
      cursor: section === "gradebook" ? cursor : undefined,
      anchorDate: section === "gradebook" ? anchorDate : undefined,
      month: section === "gradebook" ? month : undefined,
      section,
    });
    return queryClient.fetchQuery({
      queryKey: ["academic", "gradebook", id, section, month, cursor, anchorDate],
      queryFn: async () => {
        const response = await fetch(url, { signal });
        const json = await response.json();
        if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Failed to load."));
        return apiData<GradebookData>(json);
      },
    });
  }

  async function load(id: number, signal?: AbortSignal, options: GradebookLoadOptions = {}) {
    const view = options.view ?? activeView;
    const cursor = options.cursor ?? "";
    const anchorDate = options.anchorDate ?? "";
    const month = options.month ?? (view === "gradebook" ? lessonMonth : "");
    const cacheKey = `${id}:${view}:${month || cursor || `anchor:${anchorDate || "today"}`}`;
    const cached = options.force ? undefined : gradebookCacheRef.current.get(cacheKey);
    if (cached) {
      loadRequestRef.current += 1;
      setLoading(false);
      setError("");
      setData(cached);
      setLoadedView(view);
      if (view === "gradebook" && cached.pageInfo?.selectedMonth) setLessonMonth(cached.pageInfo.selectedMonth);
      return;
    }
    const requestId = ++loadRequestRef.current;
    setLoading(true);
    setError("");
    setActive(null);
    try {
      const nextData = await fetchGradebookData(id, view, cursor, anchorDate, month, signal);
      if (requestId !== loadRequestRef.current) return;
      gradebookCacheRef.current.set(cacheKey, nextData);
      setData(nextData);
      setLoadedView(view);
      if (view === "gradebook") {
        const resolvedMonth = nextData.pageInfo?.selectedMonth || month;
        if (resolvedMonth) {
          gradebookCacheRef.current.set(`${id}:gradebook:${resolvedMonth}`, nextData);
          setLessonMonth(resolvedMonth);
        }
        for (const adjacentMonth of [nextData.pageInfo?.previousMonth, nextData.pageInfo?.nextMonth]) {
          if (!adjacentMonth) continue;
          const adjacentKey = `${id}:gradebook:${adjacentMonth}`;
          if (gradebookCacheRef.current.has(adjacentKey)) continue;
          void fetchGradebookData(id, "gradebook", "", "", adjacentMonth)
            .then((page) => gradebookCacheRef.current.set(adjacentKey, page))
            .catch(() => undefined);
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      if (requestId === loadRequestRef.current) setError(err instanceof Error ? err.message : "Network error.");
    } finally {
      if (requestId === loadRequestRef.current) setLoading(false);
    }
  }

  function changeView(view: GradebookView) {
    setActiveView(view);
    if (view === "timetable") {
      loadRequestRef.current += 1;
      setLoading(false);
      setError("");
      setLoadedView("timetable");
      return;
    }
    void load(groupId, undefined, { view, month: view === "gradebook" ? lessonMonth : "" });
  }

  function changeGradebookDisplay(mode: GradebookDisplayMode) {
    if (mode === gradebookDisplay) return;
    if (gradebookDisplay === "table") {
      gradebookScrollLeftRef.current = gradebookScrollRef.current?.scrollLeft || 0;
    }
    setActive(null);
    setGradebookDisplay(mode);
    if (mode === "table") {
      requestAnimationFrame(() => {
        if (gradebookScrollRef.current) {
          gradebookScrollRef.current.scrollLeft = gradebookScrollLeftRef.current;
        }
      });
    }
  }

  function openLessonMonth(month: string | null | undefined) {
    if (!month || loading) return;
    gradebookScrollLeftRef.current = 0;
    if (gradebookScrollRef.current) gradebookScrollRef.current.scrollLeft = 0;
    setLessonMonth(month);
    void load(groupId, undefined, { view: "gradebook", month });
  }

  function jumpToCurrentMonth() {
    openLessonMonth(currentMonthKey());
  }

  async function refreshCurrentView() {
    loadRequestRef.current += 1;
    await Promise.all([
      queryClient.cancelQueries({ queryKey: ["academic", "gradebook", groupId] }),
      queryClient.cancelQueries({ queryKey: ["academic", "gradebook-trends", groupId] }),
    ]);
    gradebookCacheRef.current.clear();
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["academic", "gradebook", groupId] }),
      queryClient.invalidateQueries({ queryKey: ["academic", "gradebook-trends", groupId] }),
    ]);
    await load(groupId, undefined, {
      view: activeView,
      month: activeView === "gradebook" ? lessonMonth : "",
      force: true,
    });
  }

  async function prepareGradebookCacheMutation() {
    loadRequestRef.current += 1;
    await Promise.all([
      queryClient.cancelQueries({ queryKey: ["academic", "gradebook", groupId] }),
      queryClient.cancelQueries({ queryKey: ["academic", "gradebook-trends", groupId] }),
    ]);
    gradebookCacheRef.current.clear();
    await queryClient.invalidateQueries({ queryKey: ["academic", "gradebook-trends", groupId] });
  }

  function openAddStudent() {
    setStudentOpen(true);
    setStudentName("");
    setStudentError("");
    setCreatedStudent(null);
  }

  function updateSetupField<K extends keyof GroupSetupForm>(key: K, value: GroupSetupForm[K]) {
    setSetupForm((current) => ({ ...current, [key]: value }));
  }

  function activeScheduleRow() {
    return scheduleRows.find((row) => asNumber(row.group_id) === groupId && asString(row.status) === "active");
  }

  function hasExistingSchedule() {
    return Boolean(activeScheduleRow());
  }

  function toggleSetupWeekday(day: number) {
    setSetupForm((current) => ({
      ...current,
      weekdays: current.weekdays.includes(day)
        ? current.weekdays.filter((value) => value !== day)
        : [...current.weekdays, day].sort(),
    }));
  }

  function dateInput(value: unknown) {
    const text = asString(value);
    const match = text.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    return match ? `${match[3]}-${match[2]}-${match[1]}` : text.slice(0, 10);
  }

  function openGroupSetup() {
    const existing = activeScheduleRow();
    const scheduledLessons = (data?.lessons || []).filter((lesson) => Boolean(lesson.date));
    const firstLesson = [...scheduledLessons].sort((left, right) => asString(left.date).localeCompare(asString(right.date)))[0];
    const start = asString(existing?.start_time) || asString(firstLesson?.startTime) || "14:00";
    const next = {
      teacherId: asString(existing?.teacher_id), startDate: dateInput(existing?.start_date) || lessonDateToInputValue(firstLesson?.date || ""),
      weekdays: asString(existing?.weekdays).split(",").map(Number).filter((day) => day >= 0 && day <= 6),
      startTime: start, room: asString(existing?.room), changeScope: existing ? "remaining" : "", effectiveDate: "",
      changeLaunchDate: false, allowRecordedChanges: false,
    };
    if (!next.weekdays.length) next.weekdays = [0, 2];
    setSetupForm(next);
    setSetupInitial(JSON.stringify(next));
    setSetupSuccess("");
    setSetupError("");
    setSetupOpen(true);
  }

  function hasExistingTimetable() {
    return hasSavedSetup
      || scheduleRows.some((row) => asNumber(row.group_id) === groupId && asString(row.status) === "active")
      || Boolean(data?.lessons?.some((lesson) => Boolean(lesson.date && lesson.startTime)));
  }

  function toggleCourseLaunchDateChange() {
    const savedStartDate = dateInput(activeScheduleRow()?.start_date);
    setSetupForm((current) => ({
      ...current,
      startDate: current.changeLaunchDate && savedStartDate ? savedStartDate : current.startDate,
      changeLaunchDate: !current.changeLaunchDate,
    }));
  }

  function changeSetupScope(value: string) {
    setSetupForm((current) => ({
      ...current,
      changeScope: value,
      effectiveDate: value === "from_date" ? current.effectiveDate : "",
      allowRecordedChanges: false,
    }));
  }

  function closeGroupSetup() {
    if (setupSaving) return;
    if (setupInitial && JSON.stringify(setupForm) !== setupInitial && !window.confirm("Discard unsaved group setup changes?")) return;
    setSetupOpen(false);
  }

  async function saveGroupSetup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (setupSaving || setupForm.weekdays.length === 0) return;
    setSetupSaving(true);
    setSetupError("");
    setSetupSuccess("");
    try {
      const response = await fetch(academicRoutes.adminAcademicGroupSchedule(groupId), {
        method: "PUT",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({
          group_id: groupId,
          teacher_id: Number(setupForm.teacherId || 0),
          weekdays: setupForm.weekdays,
          lesson_time: setupForm.startTime,
          lesson_duration_minutes: lessonDurationMinutesForSchoolCode(data?.group.schoolCode),
          course_launch_date: setupForm.startDate,
          room: setupForm.room,
          change_scope: setupForm.changeScope,
          effective_date: setupForm.effectiveDate,
          change_course_launch_date: setupForm.changeLaunchDate,
          allow_recorded_lesson_changes: setupForm.allowRecordedChanges,
        }),
      });
      const json = await response.json();
      if (!apiSucceeded(response, json)) {
        setSetupError(apiErrorMessage(json, "Unable to save group setup."));
        return;
      }
      const result = apiData<{ schedule?: Record<string, unknown> }>(json).schedule || {};
      const responseData = apiData<{ schedule?: Record<string, unknown>; schedules?: Array<Record<string, unknown>> }>(json);
      setSetupSuccess(`${asNumber(result.affectedLessonCount)} lessons scheduled.`);
      setSetupInitial(JSON.stringify(setupForm));
      if (Array.isArray(responseData.schedules)) setScheduleRows(responseData.schedules);
      setHasSavedSetup(true);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["academic", "timetable", groupId] }),
        queryClient.invalidateQueries({ queryKey: ["academic", "gradebook", groupId] }),
        queryClient.invalidateQueries({ queryKey: ["academic", "gradebook-trends", groupId] }),
      ]);
      if (activeView !== "timetable") await refreshCurrentView();
      setSetupOpen(false);
      showSetupToast(`${asNumber(result.affectedLessonCount)} lessons scheduled.`);
    } catch {
      setSetupError("Network error while saving group setup.");
    } finally {
      setSetupSaving(false);
    }
  }

  async function addStudent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!studentName.trim() || studentSaving) return;
    setStudentSaving(true);
    setStudentError("");
    try {
      const response = await fetch(academicRoutes.adminAcademicGroupStudents(groupId), {
        method: "POST", headers: jsonCsrfHeaders(csrf), body: JSON.stringify({ full_name: studentName.trim() }),
      });
      const json = await response.json();
      if (!apiSucceeded(response, json)) {
        setStudentError(apiErrorMessage(json, "Unable to add student."));
        return;
      }
      const student = apiData<{ student?: Record<string, unknown> }>(json).student || {};
      setCreatedStudent(student);
      await refreshCurrentView();
      showSetupToast(`${studentName.trim()} added to the group.`);
    } catch {
      setStudentError("Network error while adding the student.");
    } finally {
      setStudentSaving(false);
    }
  }

  function openCell(
    e: React.MouseEvent<HTMLButtonElement>,
    enrollmentId: number,
    lesson: Lesson,
    kind: "att" | "hw",
    currentHw: number | undefined,
  ) {
    if (isCancelledLesson(lesson)) return;
    if (kind === "hw" && !lessonCanHaveHomework(lesson)) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setActiveExam(null);
    setCellError("");
    setActive({ enrollmentId, lesson, kind, anchorRect: rect });
    setHwInput(currentHw !== undefined ? String(currentHw) : "");
  }

  function close() {
    setActive(null);
    setSaving(false);
    setCellError("");
  }

  async function saveAtt(status: AttValue) {
    if (!active || saving) return;
    setSaving(true);
    try {
      const res = await fetch(academicRoutes.adminAcademicAttendanceApi, {
        method: "POST",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_session_id: active.lesson.id,
          lesson_label: active.lesson.lessonNumber,
          status,
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          attendance_type: "regular",
        }),
      });
      const json = await res.json().catch(() => ({}));
      if (!apiSucceeded(res, json)) {
        setCellError(apiErrorMessage(json, "Unable to update attendance."));
        return;
      }
      await prepareGradebookCacheMutation();
      patchAtt(active.enrollmentId, active.lesson.id, active.lesson.lessonNumber, status);
      close();
    } catch {
      setCellError("Network error. Check the connection and try this cell again.");
    } finally {
      setSaving(false);
    }
  }

  async function saveHw() {
    if (!active || saving || hwInput === "") return;
    const score = parseFloat(hwInput);
    if (isNaN(score)) return;
    if (score < 1 || score > 9) {
      setCellError("Homework score must be between 1 and 9.");
      return;
    }
    setSaving(true);
    setCellError("");
    try {
      const res = await fetch(academicRoutes.adminAcademicHomeworkApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_session_id: active.lesson.id,
          lesson_label: active.lesson.lessonNumber,
          score,
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          score_type: "Homework",
        }),
      });
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setCellError(apiErrorMessage(json, "Unable to update homework score."));
        return;
      }
      const result = apiData<{ studentSummary?: { averageGrade?: number } }>(json);
      await prepareGradebookCacheMutation();
      patchHw(active.enrollmentId, active.lesson.id, active.lesson.lessonNumber, score, result.studentSummary?.averageGrade);
      close();
    } catch {
      setCellError("Network error. Check the connection and try this cell again.");
    } finally {
      setSaving(false);
    }
  }

  function patchAtt(enrollmentId: number, lessonId: number, lessonNumber: string, status: AttValue) {
    const update = (prev: GradebookData | null | undefined) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) => {
          if (en.enrollmentId !== enrollmentId) return en;
          const att = { ...en.attendance };
          const byLessonId = { ...(en.attendanceByLessonId || {}) };
          if (status) att[lessonNumber] = status;
          else delete att[lessonNumber];
          if (status) byLessonId[String(lessonId)] = status;
          else delete byLessonId[String(lessonId)];
          return { ...en, attendance: att, attendanceByLessonId: byLessonId };
        }),
      };
    };
    setData((previous) => update(previous) ?? previous);
    queryClient.setQueriesData<GradebookData>(
      { queryKey: ["academic", "gradebook", groupId] },
      (previous) => update(previous) || previous,
    );
    void queryClient.invalidateQueries({ queryKey: ["academic", "gradebook", groupId], refetchType: "none" });
  }

  function patchHw(enrollmentId: number, lessonId: number, lessonNumber: string, score: number, averageGrade?: number) {
    const update = (prev: GradebookData | null | undefined) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) =>
          en.enrollmentId !== enrollmentId
            ? en
            : {
                ...en,
                averageGrade: averageGrade ?? en.averageGrade,
                homework: { ...en.homework, [lessonNumber]: score },
                homeworkByLessonId: { ...(en.homeworkByLessonId || {}), [String(lessonId)]: score },
              },
        ),
      };
    };
    setData((previous) => update(previous) ?? previous);
    queryClient.setQueriesData<GradebookData>(
      { queryKey: ["academic", "gradebook", groupId] },
      (previous) => update(previous) || previous,
    );
    void queryClient.invalidateQueries({ queryKey: ["academic", "gradebook", groupId], refetchType: "none" });
  }

  function patchExam(enrollmentId: number, examLabel: string, score: number) {
    const update = (prev: GradebookData | null | undefined) => {
      if (!prev) return prev;
      const update = (en: Enrollment) =>
        en.enrollmentId !== enrollmentId
          ? en
          : { ...en, exams: { ...(en.exams || {}), [examLabel]: score } };
      return {
        ...prev,
        enrollments: prev.enrollments.map(update),
        allEnrollments: prev.allEnrollments?.map(update) ?? prev.allEnrollments,
      };
    };
    setData((previous) => update(previous) ?? previous);
    queryClient.setQueriesData<GradebookData>(
      { queryKey: ["academic", "gradebook", groupId] },
      (previous) => update(previous) || previous,
    );
    void queryClient.invalidateQueries({ queryKey: ["academic", "gradebook", groupId], refetchType: "none" });
  }

  function openExamEditor(enrollment: Enrollment, examLabel: string) {
    if (examSavingKey) return;
    const current = enrollment.exams?.[examLabel];
    setActive(null);
    setActiveExam({
      enrollmentId: enrollment.enrollmentId,
      examLabel,
      attempt: enrollment.examAttempts?.[examLabel] || "",
    });
    setExamInput(current !== undefined ? formatScoreOutOfNine(current) : "");
  }

  function cancelExamEdit() {
    if (examSavingKey) return;
    setActiveExam(null);
    setExamInput("");
  }

  async function saveExamScore() {
    if (!activeExam || examSavingKey) return;
    const trimmed = examInput.trim();
    if (!trimmed) {
      cancelExamEdit();
      return;
    }
    const score = Number(trimmed);
    if (!Number.isFinite(score) || score < 1 || score > 9) {
      setError("Exam score must be between 1 and 9.");
      return;
    }
    const key = `${activeExam.enrollmentId}:${activeExam.examLabel}`;
    setExamSavingKey(key);
    setError("");
    try {
      const res = await fetch(academicRoutes.adminAcademicExamApi, {
        method: "POST",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({
          enrollment_id: activeExam.enrollmentId,
          exam_name: activeExam.examLabel,
          attempt: activeExam.attempt,
          score,
        }),
      });
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setError(apiErrorMessage(json, "Unable to update exam score."));
        return;
      }
      await prepareGradebookCacheMutation();
      patchExam(activeExam.enrollmentId, activeExam.examLabel, score);
      setActiveExam(null);
      setExamInput("");
    } catch {
      setError("Network error while updating the exam score.");
    } finally {
      setExamSavingKey(null);
    }
  }

  async function updateEnrollmentStatus(enrollmentId: number, status: "active" | "disqualified" | "banned") {
    if (statusSavingId) return;
    let reason = "";
    if (status === "disqualified") {
      reason = window.prompt("Reason for disqualification?", "") || "";
    }
    setStatusSavingId(enrollmentId);
    try {
      const res = await fetch(academicRoutes.adminAcademicEnrollmentStatusApi(enrollmentId), {
        method: "PATCH",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ status, reason }),
      });
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setError(apiErrorMessage(json, "Unable to update enrollment."));
        return;
      }
      setSelectedStudent(null);
      await refreshCurrentView();
    } catch {
      setError("Network error.");
    } finally {
      setStatusSavingId(null);
    }
  }

  async function moveEnrollment(enrollmentId: number) {
    if (!moveGroupId || moveSaving) return;
    setMoveSaving(true);
    setError("");
    try {
      const res = await fetch(academicRoutes.adminAcademicEnrollmentGroupApi(enrollmentId), {
        method: "PATCH",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ group_id: Number(moveGroupId) }),
      });
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setError(apiErrorMessage(json, "Unable to move student."));
        return;
      }
      setSelectedStudent(null);
      setMoveGroupId("");
      await refreshCurrentView();
    } catch {
      setError("Network error.");
    } finally {
      setMoveSaving(false);
    }
  }

  function isCancelledLesson(lesson: Lesson) {
    const status = asString(lesson.status).toLowerCase();
    const kind = asString(lesson.sourceKind).toLowerCase();
    const label = asString(lesson.lessonNumber).toLowerCase();
    return status === "cancelled" || status === "canceled" || kind === "cancelled" || label.includes("cancelled") || label.includes("canceled");
  }

  function lessonCanHaveHomework(lesson: Lesson) {
    return !isCancelledLesson(lesson) && lesson.hasHomework !== false;
  }

  function moveGradebookCellFocus(event: React.KeyboardEvent<HTMLButtonElement>, row: number, column: number) {
    const offsets: Record<string, [number, number]> = {
      ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1],
    };
    if (event.key === "Escape") {
      close();
      return;
    }
    const offset = offsets[event.key];
    if (!offset) return;
    event.preventDefault();
    const target = document.querySelector<HTMLButtonElement>(
      `[data-gradebook-cell="${row + offset[0]}:${column + offset[1]}"]`,
    );
    target?.focus();
  }

  function lessonDateToInputValue(value: string) {
    const text = asString(value).trim();
    const ddmmyy = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2})$/);
    if (ddmmyy) {
      const [, day, month, year] = ddmmyy;
      return `20${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
    }
    const ddmmyyyy = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (ddmmyyyy) {
      const [, day, month, year] = ddmmyyyy;
      return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
    }
    const iso = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (iso) {
      const [, year, month, day] = iso;
      return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
    }
    return "";
  }

  function formatGradebookDate(value: unknown) {
    const text = asString(value).trim();
    if (!text) return "";
    const ddmmyyyy = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/);
    if (ddmmyyyy) {
      const [, day, month, year] = ddmmyyyy;
      return `${day.padStart(2, "0")}/${month.padStart(2, "0")}/${year.slice(-2)}`;
    }
    const iso = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (iso) {
      const [, year, month, day] = iso;
      return `${day.padStart(2, "0")}/${month.padStart(2, "0")}/${year.slice(-2)}`;
    }
    return text;
  }

  function lessonIsRecordedInsideClosure(lesson: Lesson) {
    if (!lesson.hasAcademicRecords) return false;
    const lessonDate = lessonDateToInputValue(lesson.date);
    if (!lessonDate) return false;
    return Boolean(data?.calendarClosures?.some(
      (closure) => closure.startDate <= lessonDate && lessonDate <= closure.endDate,
    ));
  }

  const lessons = data?.lessons ?? [];
  const examLabels = data?.examLabels ?? [];
  const enrollments = data?.enrollments ?? [];
  const allEnrollments = data?.allEnrollments ?? enrollments;
  const gradebookMonthOptions = data?.pageInfo?.monthOptions ?? [];
  const selectedLessonMonth = data?.pageInfo?.selectedMonth || lessonMonth;
  const selectedLessonMonthLabel = gradebookMonthOptions.find(
    (option) => option.value === selectedLessonMonth,
  )?.label || selectedLessonMonth;
  const selectedLessonMonthOption = gradebookMonthOptions.find(
    (option) => option.value === selectedLessonMonth,
  );
  const visibleCurriculumLessonCount = lessons.filter((lesson) => !isCancelledLesson(lesson)).length;
  const visibleCancellationCount = lessons.length - visibleCurriculumLessonCount;
  const scheduledCurriculumLessonCount = gradebookMonthOptions.reduce(
    (total, option) => total + asNumber(option.lessonCount),
    0,
  );
  const unscheduledLessonCount = Math.max(
    0,
    asNumber(data?.pageInfo?.totalLessons) - scheduledCurriculumLessonCount,
  );
  const gradebookTableWidth =
    GRADEBOOK_STUDENT_COL_WIDTH +
    GRADEBOOK_AAP_COL_WIDTH +
    lessons.length * GRADEBOOK_LESSON_COL_WIDTH;
  const disqualifiedEnrollments = allEnrollments.filter((en) => en.status === "disqualified");
  const bannedEnrollments = allEnrollments.filter((en) => en.status === "banned");
  const metricLessons = useMemo(() => lessons.filter((lesson) => !isCancelledLesson(lesson)), [lessons]);
  const indicatorLessons = metricLessons;
  const examTypeOptions = useMemo(() => collectExamTypeOptions(examLabels), [examLabels]);
  const selectedExamType = examType === "all" ? null : examTypeOptions.find((option) => option.key === examType) || null;
  const selectedExamTypeValue = selectedExamType ? selectedExamType.key : "all";
  const selectedExamLabels = selectedExamType ? selectedExamType.labels : examLabels;
  const examTableMinWidth = Math.max(
    EXAM_TABLE_MIN_WIDTH,
    EXAM_TABLE_STUDENT_COL_WIDTH + selectedExamLabels.length * EXAM_TABLE_SCORE_COL_WIDTH,
  );

  const academicIndicatorData = useMemo(() => enrollments.map(en => {
    const homeworkScores = indicatorLessons
      .map((lesson) => scoreOutOfNine(en.homeworkByLessonId?.[String(lesson.id)] ?? en.homework[lesson.lessonNumber]))
      .filter((score) => score > 0);
    const filteredAAP = averageScore(homeworkScores);
    const aap = filteredAAP;
    const attendanceValues = indicatorLessons
      .map((lesson) => en.attendanceByLessonId?.[String(lesson.id)] ?? en.attendance[lesson.lessonNumber])
      .filter((status) => ["present", "absent", "justified"].includes(status));
    const present = attendanceValues.filter((status) => status === "present").length;
    const total = attendanceValues.length;
    const arRate = total > 0 ? Math.round((present / total) * 100) : null;
    const arScore = arRate === null ? null : Math.round((arRate / 100) * 90) / 10;
    const averagePerformance = averageScore([aap, arScore]);
    return {
      name: en.fullName,
      enrollmentId: en.enrollmentId,
      AAP: aap,
      AR: arRate,
      arScore,
      averagePerformance,
      isLowAAP: aap !== null && aap < 5,
      isLowAR: arRate !== null && arRate < 80,
      present,
      total,
      recordedAttendance: total,
      scheduledLessons: indicatorLessons.length,
    };
  }), [enrollments, indicatorLessons]);
  const hasAcademicIndicatorData = academicIndicatorData.some((row) => row.AAP !== null || row.AR !== null);
  const academicAverageAAP = averageScore(academicIndicatorData.map((row) => row.AAP));
  const academicAverageAR = averageScore(academicIndicatorData.map((row) => row.AR));
  const academicAveragePerformance = averageScore(academicIndicatorData.map((row) => row.averagePerformance));
  const academicChartMinWidth = Math.max(640, academicIndicatorData.length * 84);
  const academicTrendsQuery = useQuery({
    queryKey: ["academic", "gradebook-trends", groupId, selectedLessonMonth, 6],
    enabled: Boolean(data && activeView === "gradebook" && gradebookDisplay === "chart" && selectedLessonMonth),
    staleTime: 60_000,
    queryFn: async ({ signal }) => {
      const response = await fetch(
        academicRoutes.adminAcademicGradebookTrendsApi(groupId, { through: selectedLessonMonth, months: 6 }),
        { signal },
      );
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Unable to load academic trends."));
      return apiData<AcademicTrendsData>(json);
    },
  });
  const academicTrendItems = academicTrendsQuery.data?.items ?? [];
  const academicTrendCurrentIndex = academicTrendItems.findIndex((item) => item.month === selectedLessonMonth);
  const academicTrendCurrent = academicTrendCurrentIndex >= 0 ? academicTrendItems[academicTrendCurrentIndex] : undefined;
  const academicTrendPrevious = academicTrendCurrentIndex > 0 ? academicTrendItems[academicTrendCurrentIndex - 1] : undefined;
  const previousTrendMonth = academicTrendPrevious?.month || offsetMonthKey(selectedLessonMonth, -1);
  const displayedAcademicAAP = academicTrendCurrent ? academicTrendCurrent.avgAAP : academicAverageAAP;
  const displayedAcademicAR = academicTrendCurrent ? academicTrendCurrent.avgAR : academicAverageAR;
  const displayedAcademicPerformance = academicTrendCurrent ? academicTrendCurrent.avgPerformance : academicAveragePerformance;
  const hasAcademicTrendData = academicTrendItems.some(
    (item) => item.avgAAP !== null || item.avgAR !== null || item.avgPerformance !== null,
  );

  let filteredExamScoreSum = 0;
  let filteredExamScoreCount = 0;
  let filteredHighestExamScore = -Infinity;
  const studentExamData = enrollments.map(en => {
    let maxVal = -1;
    let sumVal = 0;
    let countVal = 0;
    selectedExamLabels.forEach(label => {
      const val = en.exams?.[label];
      if (typeof val === 'number') {
        const normalizedVal = scoreOutOfNine(val);
        if (normalizedVal <= 0) return;
        filteredExamScoreSum += normalizedVal;
        filteredExamScoreCount++;
        if (normalizedVal > filteredHighestExamScore) {
          filteredHighestExamScore = normalizedVal;
        }
        sumVal += normalizedVal;
        countVal++;
        if (normalizedVal > maxVal) {
          maxVal = normalizedVal;
        }
      }
    });
    const avgScore = countVal > 0 ? Math.round((sumVal / countVal) * 10) / 10 : 0;
    const bestScore = maxVal !== -1 ? maxVal : 0;
    const chartScore = selectedExamType ? avgScore : bestScore;
    const missing = Math.max(0, selectedExamLabels.length - countVal);
    return {
      name: en.fullName,
      avgScore,
      bestScore,
      chartScore,
      missing,
      hasExams: countVal > 0
    };
  });

  const filteredClassExamAverage = filteredExamScoreCount > 0 ? (filteredExamScoreSum / filteredExamScoreCount).toFixed(1) : "—";
  const filteredMaxScore = filteredHighestExamScore !== -Infinity ? filteredHighestExamScore : "—";
  const hasFilteredExamScores = filteredExamScoreCount > 0;
  const studentsWithMissingExams = selectedExamLabels.length > 0 ? studentExamData.filter(s => !s.hasExams).length : 0;

  useEffect(() => {
    setActive(null);
  }, [activeView]);

  const popTop = active
    ? Math.min(active.anchorRect.bottom + 4, window.innerHeight - 200)
    : 0;
  const popLeft = active
    ? Math.min(active.anchorRect.left, window.innerWidth - 220)
    : 0;
  const detailMetricClass = `rounded-lg border border-foreground/8 bg-background p-3 shadow-sm ${motion.card}`;
  const panelCardClass = `rounded-xl border border-foreground/8 bg-surface shadow-card ${motion.panel}`;
  const chartPanelClass = `rounded-xl border border-foreground/8 bg-gradient-to-b from-background to-muted/20 p-3 shadow-sm transition-shadow duration-200 hover:shadow-card ${motion.panel}`;
  return (
    <div className={`w-full min-w-0 max-w-full space-y-3 overflow-x-hidden ${motion.panel}`} aria-busy={loading}>
      <FloatingToast toast={setupToast} />
      {/* 1. Summary Header */}
      <div className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border border-foreground/10 bg-surface px-4 py-3 shadow-card ${motion.card}`}>
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1 rounded-lg border border-foreground/10 px-2.5 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-muted"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            Groups
          </button>
          {data && (
            <span className="text-sm font-bold">
              {data.group.name}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {data.group.subjectName} · {data.group.schoolCode}
              </span>
            </span>
          )}
          {data && (
            <span className="text-xs text-muted-foreground">
              {enrollments.length} active · {disqualifiedEnrollments.length} disqualified · {bannedEnrollments.length} banned · {data.pageInfo?.totalLessons ?? lessons.length} lessons · {data.group.examCount ?? examLabels.length} exams
            </span>
          )}
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-emerald-500 text-[9px] font-bold text-white">P</span> Present
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-red-500 text-[9px] font-bold text-white">A</span> Absent
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded bg-amber-400 text-[9px] font-bold text-white">J</span> Justified
            </span>
          </div>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}

      {/* 2. View Switcher Buttons */}
      {data && (
        <div className="flex border-b border-foreground/8 gap-2 overflow-x-auto py-1">
          {(["gradebook", "ep", "timetable"] as const).map((view) => {
            const labels: Record<string, string> = {
              gradebook: "Gradebook",
              ep: "Exam Performance",
              timetable: "Timetable",
            };
            const isActive = activeView === view;
            return (
              <button
                key={view}
                type="button"
                onClick={() => changeView(view)}
                className={`border-b-2 px-4 py-2 text-xs font-bold uppercase tracking-wider whitespace-nowrap ${motion.button} ${
                  isActive
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {labels[view]}
              </button>
            );
          })}
        </div>
      )}

      {/* 4. Active Panel Content */}
      {data && activeView === "gradebook" && loadedView === "gradebook" && (
        <div className={`min-w-0 max-w-full overflow-hidden rounded-xl border border-foreground/8 bg-surface shadow-card ${motion.panel}`}>
          <div className="border-b border-foreground/8 px-4 py-3">
            <p className="text-sm font-bold">Gradebook</p>
            <p className="text-xs text-muted-foreground">Curriculum lessons with attendance and homework</p>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-foreground/8 bg-muted/20 px-3 py-2">
            <div className="flex min-w-0 flex-wrap items-center gap-1.5">
              <div className="inline-flex h-11 rounded-lg border border-foreground/10 bg-background p-1 sm:h-9">
                {(["table", "chart"] as GradebookDisplayMode[]).map((mode) => {
                  const selected = gradebookDisplay === mode;
                  return (
                    <button
                      key={mode}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => changeGradebookDisplay(mode)}
                      className={`inline-flex min-w-20 items-center justify-center gap-1.5 rounded-md px-2.5 text-xs font-bold capitalize transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${selected ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
                    >
                      {mode === "table" ? <Table2 className="h-3.5 w-3.5" /> : <BarChart3 className="h-3.5 w-3.5" />}
                      {mode}
                    </button>
                  );
                })}
              </div>
              <span aria-hidden="true" className="mx-1 hidden h-6 w-px bg-foreground/10 sm:block" />
              <button type="button" aria-label="Previous month" disabled={!data.pageInfo?.previousMonth || loading} onClick={() => openLessonMonth(data.pageInfo?.previousMonth)} className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-foreground/10 bg-background text-foreground disabled:opacity-35 sm:h-9 sm:w-9"><ChevronLeft className="h-4 w-4" /></button>
              <div className="flex h-11 min-w-0 items-center gap-2 rounded-lg border border-foreground/10 bg-background px-3 sm:h-9">
                <CalendarDays className="h-4 w-4 shrink-0 text-muted-foreground" />
                <select
                  id="gradebook-month"
                  aria-label="Gradebook month"
                  value={selectedLessonMonth}
                  disabled={loading || gradebookMonthOptions.length === 0}
                  onChange={(event) => openLessonMonth(event.target.value)}
                  className="min-w-0 max-w-[12rem] bg-transparent text-sm font-bold text-foreground outline-none disabled:opacity-50"
                >
                  {gradebookMonthOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}{option.hasClosure ? " — Holiday" : ""}</option>
                  ))}
                </select>
              </div>
              <button type="button" aria-label="Next month" disabled={!data.pageInfo?.nextMonth || loading} onClick={() => openLessonMonth(data.pageInfo?.nextMonth)} className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-foreground/10 bg-background text-foreground disabled:opacity-35 sm:h-9 sm:w-9"><ChevronRight className="h-4 w-4" /></button>
              <span className="px-1 text-xs font-semibold tabular-nums text-muted-foreground">
                {visibleCurriculumLessonCount} {visibleCurriculumLessonCount === 1 ? "lesson" : "lessons"}
                {visibleCancellationCount > 0 ? ` · ${visibleCancellationCount} cancelled` : ""}
              </span>
            </div>
            <button type="button" disabled={loading} onClick={jumpToCurrentMonth} className="h-11 shrink-0 rounded-lg border border-primary/20 bg-primary/5 px-3 text-xs font-bold text-primary disabled:opacity-50 sm:h-9">This month</button>
          </div>

          {unscheduledLessonCount > 0 ? (
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">
              <span className="font-semibold">{unscheduledLessonCount} {unscheduledLessonCount === 1 ? "lesson is" : "lessons are"} not scheduled yet.</span>
              <button type="button" onClick={() => changeView("timetable")} className="font-bold text-amber-900 underline underline-offset-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50">Open Timetable</button>
            </div>
          ) : null}

          {selectedLessonMonthOption?.hasClosure ? (
            <div className="flex flex-wrap items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-900">
              <LockKeyhole className="h-4 w-4 shrink-0" />
              <span>{selectedLessonMonthOption.closureTitles?.join(", ") || "School holiday"}{selectedLessonMonthOption.protectedRecordCount ? ` · ${selectedLessonMonthOption.protectedRecordCount} recorded ${selectedLessonMonthOption.protectedRecordCount === 1 ? "lesson remains" : "lessons remain"} visible` : lessons.length ? " · protected lessons remain visible below" : " · no lessons scheduled"}</span>
            </div>
          ) : null}

          {gradebookDisplay === "table" ? (
            <>
              {lessons.length === 0 ? (
                <div className={`border-b px-4 py-4 text-xs ${selectedLessonMonthOption?.hasClosure ? "border-amber-200 bg-amber-50/40 text-amber-900" : "border-foreground/8 bg-muted/10 text-muted-foreground"}`}>
                  {selectedLessonMonthOption?.hasClosure ? `${selectedLessonMonthOption.closureTitles?.[0] || "School holiday"} — no lessons are scheduled in ${selectedLessonMonthLabel}.` : `No lessons are scheduled in ${selectedLessonMonthLabel || "this month"}. Student enrollment remains available below.`}
                </div>
              ) : null}
              <div
                ref={gradebookScrollRef}
                onScroll={(event) => { gradebookScrollLeftRef.current = event.currentTarget.scrollLeft; }}
                className="miniapp-table-scroll min-w-0 max-w-full overflow-auto [max-height:min(70dvh,calc(var(--tg-app-height)-17rem))] [scrollbar-gutter:stable]"
              >
                <table
                  className="w-full table-fixed border-collapse text-left text-[11px] sm:text-xs"
                  style={{ minWidth: Math.max(gradebookTableWidth, GRADEBOOK_STUDENT_COL_WIDTH + GRADEBOOK_AAP_COL_WIDTH) }}
                >
                  <colgroup>
                    <col style={{ width: GRADEBOOK_STUDENT_COL_WIDTH }} />
                    <col style={{ width: GRADEBOOK_AAP_COL_WIDTH }} />
                    {lessons.map((lesson) => (
                      <Fragment key={`gradebook-cols-${lesson.id}`}>
                        <col style={{ width: GRADEBOOK_ATT_COL_WIDTH }} />
                        <col style={{ width: GRADEBOOK_HW_COL_WIDTH }} />
                      </Fragment>
                    ))}
                  </colgroup>
                  <thead className="sticky top-0 z-30 shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                    <tr className="bg-surface">
                      <th className="sticky left-0 z-40 border-b border-r border-foreground/10 bg-surface px-3 py-3 font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]" style={{ width: GRADEBOOK_STUDENT_COL_WIDTH, minWidth: GRADEBOOK_STUDENT_COL_WIDTH, maxWidth: GRADEBOOK_STUDENT_COL_WIDTH }}>Student</th>
                      <th title="Overall AAP across recorded homework" className="sticky z-40 border-b border-r border-foreground/10 bg-surface px-1 py-3 text-center font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]" style={{ left: GRADEBOOK_STUDENT_COL_WIDTH, width: GRADEBOOK_AAP_COL_WIDTH, minWidth: GRADEBOOK_AAP_COL_WIDTH, maxWidth: GRADEBOOK_AAP_COL_WIDTH }}>AAP</th>
                      {lessons.map((lesson) => (
                        <th key={lesson.id} colSpan={2} className={`border-b border-l p-0 text-center align-top ${isCancelledLesson(lesson) ? "border-red-200 bg-red-50/55" : "border-foreground/10 bg-surface"}`} style={{ width: GRADEBOOK_LESSON_COL_WIDTH, minWidth: GRADEBOOK_LESSON_COL_WIDTH }}>
                          <div title={`${lesson.lessonNumber} - ${lesson.topic}`} className="flex min-h-[6.25rem] w-full flex-col items-center justify-start px-1 py-2">
                            <span className={`inline-flex max-w-full items-center justify-center gap-1 whitespace-nowrap text-[9px] font-bold leading-tight ${isCancelledLesson(lesson) ? "text-red-700" : "text-muted-foreground"}`} title="Date supplied by the timetable">
                              <CalendarDays className="h-2.5 w-2.5 shrink-0" />
                              {formatGradebookDate(lesson.date) || "Unscheduled"}
                            </span>
                            <span className={`mt-1 block whitespace-nowrap text-[9px] font-semibold ${isCancelledLesson(lesson) ? "text-red-700" : "text-muted-foreground/75"}`}>{lesson.lessonNumber}</span>
                            <span className={`mt-1 block w-full whitespace-normal break-words text-center text-[9px] font-medium italic leading-[1.15] ${isCancelledLesson(lesson) ? "text-red-700/80" : "text-muted-foreground/70"}`}>{lesson.topic || "—"}</span>
                            {lessonIsRecordedInsideClosure(lesson) ? <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[7px] font-bold leading-tight text-amber-900"><LockKeyhole className="h-2.5 w-2.5" />Recorded before holiday lock</span> : null}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-foreground/5 bg-surface">
                    {enrollments.map((en, enrollmentIndex) => (
                      <tr key={en.enrollmentId} className="group transition-colors hover:bg-muted/40">
                        <td className="sticky left-0 z-20 border-r border-foreground/8 bg-surface px-3 py-1.5 font-semibold text-sm shadow-[1px_0_0_hsl(var(--foreground)/0.08)] transition-colors group-hover:bg-muted/40" style={{ width: GRADEBOOK_STUDENT_COL_WIDTH, minWidth: GRADEBOOK_STUDENT_COL_WIDTH, maxWidth: GRADEBOOK_STUDENT_COL_WIDTH }}>
                          <button type="button" onClick={() => { setSelectedStudent(en); setMoveGroupId(""); }} className="line-clamp-2 w-full text-left font-semibold text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30" title={`Manage ${en.fullName}`}>{en.fullName}</button>
                        </td>
                        <td title="Overall AAP across recorded homework" className="sticky z-20 border-r border-foreground/8 bg-surface px-1 py-1.5 text-center font-bold text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)] transition-colors group-hover:bg-muted/40" style={{ left: GRADEBOOK_STUDENT_COL_WIDTH, width: GRADEBOOK_AAP_COL_WIDTH, minWidth: GRADEBOOK_AAP_COL_WIDTH, maxWidth: GRADEBOOK_AAP_COL_WIDTH }}>{en.averageGrade > 0 ? en.averageGrade.toFixed(0) : "–"}</td>
                        {lessons.map((lesson, lessonIndex) => {
                          const att = (en.attendanceByLessonId?.[String(lesson.id)] ?? en.attendance[lesson.lessonNumber] ?? "") as AttValue;
                          const hw = en.homeworkByLessonId?.[String(lesson.id)] ?? en.homework[lesson.lessonNumber];
                          const cancelled = isCancelledLesson(lesson);
                          const canEditHomework = lessonCanHaveHomework(lesson);
                          const isActiveAtt = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "att";
                          const isActiveHw = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "hw";
                          if (cancelled) {
                            return (
                              <td key={`${en.enrollmentId}-${lesson.id}-cancelled`} colSpan={2} className="border-l border-r border-red-100 bg-red-50/40 px-1 py-1.5 text-center transition-colors group-hover:bg-red-100/60" style={{ width: GRADEBOOK_LESSON_COL_WIDTH }}>
                                <span className="inline-flex max-w-full rounded-md bg-red-100 px-1 py-1 text-[8px] font-bold uppercase tracking-wide text-red-700 shadow-sm">Cancelled</span>
                              </td>
                            );
                          }
                          return (
                            <Fragment key={`${en.enrollmentId}-${lesson.id}`}>
                              <td className="border-l border-foreground/5 p-0.5 text-center" style={{ width: GRADEBOOK_ATT_COL_WIDTH }}>
                                <button type="button" data-gradebook-cell={`${enrollmentIndex}:${lessonIndex * 2}`} onClick={(event) => openCell(event, en.enrollmentId, lesson, "att", hw)} onKeyDown={(event) => moveGradebookCellFocus(event, enrollmentIndex, lessonIndex * 2)} title={`${en.fullName} · ${lesson.lessonNumber} · attendance`} className={`mx-auto flex h-9 w-8 items-center justify-center rounded-lg text-[10px] font-bold shadow-sm transition-[transform,opacity,box-shadow] hover:-translate-y-px hover:opacity-85 sm:h-7 sm:w-7 ${att ? attCls(att) : "text-foreground/20 shadow-none"} ${isActiveAtt ? "ring-2 ring-primary/35 ring-offset-1" : ""}`}>{att ? attLabel(att) : "·"}</button>
                              </td>
                              <td className="border-r border-foreground/5 p-0.5 text-center" style={{ width: GRADEBOOK_HW_COL_WIDTH }}>
                                <button type="button" data-gradebook-cell={`${enrollmentIndex}:${lessonIndex * 2 + 1}`} disabled={!canEditHomework} onClick={(event) => openCell(event, en.enrollmentId, lesson, "hw", hw)} onKeyDown={(event) => moveGradebookCellFocus(event, enrollmentIndex, lessonIndex * 2 + 1)} title={`${en.fullName} · ${lesson.lessonNumber} · homework`} className={`mx-auto flex h-9 min-w-9 items-center justify-center rounded-lg px-1 text-[10px] transition-[transform,opacity,box-shadow] hover:-translate-y-px hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 sm:h-7 sm:min-w-8 ${hw !== undefined ? "bg-blue-50 font-bold text-blue-700 shadow-sm" : "text-foreground/20"} ${isActiveHw ? "ring-2 ring-primary/35 ring-offset-1" : ""}`}>{canEditHomework && hw !== undefined ? hw : "·"}</button>
                              </td>
                            </Fragment>
                          );
                        })}
                      </tr>
                    ))}
                    <tr className="bg-muted/10">
                      <td className="sticky left-0 z-20 border-r border-foreground/8 bg-surface px-2 py-1.5 shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                        <button type="button" onClick={openAddStudent} className="inline-flex min-h-10 w-full items-center gap-2 rounded-lg px-2 text-left text-xs font-bold text-primary transition-colors hover:bg-primary/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"><Plus className="h-4 w-4" /> Add student</button>
                      </td>
                      <td colSpan={1 + lessons.length * 2} aria-hidden="true" className="bg-muted/10" />
                    </tr>
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="p-4">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h4 className="text-sm font-bold">Academic Indicators</h4>
                  <p className="text-xs text-muted-foreground">Monthly AAP and attendance rate · {selectedLessonMonthLabel}</p>
                </div>
              </div>
              <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className={detailMetricClass}>
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Avg AAP</span>
                  <span className="mt-1 block text-lg font-bold tabular-nums text-blue-600">{displayedAcademicAAP ?? "—"}</span>
                  {academicTrendsQuery.isPending ? <span className="mt-2 block h-2.5 w-24 rounded bg-muted motion-safe:animate-pulse" /> : academicTrendsQuery.isError ? <span className="mt-1.5 block text-[10px] font-semibold text-muted-foreground">Comparison unavailable</span> : <MetricDelta current={displayedAcademicAAP} previous={academicTrendPrevious?.avgAAP ?? null} previousMonth={previousTrendMonth} />}
                </div>
                <div className={detailMetricClass}>
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Avg AR</span>
                  <span className="mt-1 block text-lg font-bold tabular-nums text-emerald-600">{displayedAcademicAR ?? "—"}{displayedAcademicAR !== null ? <span className="text-xs font-normal text-muted-foreground">%</span> : null}</span>
                  {academicTrendsQuery.isPending ? <span className="mt-2 block h-2.5 w-24 rounded bg-muted motion-safe:animate-pulse" /> : academicTrendsQuery.isError ? <span className="mt-1.5 block text-[10px] font-semibold text-muted-foreground">Comparison unavailable</span> : <MetricDelta current={displayedAcademicAR} previous={academicTrendPrevious?.avgAR ?? null} previousMonth={previousTrendMonth} unit=" pp" />}
                </div>
                <div className={detailMetricClass}>
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Avg Performance</span>
                  <span className="mt-1 block text-lg font-bold tabular-nums">{displayedAcademicPerformance ?? "—"}{displayedAcademicPerformance !== null ? <span className="text-xs font-normal text-muted-foreground"> / 9</span> : null}</span>
                  {academicTrendsQuery.isPending ? <span className="mt-2 block h-2.5 w-24 rounded bg-muted motion-safe:animate-pulse" /> : academicTrendsQuery.isError ? <span className="mt-1.5 block text-[10px] font-semibold text-muted-foreground">Comparison unavailable</span> : <MetricDelta current={displayedAcademicPerformance} previous={academicTrendPrevious?.avgPerformance ?? null} previousMonth={previousTrendMonth} />}
                </div>
              </div>
              <div className="mb-3 flex justify-end">
                <div className="inline-flex rounded-xl border border-foreground/10 bg-muted/60 p-1" role="group" aria-label="Academic indicator chart view">
                  {(["trends", "students"] as const).map((mode) => {
                    const selected = academicChartMode === mode;
                    return (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setAcademicChartMode(mode)}
                        aria-pressed={selected}
                        className={`min-h-11 rounded-lg px-4 text-xs font-bold transition-[background-color,color,box-shadow] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${selected ? "bg-surface text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                      >
                        {mode === "trends" ? "Trends" : "Students"}
                      </button>
                    );
                  })}
                </div>
              </div>
              {academicChartMode === "trends" ? (
                <div key={`academic-trends-${selectedLessonMonth}`} className={motion.panel}>
                  {academicTrendsQuery.isPending ? (
                    <div className="h-[clamp(18rem,42dvh,26rem)] rounded-xl border border-foreground/8 bg-muted/35 p-5 motion-safe:animate-pulse" role="status" aria-label="Loading academic trends">
                      <div className="h-full rounded-lg bg-gradient-to-b from-background/40 to-muted/50" />
                    </div>
                  ) : academicTrendsQuery.isError ? (
                    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-12 text-center">
                      <p className="text-sm font-bold text-red-800">{academicTrendsQuery.error instanceof Error ? academicTrendsQuery.error.message : "Unable to load academic trends."}</p>
                      <button type="button" onClick={() => void academicTrendsQuery.refetch()} className="mt-3 min-h-11 rounded-lg border border-red-300 bg-surface px-4 text-xs font-bold text-red-800 transition-colors hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300">Retry</button>
                    </div>
                  ) : hasAcademicTrendData ? (
                    <>
                      <div className="h-[clamp(18rem,42dvh,26rem)] w-full" role="img" aria-label={`Six-month academic trend through ${selectedLessonMonthLabel}`}>
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={academicTrendItems} margin={{ top: 24, right: 8, left: 0, bottom: 4 }} accessibilityLayer>
                            <CartesianGrid strokeDasharray="3 5" vertical={false} stroke="hsl(var(--foreground)/0.08)" />
                            <XAxis dataKey="label" tickFormatter={(value) => asString(value).split(" ")[0]} tickLine={false} axisLine={false} tick={{ fontSize: 11, fontWeight: 600, fill: "hsl(var(--muted-foreground))" }} />
                            <YAxis yAxisId="score" domain={[0, 9]} ticks={[0, 3, 6, 9]} width={26} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                            <YAxis yAxisId="attendance" orientation="right" domain={[0, 100]} ticks={[0, 50, 100]} width={34} tickFormatter={(value) => `${value}%`} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                            <ReferenceLine x={academicTrendCurrent?.label} stroke="hsl(var(--primary)/0.32)" strokeDasharray="4 4" />
                            <Tooltip cursor={{ stroke: "hsl(var(--foreground)/0.16)", strokeDasharray: "3 3" }} wrapperClassName="!outline-none" content={<AcademicTrendTooltip />} />
                            <Legend verticalAlign="top" height={32} iconType="line" wrapperStyle={{ fontSize: 11, fontWeight: 700 }} />
                            <Line yAxisId="score" type="monotone" dataKey="avgAAP" name="AAP" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3, fill: "#2563eb", strokeWidth: 0 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={!prefersReducedMotion} animationDuration={380} animationEasing="ease-out" />
                            <Line yAxisId="score" type="monotone" dataKey="avgPerformance" name="Performance" stroke="#6d28d9" strokeWidth={2.5} strokeDasharray="8 4" dot={{ r: 3, fill: "#6d28d9", strokeWidth: 0 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={!prefersReducedMotion} animationBegin={50} animationDuration={380} animationEasing="ease-out" />
                            <Line yAxisId="attendance" type="monotone" dataKey="avgAR" name="Attendance" stroke="#059669" strokeWidth={2.5} strokeDasharray="2 5" dot={{ r: 3, fill: "#059669", strokeWidth: 0 }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={!prefersReducedMotion} animationBegin={100} animationDuration={380} animationEasing="ease-out" />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <table className="sr-only">
                        <caption>Monthly academic indicator values through {selectedLessonMonthLabel}</caption>
                        <thead><tr><th>Month</th><th>Calendar status</th><th>Average AAP</th><th>Attendance rate</th><th>Average performance</th><th>Lessons</th><th>Students with data</th><th>Homework records</th><th>Attendance records</th></tr></thead>
                        <tbody>{academicTrendItems.map((item) => <tr key={`trend-table-${item.month}`}><th>{formatTrendMonth(item.month)}</th><td>{item.hasClosure ? item.closureTitles?.join(", ") || "School holiday" : "Open"}</td><td>{item.avgAAP ?? "No data"}</td><td>{item.avgAR === null ? "No data" : `${item.avgAR}%`}</td><td>{item.avgPerformance ?? "No data"}</td><td>{item.lessonCount}</td><td>{item.studentsWithData}</td><td>{item.homeworkRecordCount}</td><td>{item.attendanceRecordCount}</td></tr>)}</tbody>
                      </table>
                    </>
                  ) : (
                    <div className="rounded-lg border border-dashed border-foreground/15 py-16 text-center text-sm text-muted-foreground">No academic indicator records are available in the six months through {selectedLessonMonthLabel}.</div>
                  )}
                </div>
              ) : hasAcademicIndicatorData ? (
                <div key={`academic-students-${selectedLessonMonth}`} className={`max-w-full overflow-x-auto pb-1 ${motion.panel}`}>
                  <div className="h-[clamp(18rem,44dvh,30rem)]" style={{ minWidth: academicChartMinWidth }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart key={`academic-chart-${selectedLessonMonth}`} data={academicIndicatorData} barCategoryGap="18%" barGap={3} margin={{ top: 28, right: 10, left: 4, bottom: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--foreground)/0.08)" />
                        <XAxis dataKey="name" interval={0} height={44} tick={<StudentNameTick />} tickLine={false} stroke="hsl(var(--muted-foreground))" />
                        <YAxis domain={[0, 9]} tickCount={10} hide />
                        <YAxis yAxisId="ar" orientation="right" domain={[0, 100]} tickCount={6} hide />
                        <Tooltip cursor={{ fill: "hsl(var(--primary) / 0.06)" }} wrapperClassName="!outline-none" content={<CompactChartTooltip percentKeys={["AR"]} />} />
                        <Legend verticalAlign="top" height={28} />
                        <Bar dataKey="AAP" name="AAP" fill="#3b82f6" radius={[6, 6, 0, 0]} maxBarSize={28} isAnimationActive={!prefersReducedMotion} animationBegin={60} animationDuration={480} animationEasing="ease-out">
                          <LabelList dataKey="AAP" position="top" fontSize={11} fontWeight={700} fill="#2563eb" formatter={formatBarLabel} />
                          {academicIndicatorData.map((entry) => <Cell key={`academic-aap-${entry.enrollmentId}`} fill={entry.isLowAAP ? "#ef4444" : "#3b82f6"} />)}
                        </Bar>
                        <Bar yAxisId="ar" dataKey="AR" name="AR" fill="#10b981" radius={[6, 6, 0, 0]} maxBarSize={28} isAnimationActive={!prefersReducedMotion} animationBegin={120} animationDuration={480} animationEasing="ease-out">
                          <LabelList dataKey="AR" position="top" fontSize={11} fontWeight={700} fill="#059669" formatter={formatPercentLabel} />
                          {academicIndicatorData.map((entry) => <Cell key={`academic-ar-${entry.enrollmentId}`} fill={entry.isLowAR ? "#f59e0b" : "#10b981"} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-foreground/15 py-16 text-center text-sm text-muted-foreground">No recorded academic indicator data for {selectedLessonMonthLabel || "this month"}.</div>
              )}
            </div>
          )}
        </div>
      )}

      {data && activeView === "ep" && loadedView === "ep" && (
        <div className={`overflow-hidden ${panelCardClass}`}>
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-foreground/8 px-4 py-3">
            <div>
              <p className="text-sm font-bold">Exam Performance</p>
              <p className="text-xs text-muted-foreground">Student results for taken exams</p>
            </div>
            <ExamTypeFilter
              value={selectedExamTypeValue}
              options={examTypeOptions}
              onChange={setExamType}
            />
          </div>
          {examLabels.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No exam results are recorded for this group yet.
            </div>
          ) : (
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className={detailMetricClass}>
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Exams Taken</span>
                  <span className="mt-1 block text-lg font-bold">{selectedExamLabels.length}</span>
                </div>
                <div className={detailMetricClass}>
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Class Average</span>
                  <span className="mt-1 block text-lg font-bold">
                    {filteredClassExamAverage}
                    {hasFilteredExamScores ? <span className="text-xs font-normal text-muted-foreground"> / 9.0</span> : null}
                  </span>
                </div>
                <div className={detailMetricClass}>
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Highest Score</span>
                  <span className="mt-1 block text-lg font-bold">
                    {filteredMaxScore}
                    {hasFilteredExamScores ? <span className="text-xs font-normal text-muted-foreground"> / 9</span> : null}
                  </span>
                </div>
                <div className={detailMetricClass}>
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">No Exam Score</span>
                  <span className="mt-1 block text-lg font-bold">{studentsWithMissingExams}</span>
                </div>
              </div>

              <div className={chartPanelClass}>
                <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-bold">Student Exam Performance</h4>
                    <p className="text-xs text-muted-foreground">
                      {selectedExamType ? `${selectedExamType.label} score on the 1-9 scale` : "Best exam score on the 1-9 scale"}
                    </p>
                  </div>
                  <ExamViewSwitcher value={examDisplay} onChange={setExamDisplay} />
                </div>
                {examDisplay === "chart" ? (
                  hasFilteredExamScores ? (
                    <div className={`overflow-hidden ${motion.panel}`}>
                      <div className="h-[clamp(19rem,46dvh,32rem)] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            key={`exam-chart-${selectedExamTypeValue}`}
                            data={studentExamData}
                            barCategoryGap="34%"
                            margin={{ top: 28, right: 10, left: 4, bottom: 8 }}
                          >
                            <defs>
                              <linearGradient id="exam-score-gradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#60a5fa" />
                                <stop offset="100%" stopColor="#2563eb" />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--foreground)/0.08)" />
                            <XAxis
                              dataKey="name"
                              interval={0}
                              height={44}
                              tick={<StudentNameTick />}
                              tickLine={false}
                              stroke="hsl(var(--muted-foreground))"
                            />
                            <YAxis domain={[0, 9]} tickCount={10} hide />
                            <Tooltip
                              cursor={{ fill: "hsl(var(--primary) / 0.06)" }}
                              wrapperClassName="!outline-none"
                              content={<CompactChartTooltip />}
                            />
                            <Bar
                              dataKey="chartScore"
                              fill="url(#exam-score-gradient)"
                              radius={[7, 7, 0, 0]}
                              name="Score"
                              maxBarSize={34}
                              activeBar={{ fill: "#2563eb", stroke: "#1d4ed8", strokeWidth: 1 }}
                              isAnimationActive={!prefersReducedMotion}
                              animationBegin={60}
                              animationDuration={480}
                              animationEasing="ease-out"
                            >
                              <LabelList dataKey="chartScore" position="top" fontSize={11} fontWeight={700} fill="#1e2d4a" formatter={formatBarLabel} />
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  ) : (
                    <div className="py-16 text-center text-sm text-muted-foreground">
                      No exam scores match this filter.
                    </div>
                  )
                ) : null}

                {examDisplay === "table" && selectedExamLabels.length > 0 ? (
                  <div
                    className="miniapp-table-scroll max-h-[min(76dvh,48rem)] min-h-0 w-full rounded-lg border border-foreground/8 [scrollbar-gutter:stable]"
                  >
                    <table
                      className="w-full table-fixed border-collapse text-left text-[11px]"
                      style={{ minWidth: examTableMinWidth }}
                    >
                      <colgroup>
                        <col style={{ width: EXAM_TABLE_STUDENT_COL_WIDTH }} />
                        {selectedExamLabels.map((label) => (
                          <col key={`exam-col-${label}`} style={{ width: EXAM_TABLE_SCORE_COL_WIDTH }} />
                        ))}
                      </colgroup>
                      <thead className="sticky top-0 z-20 bg-muted/40 text-[10px] font-bold uppercase tracking-wider text-muted-foreground shadow-[0_1px_0_hsl(var(--foreground)/0.08)]">
                        <tr>
                          <th
                            className="sticky left-0 z-30 border-r border-foreground/8 bg-muted/40 px-3 py-2"
                            style={{
                              width: EXAM_TABLE_STUDENT_COL_WIDTH,
                              minWidth: EXAM_TABLE_STUDENT_COL_WIDTH,
                              maxWidth: EXAM_TABLE_STUDENT_COL_WIDTH,
                            }}
                          >
                            Student
                          </th>
                          {selectedExamLabels.map((label) => (
                            <th
                              key={label}
                              className="border-l border-foreground/8 px-2 py-2 text-center leading-tight"
                              style={{
                                width: EXAM_TABLE_SCORE_COL_WIDTH,
                                minWidth: EXAM_TABLE_SCORE_COL_WIDTH,
                              }}
                            >
                              {label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-foreground/5 bg-surface">
                        {enrollments.map((en) => (
                          <tr key={`${en.enrollmentId}-exams`} className="transition-colors hover:bg-primary/[0.025]">
                            <td
                              className="sticky left-0 z-10 border-r border-foreground/8 bg-surface px-3 py-1.5 text-[12px] font-semibold leading-tight"
                              style={{
                                width: EXAM_TABLE_STUDENT_COL_WIDTH,
                                minWidth: EXAM_TABLE_STUDENT_COL_WIDTH,
                                maxWidth: EXAM_TABLE_STUDENT_COL_WIDTH,
                              }}
                            >
                              {en.fullName}
                            </td>
                            {selectedExamLabels.map((label) => {
                              const score = en.exams?.[label];
                              const displayScore = score !== undefined ? formatScoreOutOfNine(score) : "-";
                              const savingThisExam = examSavingKey === `${en.enrollmentId}:${label}`;
                              const editingThisExam =
                                activeExam?.enrollmentId === en.enrollmentId && activeExam.examLabel === label;
                              return (
                                <td
                                  key={`${en.enrollmentId}-${label}`}
                                  className="border-l border-foreground/5 px-2 py-1.5 text-center"
                                  style={{ width: EXAM_TABLE_SCORE_COL_WIDTH }}
                                >
                                  {editingThisExam ? (
                                    <input
                                      autoFocus
                                      type="number"
                                      min="1"
                                      max="9"
                                      step="0.5"
                                      value={examInput}
                                      onChange={(event) => setExamInput(event.target.value)}
                                      onBlur={() => void saveExamScore()}
                                      onKeyDown={(event) => {
                                        if (event.key === "Enter") {
                                          event.currentTarget.blur();
                                        }
                                        if (event.key === "Escape") {
                                          cancelExamEdit();
                                        }
                                      }}
                                      className="h-7 w-14 rounded-lg border border-blue-200 bg-background px-2 text-center text-[11px] font-bold text-blue-700 shadow-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
                                      aria-label={`Edit ${en.fullName} ${label} score`}
                                    />
                                  ) : (
                                    <button
                                      type="button"
                                      disabled={Boolean(examSavingKey)}
                                      onClick={() => openExamEditor(en, label)}
                                      className={`inline-flex h-7 min-w-8 items-center justify-center rounded-lg px-2 text-[11px] font-bold transition-[transform,opacity,box-shadow] hover:-translate-y-px hover:opacity-85 disabled:cursor-wait disabled:opacity-60 ${
                                        score !== undefined
                                          ? "bg-blue-50 text-blue-700 shadow-sm"
                                          : "text-foreground/25 hover:bg-muted"
                                      }`}
                                      title={`Edit ${en.fullName} · ${label}`}
                                    >
                                      {savingThisExam ? "..." : displayScore}
                                    </button>
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      )}

      {data && activeView === "timetable" && loadedView === "timetable" ? (
        <ModernGroupTimetable groupId={groupId} csrf={csrf} academicRoutes={academicRoutes} onChangeSchedule={openGroupSetup} />
      ) : null}

      <Modal open={setupOpen} onClose={closeGroupSetup} title={<span className="inline-flex items-center gap-2"><Settings className="h-5 w-5 text-primary" />Group Timetable</span>} subtitle="Set when and where this group studies." size="lg" mobileMode="sheet" closeOnOutsideClick={!setupSaving} closeOnEscape={!setupSaving} panelClassName="sm:h-auto">
        <form onSubmit={saveGroupSetup} className="flex min-h-0 flex-1 flex-col">
          <ModalBody className="space-y-5">
          {setupSuccess ? <p className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">{setupSuccess}</p> : null}
          {setupError ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{setupError}</p> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">School</span><input readOnly value={asString(data?.group.schoolCode)} className="h-10 w-full rounded-lg border border-foreground/10 bg-muted px-3 text-sm font-semibold text-muted-foreground" /></label>
          <label className="block"><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Teacher</span>
            <Select value={setupForm.teacherId} onChange={(event) => updateSetupField("teacherId", event.target.value)}>
              <option value="">No teacher yet</option>
              {teachers.map((teacher) => <option key={asNumber(teacher.id)} value={asString(teacher.id)}>{asString(teacher.full_name)}</option>)}
            </Select>
          </label>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label>
              <span className="mb-1 flex items-center justify-between gap-2 text-xs font-bold uppercase text-muted-foreground">
                Course Launch Date
                {hasExistingSchedule() ? <button type="button" onClick={toggleCourseLaunchDateChange} className="rounded-md px-2 py-1 text-[10px] font-bold normal-case text-primary hover:bg-primary/10">{setupForm.changeLaunchDate ? "Keep saved date" : "Change"}</button> : null}
              </span>
              <input type="date" required disabled={hasExistingSchedule() && !setupForm.changeLaunchDate} value={setupForm.startDate} onChange={(event) => updateSetupField("startDate", event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground" />
              {hasExistingSchedule() ? <span className="mt-1 block text-[11px] text-muted-foreground">Saved when the course was first launched. Changing lesson days or time does not require changing this date.</span> : null}
            </label>
            <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Lesson Time</span><input type="time" required value={setupForm.startTime} onChange={(event) => updateSetupField("startTime", event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
          </div>
          <fieldset><legend className="mb-1 text-xs font-bold uppercase text-muted-foreground">Lesson Days · {setupForm.weekdays.length} per week</legend><div className="grid grid-cols-7 gap-1">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label, day) => <button key={label} type="button" onClick={() => toggleSetupWeekday(day)} className={`h-10 rounded-lg text-[11px] font-bold ${setupForm.weekdays.includes(day) ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{label.slice(0, 2)}</button>)}</div></fieldset>
          <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Room</span><input value={setupForm.room} onChange={(event) => updateSetupField("room", event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" placeholder="Room 2" /></label>
          {hasExistingSchedule() ? (
            <fieldset className="space-y-2 rounded-lg border border-foreground/10 bg-muted/30 p-3">
              <legend className="px-1 text-xs font-bold uppercase text-muted-foreground">Apply this change to</legend>
              {[
                ["remaining", "Future unrecorded lessons", "Recommended · keeps completed lessons and their records unchanged."],
                ["from_date", "Lessons from a specific date", "Moves eligible lessons from the selected date."],
                ["all", "Entire timetable history", "Rebuilds every lesson date from the course launch."],
              ].map(([value, label, description]) => (
                <label key={value} className={`flex cursor-pointer items-start gap-2 rounded-lg border p-2.5 text-sm transition-colors ${setupForm.changeScope === value ? "border-primary/30 bg-background" : "border-transparent hover:bg-background/70"}`}>
                  <input type="radio" name="changeScope" checked={setupForm.changeScope === value} onChange={() => changeSetupScope(value)} className="mt-0.5 accent-primary" />
                  <span><span className="block font-bold">{label}</span><span className="mt-0.5 block text-[11px] font-normal text-muted-foreground">{description}</span></span>
                </label>
              ))}
              {setupForm.changeScope === "from_date" ? <label className="block px-2"><span className="mb-1 block text-xs font-bold text-muted-foreground">Effective from</span><input type="date" required value={setupForm.effectiveDate} onChange={(event) => updateSetupField("effectiveDate", event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label> : null}
              {setupForm.changeScope === "all" || setupForm.changeScope === "from_date" ? (
                <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-950">
                  <input type="checkbox" checked={setupForm.allowRecordedChanges} onChange={(event) => updateSetupField("allowRecordedChanges", event.target.checked)} className="mt-0.5 accent-amber-700" />
                  <span><span className="block text-xs font-bold">Allow completed lessons to move</span><span className="mt-0.5 block text-[11px] leading-4 text-amber-800">Attendance and homework stay attached to their lessons, but their displayed dates may change.</span></span>
                </label>
              ) : null}
            </fieldset>
          ) : null}
          </ModalBody>
          <ModalFooter className="flex justify-end gap-2">
            <button type="button" onClick={closeGroupSetup} disabled={setupSaving} className="min-h-11 rounded-lg bg-muted px-4 text-sm font-bold text-muted-foreground">Cancel</button>
            <button type="submit" disabled={setupSaving || !setupForm.startDate || !setupForm.startTime || setupForm.weekdays.length === 0 || (hasExistingSchedule() && !setupForm.changeScope) || (setupForm.changeScope === "all" && !setupForm.allowRecordedChanges)} className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground disabled:opacity-50">{setupSaving ? "Saving..." : "Save Timetable"}</button>
          </ModalFooter>
        </form>
      </Modal>

      <Modal open={studentOpen} onClose={() => !studentSaving && setStudentOpen(false)} title="Add Student" subtitle={`Register a student directly in ${asString(data?.group.name)}.`} size="sm" mobileMode="sheet" closeOnOutsideClick={!studentSaving} closeOnEscape={!studentSaving}>
        <form onSubmit={addStudent} className="flex min-h-0 flex-1 flex-col">
          <ModalBody className="space-y-4">
            {studentError ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{studentError}</p> : null}
            {createdStudent ? <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"><p className="font-bold">Student added</p><p className="mt-1 text-xs">Code: {asString(createdStudent.studentCode)}{asString(createdStudent.password) ? ` · Initial password: ${asString(createdStudent.password)}` : " · Existing account reused"}</p></div> : <label className="block"><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Full Name</span><input autoFocus required value={studentName} onChange={(event) => setStudentName(event.target.value)} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" placeholder="Student full name" /></label>}
          </ModalBody>
          <ModalFooter className="flex justify-end gap-2"><button type="button" onClick={() => setStudentOpen(false)} disabled={studentSaving} className="min-h-10 rounded-lg bg-muted px-4 text-sm font-bold text-muted-foreground">{createdStudent ? "Done" : "Cancel"}</button>{!createdStudent ? <button type="submit" disabled={studentSaving || !studentName.trim()} className="min-h-10 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground disabled:opacity-50">{studentSaving ? "Adding..." : "Add Student"}</button> : null}</ModalFooter>
        </form>
      </Modal>

      {selectedStudent ? (
        <div className="fixed inset-0 z-50 bg-foreground/45 animate-in fade-in duration-150 motion-reduce:animate-none" onClick={() => setSelectedStudent(null)} role="presentation">
          <aside
            className="ml-auto flex h-full w-full max-w-md flex-col bg-surface shadow-card-hover animate-in slide-in-from-right duration-200 motion-reduce:animate-none"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="student-actions-title"
          >
            <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-5 py-4">
              <div className="min-w-0">
                <p id="student-actions-title" className="truncate text-base font-bold">{selectedStudent.fullName}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {selectedStudent.publicDashboardId ? `Dashboard ID ${selectedStudent.publicDashboardId}` : `Enrollment ID ${selectedStudent.enrollmentId}`} · {selectedStudent.status === "banned" ? "Banned" : selectedStudent.status === "disqualified" ? "Disqualified" : "Active"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedStudent(null)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                aria-label="Close student actions"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
              <div className="grid grid-cols-3 gap-2">
                <MiniMetric icon={<BookMarked className="h-3.5 w-3.5" />} label="AAP" value={selectedStudent.averageGrade > 0 ? selectedStudent.averageGrade.toFixed(0) : "-"} />
                <MiniMetric icon={<BookMarked className="h-3.5 w-3.5" />} label="Exams" value={Object.keys(selectedStudent.exams || {}).length} />
                <MiniMetric icon={<Users className="h-3.5 w-3.5" />} label="Coins" value={selectedStudent.coins || 0} />
              </div>

              <div className="rounded-xl border border-foreground/8 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Student actions</p>
                <div className="mt-3 grid gap-2">
                  <button
                    type="button"
                    disabled={statusSavingId === selectedStudent.enrollmentId}
                    onClick={() => updateEnrollmentStatus(selectedStudent.enrollmentId, selectedStudent.status === "banned" ? "active" : "banned")}
                    className="inline-flex items-center justify-center rounded-lg border border-foreground/10 px-3 py-2 text-sm font-bold hover:bg-muted disabled:opacity-50"
                  >
                    {statusSavingId === selectedStudent.enrollmentId
                      ? "Saving..."
                      : selectedStudent.status === "banned"
                        ? "Unban student"
                        : "Ban student"}
                  </button>
                  <button
                    type="button"
                    disabled={statusSavingId === selectedStudent.enrollmentId}
                    onClick={() => updateEnrollmentStatus(selectedStudent.enrollmentId, selectedStudent.status === "disqualified" ? "active" : "disqualified")}
                    className={`inline-flex items-center justify-center rounded-lg px-3 py-2 text-sm font-bold disabled:opacity-50 ${
                      selectedStudent.status === "disqualified"
                        ? "bg-muted text-muted-foreground hover:bg-foreground/10"
                        : "bg-red-50 text-red-700 hover:bg-red-100"
                    }`}
                  >
                    {statusSavingId === selectedStudent.enrollmentId
                      ? "Saving..."
                      : selectedStudent.status === "disqualified"
                        ? "Restore qualification"
                        : "Disqualify"}
                  </button>
                </div>
              </div>

              <div className="rounded-xl border border-foreground/8 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Move to another group</p>
                <div className="mt-3 space-y-2">
                  <Select value={moveGroupId} onChange={(event) => setMoveGroupId(event.target.value)}>
                    <option value="">Choose target group</option>
                    {groups
                      .filter((group) => asNumber(group.id) !== groupId)
                      .map((group) => (
                        <option key={asNumber(group.id)} value={asString(group.id)}>
                          {asString(group.name)} · {asString(group.subject_name)} · {asString(group.school_code)}
                        </option>
                      ))}
                  </Select>
                  <button
                    type="button"
                    disabled={!moveGroupId || moveSaving}
                    onClick={() => moveEnrollment(selectedStudent.enrollmentId)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-bold text-primary-foreground disabled:opacity-50"
                  >
                    <Layers className="h-4 w-4" />
                    {moveSaving ? "Moving..." : "Move student"}
                  </button>
                </div>
              </div>
            </div>
          </aside>
        </div>
      ) : null}
      {active && (
        <div
          ref={popRef}
          style={{ position: "fixed", top: popTop, left: popLeft, zIndex: 9999 }}
          className="w-52 rounded-xl border border-foreground/10 bg-surface shadow-xl animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none"
        >
          <div className="flex items-center justify-between border-b border-foreground/8 px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-xs font-bold">{active.lesson.lessonNumber}</p>
              <p className="truncate text-[10px] text-muted-foreground">{active.lesson.topic}</p>
              {active.lesson.date && <p className="text-[10px] text-muted-foreground">{formatGradebookDate(active.lesson.date)}</p>}
            </div>
            <button type="button" onClick={close} className="ml-2 shrink-0 rounded p-0.5 hover:bg-muted">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
          <div className="p-3">
            {cellError ? <p role="alert" className="mb-2 rounded-lg border border-red-200 bg-red-50 px-2 py-1.5 text-[10px] font-semibold text-red-700">{cellError}</p> : null}
            {active.kind === "att" ? (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Attendance</p>
                <div className="grid grid-cols-4 gap-1">
                  {(["present", "absent", "justified", ""] as AttValue[]).map((v) => {
                    const lbl = v ? attLabel(v) : "–";
                    const cls = v ? attCls(v) : "bg-muted text-muted-foreground";
                    const currentEnrollment = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId);
                    const currentAtt = currentEnrollment?.attendanceByLessonId?.[String(active.lesson.id)] ?? currentEnrollment?.attendance[active.lesson.lessonNumber] ?? "";
                    return (
                      <button
                        key={v}
                        type="button"
                        disabled={saving}
                        onClick={() => saveAtt(v as AttValue)}
                        className={`inline-flex min-h-[40px] items-center justify-center rounded py-1.5 text-xs font-bold transition-opacity disabled:opacity-50 ${cls} ${currentAtt === v ? "ring-2 ring-foreground/30 ring-offset-1" : ""}`}
                      >
                        {lbl}
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Homework Score</p>
                {(() => {
                  const currentEnrollment = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId);
                  const curHw = currentEnrollment?.homeworkByLessonId?.[String(active.lesson.id)] ?? currentEnrollment?.homework[active.lesson.lessonNumber];
                  return curHw !== undefined ? (
                    <p className="text-[10px] text-muted-foreground">Current: <span className="font-bold text-foreground">{curHw}</span></p>
                  ) : null;
                })()}
                <div className="flex gap-2">
                  <input
                    autoFocus
                    type="number"
                    min="1"
                    max="9"
                    step="0.5"
                    value={hwInput}
                    onChange={(e) => setHwInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveHw()}
                    placeholder="1–9"
                    className="w-full rounded-lg border border-foreground/10 bg-background px-2 py-1.5 text-sm outline-none focus:border-foreground/30"
                  />
                  <button
                    type="button"
                    disabled={saving || hwInput === ""}
                    onClick={saveHw}
                    className="shrink-0 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground disabled:opacity-50"
                  >
                    Save
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
