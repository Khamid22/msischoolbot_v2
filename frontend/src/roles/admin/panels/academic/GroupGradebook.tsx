import { Fragment, useState, useEffect, useRef } from "react";
import { BookMarked, CalendarDays, ChevronLeft, Layers, Users, X } from "lucide-react";
import { BarChart, Bar, Cell, Legend, LabelList, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { routes } from "@/shared/lib/routes";
import { motion } from "@/shared/lib/motion";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "../../shared";
import { attCls, attLabel, formatScoreOutOfNine, scoreOutOfNine } from "../gradebookFormat";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";
import { GRADEBOOK_STUDENT_COL_WIDTH, GRADEBOOK_AAP_COL_WIDTH, GRADEBOOK_ATT_COL_WIDTH, GRADEBOOK_HW_COL_WIDTH, GRADEBOOK_LESSON_COL_WIDTH, EXAM_TABLE_STUDENT_COL_WIDTH, EXAM_TABLE_SCORE_COL_WIDTH, EXAM_TABLE_MIN_WIDTH, matchesPeriod, collectPeriodOptions, collectExamTypeOptions, averageScore, formatBarLabel, formatPercentLabel, StudentNameTick, Select, PeriodFilter, ExamTypeFilter, ExamViewSwitcher, MiniMetric, Lesson, Enrollment, GradebookData, ActiveCell, AttValue } from "./shared";

type CompactTooltipItem = {
  value?: unknown;
  dataKey?: unknown;
  color?: string;
};

type ActiveExamCell = {
  enrollmentId: number;
  examLabel: string;
  attempt: string;
};

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
    </div>
  );
}

