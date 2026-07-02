import { Fragment, useState, useEffect, useRef } from "react";
import { BookMarked, ChevronLeft, Layers, UserX, Users, X } from "lucide-react";
import { BarChart, Bar, Cell, Legend, LabelList, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { routes } from "@/shared/lib/routes";
import { motion } from "@/shared/lib/motion";
import { asNumber, asString } from "../../shared";
import { attCls, attLabel, formatScoreOutOfNine, scoreOutOfNine } from "../gradebookFormat";
import { jsonCsrfHeaders } from "@/shared/lib/api";
import { GRADEBOOK_STUDENT_COL_WIDTH, GRADEBOOK_AAP_COL_WIDTH, GRADEBOOK_ATT_COL_WIDTH, GRADEBOOK_HW_COL_WIDTH, GRADEBOOK_LESSON_COL_WIDTH, EXAM_TABLE_STUDENT_COL_WIDTH, EXAM_TABLE_SCORE_COL_WIDTH, EXAM_TABLE_MIN_WIDTH, matchesPeriod, collectPeriodOptions, collectExamTypeOptions, averageScore, chartMinWidth, formatBarLabel, formatPercentLabel, StudentNameTick, Select, PeriodFilter, ExamTypeFilter, ExamViewSwitcher, MiniMetric, Lesson, Enrollment, GradebookData, ActiveCell, AttValue } from "./shared";

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
  const [riskPanelOpen, setRiskPanelOpen] = useState(false);
  const [moveGroupId, setMoveGroupId] = useState("");
  const [moveSaving, setMoveSaving] = useState(false);
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
    setRiskPanelOpen(false);
    setIndicatorMonth("all");
    setIndicatorYear("all");
    setExamType("all");
    setExamDisplay("chart");
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
      if (json.ok) setData(json as GradebookData);
      else setError(json.message || "Failed to load.");
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
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
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
      await fetch(routes.adminAcademicAttendanceApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_label: active.lesson.lessonNumber,
          status: status || "present",
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          attendance_type: "regular",
        }),
      });
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
    setSaving(true);
    try {
      await fetch(routes.adminAcademicHomeworkApi, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({
          enrollment_id: active.enrollmentId,
          lesson_label: active.lesson.lessonNumber,
          score,
          topic: active.lesson.topic,
          lesson_date: active.lesson.date,
          score_type: "Homework",
        }),
      });
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
      if (!res.ok || !json.ok) {
        setError(asString(json.message) || "Unable to update enrollment.");
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
      if (!res.ok || !json.ok) {
        setError(asString(json.message) || "Unable to move student.");
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
  const indicatorLessons = indicatorFilterActive
    ? lessons.filter((lesson) => matchesPeriod(lesson.date, indicatorMonth, indicatorYear))
    : lessons;
  const examTypeOptions = collectExamTypeOptions(examLabels);
  const selectedExamType = examType === "all" ? null : examTypeOptions.find((option) => option.key === examType) || null;
  const selectedExamTypeValue = selectedExamType ? selectedExamType.key : "all";
  const selectedExamLabels = selectedExamType ? selectedExamType.labels : examLabels;
  const examTableMinWidth = Math.max(
    EXAM_TABLE_MIN_WIDTH,
    EXAM_TABLE_STUDENT_COL_WIDTH + selectedExamLabels.length * EXAM_TABLE_SCORE_COL_WIDTH,
  );

  // 1. AAP Metrics
  const activeAAPGrades = enrollments.map(en => scoreOutOfNine(en.averageGrade)).filter(g => g > 0);
  const classAAPAverage = activeAAPGrades.length > 0
    ? (activeAAPGrades.reduce((sum, g) => sum + g, 0) / activeAAPGrades.length).toFixed(1)
    : "—";

  // 2. Attendance Metrics
  const totalPresent = enrollments.reduce((sum, en) => sum + Object.values(en.attendance).filter(v => v === "present").length, 0);
  const totalAtt = enrollments.reduce((sum, en) => sum + Object.values(en.attendance).filter(v => ["present", "absent", "justified"].includes(v)).length, 0);
  const classAttendanceRate = totalAtt > 0 ? Math.round((totalPresent / totalAtt) * 100) : 100;

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

  // 3. Exam Metrics
  let totalExamScoreSum = 0;
  let totalExamScoreCount = 0;
  enrollments.forEach(en => {
    if (en.exams) {
      Object.values(en.exams).forEach(score => {
        if (typeof score === "number") {
          const normalizedScore = scoreOutOfNine(score);
          if (normalizedScore <= 0) return;
          totalExamScoreSum += normalizedScore;
          totalExamScoreCount++;
        }
      });
    }
  });
  const classExamAverage = totalExamScoreCount > 0 ? (totalExamScoreSum / totalExamScoreCount).toFixed(1) : "—";
  const hasExamScores = totalExamScoreCount > 0;

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

  // 4. At-Risk Metrics
  const atRiskStudents = enrollments.map(en => {
    const present = Object.values(en.attendance).filter(v => v === "present").length;
    const total = Object.values(en.attendance).filter(v => ["present", "absent", "justified"].includes(v)).length;
    const attRate = total > 0 ? Math.round((present / total) * 100) : 100;
    const aap = scoreOutOfNine(en.averageGrade);
    const isLowAAP = aap > 0 && aap < 5;
    const isLowAtt = attRate < 80 && total > 0;
    const reasons = [
      isLowAAP ? `AAP ${formatScoreOutOfNine(aap)}` : "",
      isLowAtt ? `AR ${attRate}%` : "",
    ].filter(Boolean);
    return {
      enrollment: en,
      aap,
      arRate: attRate,
      reasons,
      atRisk: isLowAAP || isLowAtt,
    };
  }).filter((row) => row.atRisk);
  const atRiskCount = atRiskStudents.length;

  useEffect(() => {
    setActive(null);
  }, [activeView]);

  const popTop = active
    ? Math.min(active.anchorRect.bottom + 4, window.innerHeight - 200)
    : 0;
  const popLeft = active
    ? Math.min(active.anchorRect.left, window.innerWidth - 220)
    : 0;
  const summaryMetricClass = `rounded-xl border border-foreground/8 bg-surface p-3 shadow-card ${motion.card}`;
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

      {/* 2. Class Insights Cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className={summaryMetricClass}>
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Class Average AAP</span>
            <span className="mt-1 block text-lg font-bold">{classAAPAverage} <span className="text-xs font-normal text-muted-foreground">/ 9.0</span></span>
          </div>
          <div className={summaryMetricClass}>
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Attendance Rate</span>
            <span className="mt-1 block text-lg font-bold">{classAttendanceRate}%</span>
          </div>
          <div className={summaryMetricClass}>
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Exam Avg Score</span>
            <span className="mt-1 block text-lg font-bold">
              {classExamAverage}
              {hasExamScores ? <span className="text-xs font-normal text-muted-foreground"> / 9.0</span> : null}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setRiskPanelOpen(true)}
            className={`rounded-xl border border-foreground/8 bg-surface p-3 text-left shadow-card transition-colors hover:border-red-200 hover:bg-red-50/30 focus:outline-none focus:ring-2 focus:ring-red-200 ${motion.card}`}
            aria-label="Show at-risk students"
          >
            <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">At-Risk Students</span>
            <span className={`mt-1 block text-lg font-bold ${atRiskCount > 0 ? "text-red-500" : ""}`}>{atRiskCount}</span>
          </button>
        </div>
      )}

      {/* 3. View Switcher Buttons */}
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
          <div className="overflow-hidden rounded-xl border border-foreground/8 bg-surface">
            <div className="border-b border-foreground/8 px-4 py-3">
              <p className="text-sm font-bold">Gradebook</p>
              <p className="text-xs text-muted-foreground">Attendance and homework by lesson</p>
            </div>
            <div className="miniapp-table-scroll max-h-[72dvh] pb-3 [scrollbar-gutter:stable]">
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
                    <th rowSpan={2} className="sticky left-0 z-40 w-[180px] min-w-[180px] max-w-[180px] border-b border-r border-foreground/10 bg-surface px-3 py-2 font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                      Student
                    </th>
                    <th rowSpan={2} className="sticky left-[180px] z-40 w-[56px] min-w-[56px] max-w-[56px] border-b border-r border-foreground/10 bg-surface px-2 py-2 text-center font-bold uppercase tracking-wide text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                      AAP
                    </th>
                    {lessons.map((lesson) => (
                      <th key={lesson.id} colSpan={2} className="w-[84px] border-l border-foreground/10 p-0 text-center align-top">
                        <div
                          title={`${lesson.lessonNumber} - ${lesson.topic}`}
                          className="w-full px-2 py-2"
                        >
                          <span className="block whitespace-nowrap text-[10px] font-semibold leading-tight text-muted-foreground">
                            {lesson.date || lesson.lessonNumber}
                          </span>
                          <span className="block whitespace-nowrap text-[9px] font-semibold text-muted-foreground/70">
                            {lesson.lessonNumber}
                          </span>
                          <span className="mt-1 block whitespace-normal break-words text-[9px] font-normal italic leading-tight text-muted-foreground/70">
                            {lesson.topic || "—"}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                  <tr className="bg-surface">
                    {lessons.map((lesson) => (
                      <Fragment key={`gradebook-subhead-${lesson.id}`}>
                        <th className="w-[38px] border-b border-t border-l border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70">Att</th>
                        <th className="w-[46px] border-b border-t border-r border-foreground/10 px-0.5 py-1 text-center font-normal text-muted-foreground/70">HW</th>
                      </Fragment>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-foreground/5 bg-surface">
                  {enrollments.map((en) => (
                    <tr key={en.enrollmentId} className="hover:bg-foreground/[0.015]">
                      <td className="sticky left-0 z-20 w-[180px] min-w-[180px] max-w-[180px] border-r border-foreground/8 bg-surface px-3 py-1 font-semibold text-sm shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
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
                      <td className="sticky left-[180px] z-20 w-[56px] min-w-[56px] max-w-[56px] border-r border-foreground/8 bg-surface px-2 py-1 text-center font-bold text-muted-foreground shadow-[1px_0_0_hsl(var(--foreground)/0.08)]">
                        {en.averageGrade > 0 ? en.averageGrade.toFixed(0) : "–"}
                      </td>
                      {lessons.map((lesson) => {
                        const att = (en.attendance[lesson.lessonNumber] || "") as AttValue;
                        const hw = en.homework[lesson.lessonNumber];
                        const isActiveAtt = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "att";
                        const isActiveHw = active?.enrollmentId === en.enrollmentId && active?.lesson.id === lesson.id && active?.kind === "hw";
                        return (
                          <Fragment key={`${en.enrollmentId}-${lesson.id}`}>
                            <td className="w-[38px] border-l border-foreground/5 p-0 text-center">
                              <button
                                type="button"
                                onClick={(e) => openCell(e, en.enrollmentId, lesson, "att", hw)}
                                title={`${en.fullName} · ${lesson.lessonNumber} · attendance`}
                                className={`h-8 w-8 rounded text-[11px] font-bold transition-opacity hover:opacity-75 sm:h-[26px] sm:w-[30px] sm:text-[10px] ${att ? attCls(att) : "text-foreground/20"} ${isActiveAtt ? "ring-1 ring-foreground/40" : ""}`}
                              >
                                {att ? attLabel(att) : "·"}
                              </button>
                            </td>
                            <td className="w-[46px] border-r border-foreground/5 p-0 text-center">
                              <button
                                type="button"
                                onClick={(e) => openCell(e, en.enrollmentId, lesson, "hw", hw)}
                                title={`${en.fullName} · ${lesson.lessonNumber} · homework`}
                                className={`h-8 w-10 rounded text-[11px] transition-opacity hover:opacity-75 sm:h-[26px] sm:w-[38px] sm:text-[10px] ${hw !== undefined ? "font-bold text-blue-600" : "text-foreground/20"} ${isActiveHw ? "ring-1 ring-foreground/40" : ""}`}
                              >
                                {hw !== undefined ? hw : "·"}
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
          <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
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
            <div className={detailMetricClass}>
              <span className="block text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Lessons Matched</span>
              <span className="mt-1 block text-lg font-bold">{indicatorLessons.length}</span>
            </div>
          </div>
          {hasAcademicIndicatorData ? (
            <div className={`overflow-x-auto pb-1 ${motion.panel}`}>
              <div
                className="h-[410px] sm:h-[440px] lg:h-[460px]"
                style={{ minWidth: chartMinWidth(academicIndicatorData.length) }}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={academicIndicatorData} margin={{ top: 32, right: 18, left: -10, bottom: 52 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--foreground)/0.08)" />
                    <XAxis
                      dataKey="name"
                      interval={0}
                      height={70}
                      tick={<StudentNameTick />}
                      tickLine={false}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <YAxis domain={[0, 9]} tickCount={10} stroke="hsl(var(--muted-foreground))" />
                    <YAxis
                      yAxisId="ar"
                      orientation="right"
                      domain={[0, 100]}
                      tickCount={6}
                      tickFormatter={(value) => `${value}%`}
                      stroke="hsl(var(--muted-foreground))"
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: "var(--background)", borderColor: "hsl(var(--foreground)/0.08)", color: "hsl(var(--foreground))" }}
                      labelStyle={{ fontSize: 11, fontWeight: "bold" }}
                      formatter={(value, name) => {
                        const label = asString(name);
                        return [label === "AR" ? formatPercentLabel(value) : formatBarLabel(value), label];
                      }}
                    />
                    <Legend verticalAlign="top" height={28} />
                    <Bar
                      dataKey="AAP"
                      name="AAP"
                      fill="#3b82f6"
                      radius={[5, 5, 0, 0]}
                      maxBarSize={42}
                      isAnimationActive
                      animationDuration={650}
                      animationEasing="ease-out"
                    >
                      <LabelList dataKey="AAP" position="top" fontSize={12} fontWeight={700} fill="#2563eb" formatter={formatBarLabel} />
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
                      maxBarSize={42}
                      isAnimationActive
                      animationBegin={90}
                      animationDuration={650}
                      animationEasing="ease-out"
                    >
                      <LabelList dataKey="AR" position="top" fontSize={12} fontWeight={700} fill="#059669" formatter={formatPercentLabel} />
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
                    <div className={`overflow-x-auto pb-1 ${motion.panel}`}>
                      <div
                        className="h-[390px] sm:h-[420px] lg:h-[445px]"
                        style={{ minWidth: chartMinWidth(studentExamData.length) }}
                      >
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={studentExamData} margin={{ top: 32, right: 18, left: -10, bottom: 52 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--foreground)/0.08)" />
                            <XAxis
                              dataKey="name"
                              interval={0}
                              height={70}
                              tick={<StudentNameTick />}
                              tickLine={false}
                              stroke="hsl(var(--muted-foreground))"
                            />
                            <YAxis domain={[0, 9]} tickCount={10} stroke="hsl(var(--muted-foreground))" />
                            <Tooltip
                              contentStyle={{ backgroundColor: "var(--background)", borderColor: "hsl(var(--foreground)/0.08)", color: "hsl(var(--foreground))" }}
                              labelStyle={{ fontSize: 11, fontWeight: "bold" }}
                            />
                            <Bar
                              dataKey="chartScore"
                              fill="#3b82f6"
                              radius={[5, 5, 0, 0]}
                              name={selectedExamType ? `${selectedExamType.label} / 9` : "Best Score / 9"}
                              maxBarSize={48}
                              isAnimationActive
                              animationDuration={650}
                              animationEasing="ease-out"
                            >
                              <LabelList dataKey="chartScore" position="top" fontSize={12} fontWeight={700} fill="#1e2d4a" formatter={formatBarLabel} />
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
                    className="miniapp-table-scroll max-h-[min(64dvh,42rem)] min-h-0 w-full rounded-lg border border-foreground/8 [scrollbar-gutter:stable]"
                  >
                    <table
                      className="w-full table-fixed border-collapse text-left text-xs"
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
                          <th className="sticky left-0 z-30 w-[280px] min-w-[280px] max-w-[280px] border-r border-foreground/8 bg-muted/40 px-4 py-3">Student</th>
                          {selectedExamLabels.map((label) => (
                            <th key={label} className="w-[176px] min-w-[176px] border-l border-foreground/8 px-4 py-3 text-center">
                              {label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-foreground/5 bg-surface">
                        {enrollments.map((en) => (
                          <tr key={`${en.enrollmentId}-exams`} className="hover:bg-foreground/[0.015]">
                            <td className="sticky left-0 z-10 w-[280px] min-w-[280px] max-w-[280px] border-r border-foreground/8 bg-surface px-4 py-3 font-semibold">
                              {en.fullName}
                            </td>
                            {selectedExamLabels.map((label) => {
                              const score = en.exams?.[label];
                              const displayScore = score !== undefined ? formatScoreOutOfNine(score) : "-";
                              return (
                                <td key={`${en.enrollmentId}-${label}`} className="w-[176px] border-l border-foreground/5 px-4 py-3 text-center">
                                  <span className={`inline-flex min-w-8 justify-center rounded-md px-2 py-1 font-bold ${score !== undefined ? "bg-blue-50 text-blue-700" : "text-foreground/25"}`}>
                                    {displayScore}
                                  </span>
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

      {riskPanelOpen ? (
        <div className="fixed inset-0 z-50 bg-foreground/45 animate-in fade-in duration-150 motion-reduce:animate-none" onClick={() => setRiskPanelOpen(false)}>
          <aside
            className="ml-auto flex h-full w-full max-w-md flex-col bg-surface shadow-card-hover animate-in slide-in-from-right duration-200 motion-reduce:animate-none"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="At-risk students"
          >
            <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-5 py-4">
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-base font-bold">
                  <UserX className="h-4 w-4 text-red-500" />
                  At-Risk Students
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Students flagged by low AAP or attendance rate
                </p>
              </div>
              <button
                type="button"
                onClick={() => setRiskPanelOpen(false)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted"
                aria-label="Close at-risk students"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {atRiskStudents.length ? (
                <div className="space-y-2">
                  {atRiskStudents.map((row) => (
                    <button
                      key={row.enrollment.enrollmentId}
                      type="button"
                      onClick={() => {
                        setRiskPanelOpen(false);
                        setSelectedStudent(row.enrollment);
                        setMoveGroupId("");
                      }}
                      className={`w-full rounded-xl border border-foreground/8 bg-background p-3 text-left hover:border-red-200 hover:bg-red-50/40 focus:outline-none focus:ring-2 focus:ring-red-200 ${motion.card}`}
                    >
                      <span className="block break-words text-sm font-bold">{row.enrollment.fullName}</span>
                      <span className="mt-2 flex flex-wrap gap-1.5">
                        {row.reasons.map((reason) => (
                          <span key={reason} className="rounded-md bg-red-50 px-2 py-1 text-[11px] font-bold text-red-700">
                            {reason}
                          </span>
                        ))}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-foreground/8 bg-background px-4 py-8 text-center text-sm text-muted-foreground">
                  No students are currently marked at risk.
                </div>
              )}
            </div>
          </aside>
        </div>
      ) : null}

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
              {active.lesson.date && <p className="text-[10px] text-muted-foreground">{active.lesson.date}</p>}
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
                    min="0"
                    max="100"
                    step="0.5"
                    value={hwInput}
                    onChange={(e) => setHwInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveHw()}
                    placeholder="0–100"
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