export function GroupGradebook({
  groupId,
  csrf,
  groups,
  onClose,
}: {
  groupId: number;
  csrf: string;
  groups: Array<Record<string, unknown>>;
  onClose: () => void;
}) {
  const [data, setData] = useState<GradebookData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [active, setActive] = useState<ActiveCell | null>(null);
  const [hwInput, setHwInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [statusSavingId, setStatusSavingId] = useState<number | null>(null);
  const [selectedStudent, setSelectedStudent] = useState<Enrollment | null>(null);
  useDismissibleLayer({
    enabled: Boolean(selectedStudent),
    onDismiss: () => setSelectedStudent(null),
    dismissOnOutsidePointer: false,
  });
  const [moveGroupId, setMoveGroupId] = useState("");
  const [moveSaving, setMoveSaving] = useState(false);
  const [lessonDateSavingId, setLessonDateSavingId] = useState<number | null>(null);
  const [activeExam, setActiveExam] = useState<ActiveExamCell | null>(null);
  const [examInput, setExamInput] = useState("");
  const [examSavingKey, setExamSavingKey] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<"gradebook" | "academic" | "ep">("gradebook");
  const [indicatorMonth, setIndicatorMonth] = useState("all");
  const [indicatorYear, setIndicatorYear] = useState("all");
  const [examType, setExamType] = useState("all");
  const [examDisplay, setExamDisplay] = useState<"chart" | "table">("chart");
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    load(groupId, controller.signal);
    return () => controller.abort();
  }, [groupId]);

  useEffect(() => {
    setActiveView("gradebook");
    setSelectedStudent(null);
    setIndicatorMonth("all");
    setIndicatorYear("all");
    setExamType("all");
    setExamDisplay("chart");
    setActiveExam(null);
    setExamInput("");
  }, [groupId]);

  useEffect(() => {
    if (!active) return;
    const handler = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) close();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [active]);

  async function load(id: number, signal?: AbortSignal) {
    setLoading(true);
    setError("");
    setActive(null);
    try {
      const res = await fetch(routes.adminAcademicGradebookApi(id), { signal });
      const json = await res.json();
      if (apiSucceeded(res, json)) setData(apiData<GradebookData>(json));
      else setError(apiErrorMessage(json, "Failed to load."));
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError("Network error.");
    } finally {
      setLoading(false);
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
    setActive({ enrollmentId, lesson, kind, anchorRect: rect });
    setHwInput(currentHw !== undefined ? String(currentHw) : "");
  }

  function close() {
    setActive(null);
    setSaving(false);
  }

  async function saveAtt(status: AttValue) {
    if (!active || saving) return;
    setSaving(true);
    try {
      const res = await fetch(routes.adminAcademicAttendanceApi, {
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
        setError(apiErrorMessage(json, "Unable to update attendance."));
        return;
      }
      patchAtt(active.enrollmentId, active.lesson.lessonNumber, status);
      close();
    } finally {
      setSaving(false);
    }
  }

  async function saveHw() {
    if (!active || saving || hwInput === "") return;
    const score = parseFloat(hwInput);
    if (isNaN(score)) return;
    if (score < 1 || score > 9) {
      setError("Homework score must be between 1 and 9.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await fetch(routes.adminAcademicHomeworkApi, {
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
        setError(apiErrorMessage(json, "Unable to update homework score."));
        return;
      }
      patchHw(active.enrollmentId, active.lesson.lessonNumber, score);
      close();
    } finally {
      setSaving(false);
    }
  }

  function patchAtt(enrollmentId: number, lessonNumber: string, status: AttValue) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) => {
          if (en.enrollmentId !== enrollmentId) return en;
          const att = { ...en.attendance };
          if (status) att[lessonNumber] = status;
          else delete att[lessonNumber];
          return { ...en, attendance: att };
        }),
      };
    });
  }

  function patchHw(enrollmentId: number, lessonNumber: string, score: number) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        enrollments: prev.enrollments.map((en) =>
          en.enrollmentId !== enrollmentId
            ? en
            : { ...en, homework: { ...en.homework, [lessonNumber]: score } },
        ),
      };
    });
  }

  function patchExam(enrollmentId: number, examLabel: string, score: number) {
    setData((prev) => {
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
    });
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
      const res = await fetch(routes.adminAcademicExamApi, {
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
      const res = await fetch(routes.adminAcademicEnrollmentStatusApi(enrollmentId), {
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
      await load(groupId);
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
      const res = await fetch(routes.adminAcademicEnrollmentGroupApi(enrollmentId), {
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
      await load(groupId);
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

  async function editLessonDate(lesson: Lesson) {
    if (lessonDateSavingId) return;
    const current = lessonDateToInputValue(lesson.date);
    const next = window.prompt("Conducted date (YYYY-MM-DD). Leave empty to clear.", current);
    if (next === null) return;
    const trimmed = next.trim();
    if (trimmed && !/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      setError("Use YYYY-MM-DD for lesson dates.");
      return;
    }
    setLessonDateSavingId(lesson.id);
    setError("");
    try {
      const res = await fetch(routes.adminAcademicLessonApi(lesson.id), {
        method: "PATCH",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ lesson_date: trimmed }),
      });
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setError(apiErrorMessage(json, "Unable to update lesson date."));
        return;
      }
      const updated = apiData<{ lesson?: Partial<Lesson> }>(json).lesson || {};
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          lessons: prev.lessons.map((item) =>
            item.id === lesson.id
              ? {
                  ...item,
                  date: asString(updated.date),
                  status: asString(updated.status) || item.status,
                }
              : item,
          ),
        };
      });
    } catch {
      setError("Network error while updating the lesson date.");
    } finally {
      setLessonDateSavingId(null);
    }
  }

  const lessons = data?.lessons ?? [];
  const examLabels = data?.examLabels ?? [];
  const enrollments = data?.enrollments ?? [];
  const allEnrollments = data?.allEnrollments ?? enrollments;
  const gradebookTableWidth =
    GRADEBOOK_STUDENT_COL_WIDTH +
    GRADEBOOK_AAP_COL_WIDTH +
    lessons.length * GRADEBOOK_LESSON_COL_WIDTH;
  const disqualifiedEnrollments = allEnrollments.filter((en) => en.status === "disqualified");
  const bannedEnrollments = allEnrollments.filter((en) => en.status === "banned");

  const academicPeriodOptions = collectPeriodOptions(lessons.map((lesson) => lesson.date));
  const indicatorFilterActive = indicatorMonth !== "all" || indicatorYear !== "all";
  const metricLessons = lessons.filter((lesson) => !isCancelledLesson(lesson));
  const indicatorLessons = indicatorFilterActive
    ? metricLessons.filter((lesson) => matchesPeriod(lesson.date, indicatorMonth, indicatorYear))
    : metricLessons;
  const examTypeOptions = collectExamTypeOptions(examLabels);
  const selectedExamType = examType === "all" ? null : examTypeOptions.find((option) => option.key === examType) || null;
  const selectedExamTypeValue = selectedExamType ? selectedExamType.key : "all";
  const selectedExamLabels = selectedExamType ? selectedExamType.labels : examLabels;
  const examTableMinWidth = Math.max(
    EXAM_TABLE_MIN_WIDTH,
    EXAM_TABLE_STUDENT_COL_WIDTH + selectedExamLabels.length * EXAM_TABLE_SCORE_COL_WIDTH,
  );

  const academicIndicatorData = enrollments.map(en => {
    const homeworkScores = indicatorLessons
      .map((lesson) => scoreOutOfNine(en.homework[lesson.lessonNumber]))
      .filter((score) => score > 0);
    const filteredAAP = averageScore(homeworkScores);
    const aap = filteredAAP ?? (indicatorFilterActive ? null : scoreOutOfNine(en.averageGrade) || null);
    const attendanceValues = indicatorLessons
      .map((lesson) => en.attendance[lesson.lessonNumber])
      .filter((status) => ["present", "absent", "justified"].includes(status));
    const present = attendanceValues.filter((status) => status === "present").length;
    const total = attendanceValues.length;
    const arRate = total > 0 ? Math.round((present / total) * 100) : null;
    const arScore = arRate === null ? null : Math.round((arRate / 100) * 90) / 10;
    const averagePerformance = averageScore([aap, arScore]);
    return {
      name: en.fullName,
      AAP: aap,
      AR: arRate,
      arScore,
      averagePerformance,
      isLowAAP: aap !== null && aap < 5,
      isLowAR: arRate !== null && arRate < 80,
      present,
      total,
    };
  });
  const hasAcademicIndicatorData = academicIndicatorData.some((row) => row.AAP !== null || row.AR !== null);
  const academicAverageAAP = averageScore(academicIndicatorData.map((row) => row.AAP));
  const academicAverageAR = averageScore(academicIndicatorData.map((row) => row.AR));
  const academicAveragePerformance = averageScore(academicIndicatorData.map((row) => row.averagePerformance));

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
  const chartPanelClass = `rounded-lg border border-foreground/8 bg-background/80 p-3 shadow-sm ${motion.panel}`;
  return (
    <div className={`space-y-3 ${motion.panel}`}>
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
              {enrollments.length} active · {disqualifiedEnrollments.length} disqualified · {bannedEnrollments.length} banned · {lessons.length} lessons · {examLabels.length} exams
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
      ) : loading ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">Loading…</div>
      ) : null}

      {/* 2. View Switcher Buttons */}
      {data && (
        <div className="flex border-b border-foreground/8 gap-2 overflow-x-auto py-1">
          {(["gradebook", "academic", "ep"] as const).map((view) => {
            const labels: Record<string, string> = {
              gradebook: "Gradebook",
              academic: "Academic Indicators",
              ep: "Exam Performance",
            };
            const isActive = activeView === view;
            return (
              <button
                key={view}
                type="button"
                onClick={() => setActiveView(view)}
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
      {data && activeView === "gradebook" && (
        lessons.length === 0 ? (
          <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">
            No lessons found for this group.
          </div>
        ) : (
          <div
            className={`flex min-h-0 flex-col overflow-hidden rounded-xl border border-foreground/8 bg-surface shadow-card ${motion.panel}`}
            style={{
              height: "calc(var(--tg-app-height) - 11rem)",
              maxHeight: "78dvh",
              minHeight: "26rem",
            }}
          >
            <div className="shrink-0 border-b border-foreground/8 px-4 py-3">
              <p className="text-sm font-bold">Gradebook</p>
              <p className="text-xs text-muted-foreground">Curriculum lessons with attendance and homework</p>
            </div>
            <div className="miniapp-table-scroll min-h-0 flex-1 pb-8 [scrollbar-gutter:stable]">
              <table
                className="table-fixed border-collapse text-left text-[11px] sm:text-xs"
                style={{ width: gradebookTableWidth, minWidth: gradebookTableWidth }}
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
                    <th
                      className="sticky left-0 z-40 border-b border-r border-foreground/10 bg-surface px-3 py-3 font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]"
                      style={{
                        width: GRADEBOOK_STUDENT_COL_WIDTH,
                        minWidth: GRADEBOOK_STUDENT_COL_WIDTH,
                        maxWidth: GRADEBOOK_STUDENT_COL_WIDTH,
                      }}
                    >
                      Student
                    </th>
                    <th
                      className="sticky z-40 border-b border-r border-foreground/10 bg-surface px-2 py-3 text-center font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]"
                      style={{
                        left: GRADEBOOK_STUDENT_COL_WIDTH,
                        width: GRADEBOOK_AAP_COL_WIDTH,
                        minWidth: GRADEBOOK_AAP_COL_WIDTH,
                        maxWidth: GRADEBOOK_AAP_COL_WIDTH,
                      }}
                    >
                      AAP
                    </th>
                    {lessons.map((lesson) => (
                      <th
                        key={lesson.id}
                        colSpan={2}
                        className={`border-b border-l p-0 text-center align-top ${isCancelledLesson(lesson) ? "border-red-200 bg-red-50/55" : "border-foreground/10 bg-surface"}`}
                        style={{
                          width: GRADEBOOK_LESSON_COL_WIDTH,
                          minWidth: GRADEBOOK_LESSON_COL_WIDTH,
                          maxWidth: GRADEBOOK_LESSON_COL_WIDTH,
                        }}
                      >
                        <div
                          title={`${lesson.lessonNumber} - ${lesson.topic}`}
                          className="flex min-h-[6.25rem] w-full flex-col items-center justify-start px-2.5 py-2"
                        >
                          <button
                            type="button"
                            disabled={lessonDateSavingId === lesson.id}
                            onClick={() => editLessonDate(lesson)}
                            className={`inline-flex max-w-full items-center justify-center gap-1 rounded-md border border-transparent px-1.5 py-0.5 text-[10px] font-bold leading-tight transition-colors hover:border-foreground/10 hover:bg-foreground/5 disabled:opacity-60 ${
                              isCancelledLesson(lesson) ? "text-red-700" : "text-muted-foreground"
                            }`}
                            title="Change conducted lesson date"
                          >
                            <CalendarDays className="h-2.5 w-2.5 shrink-0" />
                            <span className="whitespace-nowrap">
                              {lessonDateSavingId === lesson.id ? "Saving..." : formatGradebookDate(lesson.date) || "Set date"}
                            </span>
                          </button>
                          <span className={`mt-1 block whitespace-nowrap text-[9px] font-semibold ${isCancelledLesson(lesson) ? "text-red-700" : "text-muted-foreground/75"}`}>
                            {lesson.lessonNumber}
                          </span>
                          <span className={`mt-1 block w-full whitespace-normal break-words text-center text-[9px] font-medium italic leading-[1.15] ${isCancelledLesson(lesson) ? "text-red-700/80" : "text-muted-foreground/70"}`}>
                            {lesson.topic || "—"}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-foreground/5 bg-surface">
                  {enrollments.map((en) => (
                    <tr key={en.enrollmentId} className="transition-colors hover:bg-primary/[0.025]">
                      <td
                        className="sticky left-0 z-20 border-r border-foreground/8 bg-surface px-3 py-1.5 font-semibold text-sm shadow-[1px_0_0_hsl(var(--foreground)/0.08)]"
                        style={{
                          width: GRADEBOOK_STUDENT_COL_WIDTH,
                          minWidth: GRADEBOOK_STUDENT_COL_WIDTH,
                          maxWidth: GRADEBOOK_STUDENT_COL_WIDTH,
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedStudent(en);
                            setMoveGroupId("");
                          }}
                          className="w-full break-words text-left font-semibold text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary/20"
                          title={`Manage ${en.fullName}`}
                        >
                          {en.fullName}
                        </button>
                      </td>
                      <td
                        className="sticky z-20 border-r border-foreground/8 bg-surface px-2 py-1.5 text-center font-bold text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]"
                        style={{
                          left: GRADEBOOK_STUDENT_COL_WIDTH,
                          width: GRADEBOOK_AAP_COL_WIDTH,
                          minWidth: GRADEBOOK_AAP_COL_WIDTH,
                          maxWidth: GRADEBOOK_AAP_COL_WIDTH,
                        }}
                      >
                        {en.averageGrade > 0 ? en.averageGrade.toFixed(0) : "–"}
                      </td>
                      {lessons.map((lesson) => {
                        const att = (en.attendance[lesson.lessonNumber] || "") as AttValue;
                        const hw = en.homework[lesson.lessonNumber];
                        const cancelled = isCancelledLesson(lesson);
                        const canEditHomework = lessonCanHaveHomework(lesson);
                        const isActiveAtt = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "att";
                        const isActiveHw = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "hw";
                        if (cancelled) {
                          return (
                            <td
                              key={`${en.enrollmentId}-${lesson.id}-cancelled`}
                              colSpan={2}
                              className="border-l border-r border-red-100 bg-red-50/40 px-1.5 py-1.5 text-center"
                              style={{ width: GRADEBOOK_LESSON_COL_WIDTH }}
                            >
                              <span className="inline-flex max-w-full rounded-md bg-red-100 px-1.5 py-1 text-[9px] font-bold uppercase tracking-wide text-red-700 shadow-sm">
                                Cancelled
                              </span>
                            </td>
                          );
                        }
                        return (
                          <Fragment key={`${en.enrollmentId}-${lesson.id}`}>
                            <td className="border-l border-foreground/5 p-0.5 text-center" style={{ width: GRADEBOOK_ATT_COL_WIDTH }}>
                              <button
                                type="button"
                                onClick={(e) => openCell(e, en.enrollmentId, lesson, "att", hw)}
                                title={`${en.fullName} · ${lesson.lessonNumber} · attendance`}
                                className={`mx-auto flex h-8 w-9 items-center justify-center rounded-lg text-[11px] font-bold shadow-sm transition-[transform,opacity,box-shadow] hover:-translate-y-px hover:opacity-85 sm:h-7 sm:w-9 sm:text-[10px] ${att ? attCls(att) : "text-foreground/20 shadow-none"} ${isActiveAtt ? "ring-2 ring-primary/35 ring-offset-1" : ""}`}
                              >
                                {att ? attLabel(att) : "·"}
                              </button>
                            </td>
                            <td className="border-r border-foreground/5 p-0.5 text-center" style={{ width: GRADEBOOK_HW_COL_WIDTH }}>
                              <button
                                type="button"
                                disabled={!canEditHomework}
                                onClick={(e) => openCell(e, en.enrollmentId, lesson, "hw", hw)}
                                title={`${en.fullName} · ${lesson.lessonNumber} · homework`}
                                className={`mx-auto flex h-8 min-w-10 items-center justify-center rounded-lg px-2 text-[11px] transition-[transform,opacity,box-shadow] hover:-translate-y-px hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 sm:h-7 sm:min-w-10 sm:text-[10px] ${hw !== undefined ? "bg-blue-50 font-bold text-blue-700 shadow-sm" : "text-foreground/20"} ${isActiveHw ? "ring-2 ring-primary/35 ring-offset-1" : ""}`}
                              >
                                {canEditHomework && hw !== undefined ? hw : "·"}
                              </button>
                            </td>
                          </Fragment>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}

      {data && activeView === "academic" && (
        <div className={`${panelCardClass} p-4`}>
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h4 className="text-sm font-bold">Academic Indicators</h4>
              <p className="text-xs text-muted-foreground">AAP score and AR percentage by student</p>
            </div>
            <PeriodFilter
              month={indicatorMonth}
              year={indicatorYear}
              months={academicPeriodOptions.months}
              years={academicPeriodOptions.years}
              onMonthChange={setIndicatorMonth}
              onYearChange={setIndicatorYear}
            />
          </div>
          <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className={detailMetricClass}>
              <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Avg AAP</span>
              <span className="mt-1 block text-lg font-bold text-blue-600">{academicAverageAAP ?? "—"}</span>
            </div>
            <div className={detailMetricClass}>
              <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Avg AR</span>
              <span className="mt-1 block text-lg font-bold text-emerald-600">
                {academicAverageAR ?? "—"}<span className="text-xs font-normal text-muted-foreground">%</span>
              </span>
            </div>
            <div className={detailMetricClass}>
              <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Avg Performance</span>
              <span className="mt-1 block text-lg font-bold">{academicAveragePerformance ?? "—"} <span className="text-xs font-normal text-muted-foreground">/ 9</span></span>
            </div>
          </div>
          {hasAcademicIndicatorData ? (
            <div className={`overflow-hidden pb-1 ${motion.panel}`}>
              <div className="h-[calc(var(--tg-app-height)-24rem)] min-h-[500px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={academicIndicatorData}
                    barCategoryGap="18%"
                    barGap={3}
                    margin={{ top: 30, right: 10, left: 4, bottom: 44 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--foreground)/0.08)" />
                    <XAxis
                      dataKey="name"
                      interval={0}
                      height={58}
                      tick={<StudentNameTick />}
                      tickLine={false}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <YAxis domain={[0, 9]} tickCount={10} hide />
                    <YAxis
                      yAxisId="ar"
                      orientation="right"
                      domain={[0, 100]}
                      tickCount={6}
                      hide
                    />
                    <Tooltip
                      cursor={{ fill: "hsl(var(--primary) / 0.06)" }}
                      wrapperClassName="!outline-none"
                      content={<CompactChartTooltip percentKeys={["AR"]} />}
                    />
                    <Legend verticalAlign="top" height={28} />
                    <Bar
                      dataKey="AAP"
                      name="AAP"
                      fill="#3b82f6"
                      radius={[5, 5, 0, 0]}
                      maxBarSize={28}
                      isAnimationActive
                      animationDuration={650}
                      animationEasing="ease-out"
                    >
                      <LabelList dataKey="AAP" position="top" fontSize={11} fontWeight={700} fill="#2563eb" formatter={formatBarLabel} />
                      {academicIndicatorData.map((entry, index) => (
                        <Cell key={`academic-aap-${index}`} fill={entry.isLowAAP ? "#ef4444" : "#3b82f6"} />
                      ))}
                    </Bar>
                    <Bar
                      yAxisId="ar"
                      dataKey="AR"
                      name="AR"
                      fill="#10b981"
                      radius={[5, 5, 0, 0]}
                      maxBarSize={28}
                      isAnimationActive
                      animationBegin={90}
                      animationDuration={650}
                      animationEasing="ease-out"
                    >
                      <LabelList dataKey="AR" position="top" fontSize={11} fontWeight={700} fill="#059669" formatter={formatPercentLabel} />
                      {academicIndicatorData.map((entry, index) => (
                        <Cell key={`academic-ar-${index}`} fill={entry.isLowAR ? "#f59e0b" : "#10b981"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-sm text-muted-foreground">
              No academic indicator data matches this filter.
            </div>
          )}
        </div>
      )}

      {data && activeView === "ep" && (
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
                    <div className={`overflow-hidden pb-1 ${motion.panel}`}>
                      <div className="h-[calc(var(--tg-app-height)-30rem)] min-h-[500px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={studentExamData}
                            barCategoryGap="34%"
                            margin={{ top: 30, right: 10, left: 4, bottom: 44 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--foreground)/0.08)" />
                            <XAxis
                              dataKey="name"
                              interval={0}
                              height={58}
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
                              fill="#3b82f6"
                              radius={[5, 5, 0, 0]}
                              name="Score"
                              maxBarSize={34}
                              isAnimationActive
                              animationDuration={650}
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

      {selectedStudent ? (
        <div className="fixed inset-0 z-50 bg-foreground/45 animate-in fade-in duration-150 motion-reduce:animate-none" onClick={() => setSelectedStudent(null)}>
          <aside
            className="ml-auto flex h-full w-full max-w-md flex-col bg-surface shadow-card-hover animate-in slide-in-from-right duration-200 motion-reduce:animate-none"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-5 py-4">
              <div className="min-w-0">
                <p className="truncate text-base font-bold">{selectedStudent.fullName}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {selectedStudent.publicDashboardId ? `Dashboard ID ${selectedStudent.publicDashboardId}` : `Enrollment ID ${selectedStudent.enrollmentId}`} · {selectedStudent.status === "banned" ? "Banned" : selectedStudent.status === "disqualified" ? "Disqualified" : "Active"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedStudent(null)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted"
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
            {active.kind === "att" ? (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Attendance</p>
                <div className="grid grid-cols-4 gap-1">
                  {(["present", "absent", "justified", ""] as AttValue[]).map((v) => {
                    const lbl = v ? attLabel(v) : "–";
                    const cls = v ? attCls(v) : "bg-muted text-muted-foreground";
                    const currentAtt = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId)?.attendance[active.lesson.lessonNumber] ?? "";
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
                  const curHw = data?.enrollments.find((e) => e.enrollmentId === active.enrollmentId)?.homework[active.lesson.lessonNumber];
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
