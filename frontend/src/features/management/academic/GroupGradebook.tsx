import { Fragment, useState, useEffect, useMemo, useRef } from "react";
import { AlertTriangle, BookMarked, CalendarDays, ChevronLeft, ChevronRight, Layers, Pencil, Plus, RotateCcw, Search, Settings, Users, X } from "lucide-react";
import { BarChart, Bar, Cell, Legend, LabelList, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { routes } from "@/shared/lib/routes";
import { motion } from "@/shared/lib/motion";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "@/features/managementTypes";
import { attCls, attLabel, formatScoreOutOfNine, scoreOutOfNine } from "../gradebookFormat";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";
import { GRADEBOOK_STUDENT_COL_WIDTH, GRADEBOOK_AAP_COL_WIDTH, GRADEBOOK_ATT_COL_WIDTH, GRADEBOOK_HW_COL_WIDTH, GRADEBOOK_LESSON_COL_WIDTH, EXAM_TABLE_STUDENT_COL_WIDTH, EXAM_TABLE_SCORE_COL_WIDTH, EXAM_TABLE_MIN_WIDTH, matchesPeriod, collectPeriodOptions, collectExamTypeOptions, averageScore, formatBarLabel, formatPercentLabel, StudentNameTick, Select, PeriodFilter, ExamTypeFilter, ExamViewSwitcher, MiniMetric, Lesson, Enrollment, GradebookData, ActiveCell, AttValue } from "./shared";
import { TimetableCard, TimePopover, RoomPopover, TimetableDateGroup } from "./Timetable";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { lessonDurationMinutesForSchoolCode } from "./scheduleMath";

type AcademicGradebookRoutes = Pick<
  typeof routes,
  | "adminAcademicGradebookApi"
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
>;

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

type GradebookView = "gradebook" | "academic" | "ep" | "timetable";
type GradebookLoadOptions = { view?: GradebookView; cursor?: string; anchorDate?: string; force?: boolean };

const GRADEBOOK_LESSON_WINDOW = 12;

function gradebookSection(view: GradebookView) {
  return view === "ep" ? "exams" : view;
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
  const [lessonCursor, setLessonCursor] = useState("");
  const [lessonJumpInput, setLessonJumpInput] = useState("");
  const [lessonDateInput, setLessonDateInput] = useState("");
  const [setupOpen, setSetupOpen] = useState(false);
  const [setupSaving, setSetupSaving] = useState(false);
  const [setupSuccess, setSetupSuccess] = useState("");
  const [setupError, setSetupError] = useState("");
  const [setupForm, setSetupForm] = useState({
    teacherId: "", startDate: "", weekdays: [0, 2], startTime: "14:00",
    room: "", changeScope: "", effectiveDate: "",
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
  const [indicatorMonth, setIndicatorMonth] = useState("all");
  const [indicatorYear, setIndicatorYear] = useState("all");
  const [examType, setExamType] = useState("all");
  const [examDisplay, setExamDisplay] = useState<"chart" | "table">("chart");
  const popRef = useRef<HTMLDivElement>(null);
  const [scheduleEdit, setScheduleEdit] = useState<{ lesson: Lesson; kind: "time" | "room"; anchorRect: DOMRect } | null>(null);
  const [timeStartInput, setTimeStartInput] = useState("");
  const [timeEndInput, setTimeEndInput] = useState("");
  const [roomInput, setRoomInput] = useState("");
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const schedulePopRef = useRef<HTMLDivElement>(null);
  const [lessonAction, setLessonAction] = useState<{ kind: "edit" | "cancel" | "recover"; lesson: Lesson } | null>(null);
  const [lessonActionSaving, setLessonActionSaving] = useState(false);
  const [lessonActionError, setLessonActionError] = useState("");
  const [lessonNameInput, setLessonNameInput] = useState("");
  const [lessonTopicInput, setLessonTopicInput] = useState("");
  const [cancellationReason, setCancellationReason] = useState("");
  const gradebookCacheRef = useRef(new Map<string, GradebookData>());
  const loadRequestRef = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    load(groupId, controller.signal, { view: "gradebook", cursor: "", force: true });
    return () => controller.abort();
  }, [groupId]);

  useEffect(() => {
    setActiveView("gradebook");
    setLoadedView("gradebook");
    setData(null);
    setSelectedStudent(null);
    setIndicatorMonth("all");
    setIndicatorYear("all");
    setExamType("all");
    setExamDisplay("chart");
    setActiveExam(null);
    setExamInput("");
    setScheduleEdit(null);
    setLessonAction(null);
    setLessonCursor("");
    setLessonJumpInput("");
    setLessonDateInput("");
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

  useEffect(() => {
    if (!scheduleEdit) return;
    const handler = (e: MouseEvent) => {
      // Don't let a stray outside click drop an in-flight save silently.
      if (scheduleSaving) return;
      if (schedulePopRef.current && !schedulePopRef.current.contains(e.target as Node)) closeScheduleEdit();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [scheduleEdit, scheduleSaving]);

  async function fetchGradebookData(id: number, view: GradebookView, cursor = "", anchorDate = "", signal?: AbortSignal) {
    const section = gradebookSection(view);
    const response = await fetch(academicRoutes.adminAcademicGradebookApi(id, {
      lessonLimit: section === "gradebook" ? GRADEBOOK_LESSON_WINDOW : undefined,
      cursor: section === "gradebook" ? cursor : undefined,
      anchorDate: section === "gradebook" ? anchorDate : undefined,
      section,
    }), { signal });
    const json = await response.json();
    if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Failed to load."));
    return apiData<GradebookData>(json);
  }

  async function load(id: number, signal?: AbortSignal, options: GradebookLoadOptions = {}) {
    const view = options.view ?? activeView;
    const cursor = options.cursor ?? (view === "gradebook" ? lessonCursor : "");
    const anchorDate = options.anchorDate ?? "";
    const cacheKey = `${id}:${view}:${cursor || `anchor:${anchorDate || "today"}`}`;
    const cached = options.force ? undefined : gradebookCacheRef.current.get(cacheKey);
    if (cached) {
      loadRequestRef.current += 1;
      setLoading(false);
      setError("");
      setData(cached);
      setLoadedView(view);
      if (view === "gradebook") setLessonCursor(`o${cached.pageInfo?.startIndex ?? 0}`);
      return;
    }
    const requestId = ++loadRequestRef.current;
    setLoading(true);
    setError("");
    setActive(null);
    try {
      const nextData = await fetchGradebookData(id, view, cursor, anchorDate, signal);
      if (requestId !== loadRequestRef.current) return;
      gradebookCacheRef.current.set(cacheKey, nextData);
      setData(nextData);
      setLoadedView(view);
      if (view === "gradebook") {
        const resolvedCursor = `o${nextData.pageInfo?.startIndex ?? 0}`;
        gradebookCacheRef.current.set(`${id}:gradebook:${resolvedCursor}`, nextData);
        setLessonCursor(resolvedCursor);
        for (const adjacentCursor of [nextData.pageInfo?.previousCursor, nextData.pageInfo?.nextCursor]) {
          if (!adjacentCursor) continue;
          const adjacentKey = `${id}:gradebook:${adjacentCursor}`;
          if (gradebookCacheRef.current.has(adjacentKey)) continue;
          void fetchGradebookData(id, "gradebook", adjacentCursor)
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
    void load(groupId, undefined, { view, cursor: view === "gradebook" ? lessonCursor : "" });
  }

  function openLessonWindow(cursor: string | null | undefined) {
    if (!cursor || loading) return;
    setLessonCursor(cursor);
    void load(groupId, undefined, { view: "gradebook", cursor });
  }

  function jumpToLessonWindow(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const lessonNumber = Math.max(1, Number.parseInt(lessonJumpInput, 10) || 1);
    const total = data?.pageInfo?.totalLessons || lessonNumber;
    const start = Math.max(0, Math.min(lessonNumber - 1, Math.max(0, total - GRADEBOOK_LESSON_WINDOW)));
    openLessonWindow(`o${start}`);
  }

  function jumpToLessonDate() {
    if (!lessonDateInput || loading) return;
    setLessonCursor("");
    void load(groupId, undefined, { view: "gradebook", cursor: "", anchorDate: lessonDateInput, force: true });
  }

  function jumpToToday() {
    setLessonCursor("");
    setLessonDateInput("");
    void load(groupId, undefined, { view: "gradebook", cursor: "", force: true });
  }

  async function refreshCurrentView() {
    gradebookCacheRef.current.clear();
    await load(groupId, undefined, {
      view: activeView,
      cursor: activeView === "gradebook" ? lessonCursor : "",
      force: true,
    });
  }

  function openLessonAction(kind: "edit" | "cancel" | "recover", lesson: Lesson) {
    setLessonAction({ kind, lesson });
    setLessonActionError("");
    setLessonNameInput(lesson.lessonNumber.replace(/ \(Cancelled\)$/, ""));
    setLessonTopicInput(lesson.isCancellation ? "" : lesson.topic);
    setCancellationReason("");
  }

  async function submitLessonAction(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!lessonAction || lessonActionSaving) return;
    const targetId = lessonAction.lesson.lessonSessionId || lessonAction.lesson.id;
    setLessonActionSaving(true);
    setLessonActionError("");
    try {
      const isEdit = lessonAction.kind === "edit";
      const endpoint = isEdit
        ? academicRoutes.adminAcademicLessonApi(targetId)
        : lessonAction.kind === "cancel"
          ? academicRoutes.adminAcademicLessonCancelApi(targetId)
          : academicRoutes.adminAcademicLessonRecoverApi(targetId);
      const body = isEdit
        ? { lesson_name: lessonNameInput.trim(), topic: lessonTopicInput.trim() }
        : lessonAction.kind === "cancel"
          ? { reason: cancellationReason.trim() }
          : undefined;
      const response = await fetch(endpoint, {
        method: isEdit ? "PATCH" : "POST",
        headers: jsonCsrfHeaders(csrf),
        body: body ? JSON.stringify(body) : undefined,
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) {
        setLessonActionError(apiErrorMessage(json, "Unable to update this lesson."));
        return;
      }
      const payload = apiData<{ gradebook?: GradebookData }>(json);
      if (payload.gradebook) {
        gradebookCacheRef.current.clear();
        setData(payload.gradebook);
        setLoadedView(activeView);
      }
      else await refreshCurrentView();
      const message = isEdit
        ? "Lesson content updated. Its timetable date was kept."
        : lessonAction.kind === "cancel"
          ? "Lesson cancelled and the remaining program moved forward."
          : "Lesson recovered and the remaining program moved back.";
      setLessonAction(null);
      showSetupToast(message);
    } catch {
      setLessonActionError("Network error while updating the lesson.");
    } finally {
      setLessonActionSaving(false);
    }
  }

  function updateSetupField(key: string, value: string) {
    setSetupForm((current) => ({ ...current, [key]: value }));
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
    const existing = scheduleRows.find((row) => asNumber(row.group_id) === groupId && asString(row.status) === "active");
    const scheduledLessons = (data?.lessons || []).filter((lesson) => Boolean(lesson.date));
    const firstLesson = [...scheduledLessons].sort((left, right) => asString(left.date).localeCompare(asString(right.date)))[0];
    const start = asString(existing?.start_time) || asString(firstLesson?.startTime) || "14:00";
    const next = {
      teacherId: asString(existing?.teacher_id), startDate: dateInput(existing?.start_date) || lessonDateToInputValue(firstLesson?.date || ""),
      weekdays: asString(existing?.weekdays).split(",").map(Number).filter((day) => day >= 0 && day <= 6),
      startTime: start, room: asString(existing?.room), changeScope: "", effectiveDate: "",
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
      await refreshCurrentView();
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
      patchHw(active.enrollmentId, active.lesson.id, active.lesson.lessonNumber, score, result.studentSummary?.averageGrade);
      close();
    } catch {
      setCellError("Network error. Check the connection and try this cell again.");
    } finally {
      setSaving(false);
    }
  }

  function patchAtt(enrollmentId: number, lessonId: number, lessonNumber: string, status: AttValue) {
    gradebookCacheRef.current.clear();
    setData((prev) => {
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
    });
  }

  function patchHw(enrollmentId: number, lessonId: number, lessonNumber: string, score: number, averageGrade?: number) {
    gradebookCacheRef.current.clear();
    setData((prev) => {
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
    });
  }

  function patchExam(enrollmentId: number, examLabel: string, score: number) {
    gradebookCacheRef.current.clear();
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

  function patchLessonSchedule(lessonId: number, patch: Partial<Lesson>) {
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        lessons: prev.lessons.map((item) => (item.id === lessonId ? { ...item, ...patch } : item)),
      };
    });
  }

  function openTimeEdit(e: React.MouseEvent<HTMLButtonElement>, lesson: Lesson) {
    if (isCancelledLesson(lesson)) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setScheduleEdit({ lesson, kind: "time", anchorRect: rect });
    setTimeStartInput(lesson.startTime || "");
    setTimeEndInput(lesson.endTime || "");
    setError("");
  }

  function openRoomEdit(e: React.MouseEvent<HTMLButtonElement>, lesson: Lesson) {
    if (isCancelledLesson(lesson)) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setScheduleEdit({ lesson, kind: "room", anchorRect: rect });
    setRoomInput(lesson.room || "");
    setError("");
  }

  function closeScheduleEdit() {
    setScheduleEdit(null);
    setScheduleSaving(false);
  }

  async function persistTime(start: string, end: string) {
    if (!scheduleEdit || scheduleSaving) return;
    if (start && end && start >= end) {
      setError("End time must be after the start time.");
      return;
    }
    setScheduleSaving(true);
    setError("");
    try {
      const res = await fetch(academicRoutes.adminAcademicLessonApi(scheduleEdit.lesson.id), {
        method: "PATCH",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ start_time: start, end_time: end }),
      });
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setError(apiErrorMessage(json, "Unable to update the lesson time."));
        return;
      }
      patchLessonSchedule(scheduleEdit.lesson.id, { startTime: start, endTime: end });
      closeScheduleEdit();
    } catch {
      setError("Network error while updating the lesson time.");
    } finally {
      setScheduleSaving(false);
    }
  }

  function saveTime() {
    const start = timeStartInput.trim();
    const end = timeEndInput.trim();
    if (Boolean(start) !== Boolean(end)) {
      setError("Enter both a start and end time, or leave both empty.");
      return;
    }
    void persistTime(start, end);
  }

  function clearTime() {
    // Only resets the fields — Save is the single action that persists.
    setTimeStartInput("");
    setTimeEndInput("");
    setError("");
  }

  async function persistRoom(room: string) {
    if (!scheduleEdit || scheduleSaving) return;
    setScheduleSaving(true);
    setError("");
    try {
      const res = await fetch(academicRoutes.adminAcademicLessonApi(scheduleEdit.lesson.id), {
        method: "PATCH",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ room }),
      });
      const json = await res.json();
      if (!apiSucceeded(res, json)) {
        setError(apiErrorMessage(json, "Unable to update the lesson room."));
        return;
      }
      patchLessonSchedule(scheduleEdit.lesson.id, { room });
      closeScheduleEdit();
    } catch {
      setError("Network error while updating the lesson room.");
    } finally {
      setScheduleSaving(false);
    }
  }

  function saveRoom() {
    void persistRoom(roomInput.trim());
  }

  function clearRoom() {
    // Only resets the field — Save is the single action that persists.
    setRoomInput("");
    setError("");
  }

  const WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  function weekdayName(iso: string) {
    const parsed = new Date(`${iso}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? "" : WEEKDAY_NAMES[parsed.getDay()];
  }

  function groupLessonsByDate(items: Lesson[]): TimetableDateGroup[] {
    const groups: TimetableDateGroup[] = [];
    const indexByKey = new Map<string, number>();
    items.forEach((lesson) => {
      const iso = lessonDateToInputValue(lesson.date);
      const key = iso || "unscheduled";
      if (!indexByKey.has(key)) {
        indexByKey.set(key, groups.length);
        groups.push({
          key,
          iso,
          display: iso ? formatGradebookDate(lesson.date) : "No date set",
          weekday: iso ? weekdayName(iso) : "",
          lessons: [],
        });
      }
      groups[indexByKey.get(key)!].lessons.push(lesson);
    });
    return groups;
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
  const timetableGroups = groupLessonsByDate(lessons);

  const academicPeriodOptions = useMemo(() => collectPeriodOptions(lessons.map((lesson) => lesson.date)), [lessons]);
  const indicatorFilterActive = indicatorMonth !== "all" || indicatorYear !== "all";
  const metricLessons = useMemo(() => lessons.filter((lesson) => !isCancelledLesson(lesson)), [lessons]);
  const indicatorLessons = useMemo(
    () => indicatorFilterActive
      ? metricLessons.filter((lesson) => matchesPeriod(lesson.date, indicatorMonth, indicatorYear))
      : metricLessons,
    [indicatorFilterActive, indicatorMonth, indicatorYear, metricLessons],
  );
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
    const aap = filteredAAP ?? (indicatorFilterActive ? null : scoreOutOfNine(en.averageGrade) || null);
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
      AAP: aap,
      AR: arRate,
      arScore,
      averagePerformance,
      isLowAAP: aap !== null && aap < 5,
      isLowAR: arRate !== null && arRate < 80,
      present,
      total,
    };
  }), [enrollments, indicatorFilterActive, indicatorLessons]);
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
    setScheduleEdit(null);
  }, [activeView]);

  const popTop = active
    ? Math.min(active.anchorRect.bottom + 4, window.innerHeight - 200)
    : 0;
  const popLeft = active
    ? Math.min(active.anchorRect.left, window.innerWidth - 220)
    : 0;
  const schedulePopTop = scheduleEdit
    ? Math.min(scheduleEdit.anchorRect.bottom + 8, window.innerHeight - 260)
    : 0;
  const schedulePopLeft = scheduleEdit
    ? Math.max(8, Math.min(scheduleEdit.anchorRect.left, window.innerWidth - 316))
    : 0;
  const detailMetricClass = `rounded-lg border border-foreground/8 bg-background p-3 shadow-sm ${motion.card}`;
  const panelCardClass = `rounded-xl border border-foreground/8 bg-surface shadow-card ${motion.panel}`;
  const chartPanelClass = `rounded-lg border border-foreground/8 bg-background/80 p-3 shadow-sm ${motion.panel}`;
  return (
    <div className={`space-y-3 ${motion.panel}`}>
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
      ) : loading ? (
        <div className="rounded-xl border border-foreground/8 bg-surface p-6 text-center text-sm text-muted-foreground">Loading…</div>
      ) : null}

      {/* 2. View Switcher Buttons */}
      {data && (
        <div className="flex border-b border-foreground/8 gap-2 overflow-x-auto py-1">
          {(["gradebook", "academic", "ep", "timetable"] as const).map((view) => {
            const labels: Record<string, string> = {
              gradebook: "Gradebook",
              academic: "Academic Indicators",
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
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-foreground/8 px-4 py-3">
              <div><p className="text-sm font-bold">Gradebook</p><p className="text-xs text-muted-foreground">Curriculum lessons with attendance and homework</p></div>
              <button type="button" onClick={() => { setStudentOpen(true); setStudentName(""); setStudentError(""); setCreatedStudent(null); }} className="inline-flex min-h-11 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground sm:min-h-9"><Plus className="h-4 w-4" /> New Student</button>
            </div>
            {data.pageInfo ? (
              <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-foreground/8 bg-muted/20 px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <button type="button" aria-label="Previous lessons" disabled={!data.pageInfo.hasPrevious || loading} onClick={() => openLessonWindow(data.pageInfo?.previousCursor)} className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-foreground/10 bg-background text-foreground disabled:opacity-35 sm:h-9 sm:w-9"><ChevronLeft className="h-4 w-4" /></button>
                  <span className="min-w-32 text-center text-xs font-bold tabular-nums">Lessons {data.pageInfo.startIndex + 1}–{data.pageInfo.endIndex} of {data.pageInfo.totalLessons}</span>
                  <button type="button" aria-label="Next lessons" disabled={!data.pageInfo.hasNext || loading} onClick={() => openLessonWindow(data.pageInfo?.nextCursor)} className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-foreground/10 bg-background text-foreground disabled:opacity-35 sm:h-9 sm:w-9"><ChevronRight className="h-4 w-4" /></button>
                  <button type="button" disabled={loading} onClick={jumpToToday} className="h-11 rounded-lg border border-primary/20 bg-primary/5 px-3 text-xs font-bold text-primary disabled:opacity-50 sm:h-9">Today</button>
                </div>
                <div className="flex flex-1 flex-wrap items-center justify-end gap-1.5">
                  <form onSubmit={jumpToLessonWindow} className="flex items-center gap-1">
                    <label className="sr-only" htmlFor="gradebook-lesson-jump">Jump to lesson number</label>
                    <input id="gradebook-lesson-jump" type="number" min={1} max={data.pageInfo.totalLessons} value={lessonJumpInput} onChange={(event) => setLessonJumpInput(event.target.value)} placeholder="Lesson #" className="h-11 w-24 rounded-lg border border-foreground/10 bg-background px-2 text-sm sm:h-9" />
                    <button type="submit" disabled={!lessonJumpInput || loading} className="h-11 rounded-lg border border-foreground/10 bg-background px-3 text-xs font-bold disabled:opacity-40 sm:h-9">Go</button>
                  </form>
                  <label className="sr-only" htmlFor="gradebook-date-jump">Jump to lesson date</label>
                  <input id="gradebook-date-jump" type="date" value={lessonDateInput} onChange={(event) => setLessonDateInput(event.target.value)} className="h-11 rounded-lg border border-foreground/10 bg-background px-2 text-sm sm:h-9" />
                  <button type="button" aria-label="Find lessons by date" disabled={!lessonDateInput || loading} onClick={jumpToLessonDate} className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-foreground/10 bg-background disabled:opacity-40 sm:h-9 sm:w-9"><Search className="h-4 w-4" /></button>
                </div>
              </div>
            ) : null}
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
                          <span
                            className={`inline-flex max-w-full items-center justify-center gap-1 px-1.5 py-0.5 text-[10px] font-bold leading-tight ${
                              isCancelledLesson(lesson) ? "text-red-700" : "text-muted-foreground"
                            }`}
                            title="Date supplied by the timetable"
                          >
                            <CalendarDays className="h-2.5 w-2.5 shrink-0" />
                            <span className="whitespace-nowrap">{formatGradebookDate(lesson.date) || "Unscheduled"}</span>
                          </span>
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
                  {enrollments.map((en, enrollmentIndex) => (
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
                      {lessons.map((lesson, lessonIndex) => {
                        const att = (en.attendanceByLessonId?.[String(lesson.id)] ?? en.attendance[lesson.lessonNumber] ?? "") as AttValue;
                        const hw = en.homeworkByLessonId?.[String(lesson.id)] ?? en.homework[lesson.lessonNumber];
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
                                data-gradebook-cell={`${enrollmentIndex}:${lessonIndex * 2}`}
                                onClick={(e) => openCell(e, en.enrollmentId, lesson, "att", hw)}
                                onKeyDown={(event) => moveGradebookCellFocus(event, enrollmentIndex, lessonIndex * 2)}
                                title={`${en.fullName} · ${lesson.lessonNumber} · attendance`}
                                className={`mx-auto flex h-11 w-11 items-center justify-center rounded-lg text-[11px] font-bold shadow-sm transition-[transform,opacity,box-shadow] hover:-translate-y-px hover:opacity-85 sm:h-7 sm:w-9 sm:text-[10px] ${att ? attCls(att) : "text-foreground/20 shadow-none"} ${isActiveAtt ? "ring-2 ring-primary/35 ring-offset-1" : ""}`}
                              >
                                {att ? attLabel(att) : "·"}
                              </button>
                            </td>
                            <td className="border-r border-foreground/5 p-0.5 text-center" style={{ width: GRADEBOOK_HW_COL_WIDTH }}>
                              <button
                                type="button"
                                data-gradebook-cell={`${enrollmentIndex}:${lessonIndex * 2 + 1}`}
                                disabled={!canEditHomework}
                                onClick={(e) => openCell(e, en.enrollmentId, lesson, "hw", hw)}
                                onKeyDown={(event) => moveGradebookCellFocus(event, enrollmentIndex, lessonIndex * 2 + 1)}
                                title={`${en.fullName} · ${lesson.lessonNumber} · homework`}
                                className={`mx-auto flex h-11 min-w-11 items-center justify-center rounded-lg px-2 text-[11px] transition-[transform,opacity,box-shadow] hover:-translate-y-px hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 sm:h-7 sm:min-w-10 sm:text-[10px] ${hw !== undefined ? "bg-blue-50 font-bold text-blue-700 shadow-sm" : "text-foreground/20"} ${isActiveHw ? "ring-2 ring-primary/35 ring-offset-1" : ""}`}
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

      {data && activeView === "academic" && loadedView === "academic" && (
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

      {data && activeView === "timetable" && loadedView === "timetable" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-foreground/8 bg-surface px-4 py-3 shadow-card">
            <div><h3 className="text-sm font-bold">Lesson Timetable</h3><p className="text-xs text-muted-foreground">Timetable dates flow directly into the Gradebook.</p></div>
            <button type="button" onClick={openGroupSetup} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-primary px-4 text-xs font-bold text-primary-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40">
              <Settings className="h-4 w-4" />
              {hasSavedSetup || scheduleRows.some((row) => asNumber(row.group_id) === groupId && asString(row.status) === "active") ? "Change Schedule" : "Set Up Timetable"}
            </button>
          </div>
          {timetableGroups.length ? (
            <TimetableCard groups={timetableGroups} isLessonCancelled={isCancelledLesson} onOpenTime={openTimeEdit} onOpenRoom={openRoomEdit} onEditLesson={(lesson) => openLessonAction("edit", lesson)} onCancelLesson={(lesson) => openLessonAction("cancel", lesson)} onRecoverLesson={(lesson) => openLessonAction("recover", lesson)} />
          ) : (
            <div className="rounded-xl border border-dashed border-foreground/15 bg-surface px-6 py-16 text-center">
              <CalendarDays className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm font-bold">Timetable not configured</p>
              <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">Set the launch date, teaching days, and lesson time to place every program lesson automatically.</p>
              <button type="button" onClick={openGroupSetup} className="mt-4 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground">Set Up Timetable</button>
            </div>
          )}
        </div>
      )}

      <Modal open={Boolean(lessonAction)} onClose={() => !lessonActionSaving && setLessonAction(null)} title={lessonAction?.kind === "edit" ? <span className="inline-flex items-center gap-2"><Pencil className="h-5 w-5 text-primary" />Edit Lesson</span> : lessonAction?.kind === "recover" ? <span className="inline-flex items-center gap-2"><RotateCcw className="h-5 w-5 text-emerald-600" />Recover Lesson</span> : <span className="inline-flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-red-600" />Cancel Lesson</span>} subtitle={lessonAction?.kind === "edit" ? "Change this group's lesson content without moving its date." : lessonAction?.kind === "recover" ? "Restore the original slot and move following lessons back." : "Leave a cancelled slot and move this lesson plus following lessons forward."} size="sm" mobileMode="sheet" closeOnOutsideClick={!lessonActionSaving} closeOnEscape={!lessonActionSaving}>
        <form onSubmit={submitLessonAction} className="flex min-h-0 flex-1 flex-col">
          <ModalBody className="space-y-4">
            {lessonActionError ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{lessonActionError}</p> : null}
            {lessonAction ? <div className="rounded-lg border border-foreground/10 bg-muted/30 p-3"><p className="text-sm font-bold">{lessonAction.lesson.lessonNumber}</p><p className="mt-1 text-xs text-muted-foreground">{formatGradebookDate(lessonAction.lesson.date)}{lessonAction.lesson.startTime ? ` · ${lessonAction.lesson.startTime}` : ""}</p></div> : null}
            {lessonAction?.kind === "edit" ? <><label className="block"><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Lesson name</span><input autoFocus required value={lessonNameInput} onChange={(event) => setLessonNameInput(event.target.value)} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label><label className="block"><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Topic</span><textarea value={lessonTopicInput} onChange={(event) => setLessonTopicInput(event.target.value)} rows={3} className="w-full resize-none rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm" /></label></> : lessonAction?.kind === "cancel" ? <label className="block"><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Cancellation reason</span><textarea autoFocus required minLength={3} value={cancellationReason} onChange={(event) => setCancellationReason(event.target.value)} rows={3} placeholder="For example: school closed" className="w-full resize-none rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm" /><span className="mt-1 block text-xs text-muted-foreground">Required and shown on the cancelled slot.</span></label> : <p className="text-sm text-muted-foreground">The cancellation remains in audit history, while its active placeholder is removed.</p>}
          </ModalBody>
          <ModalFooter className="flex justify-end gap-2"><button type="button" onClick={() => setLessonAction(null)} disabled={lessonActionSaving} className="min-h-11 rounded-lg bg-muted px-4 text-sm font-bold text-muted-foreground">Keep unchanged</button><button type="submit" disabled={lessonActionSaving || (lessonAction?.kind === "edit" && !lessonNameInput.trim()) || (lessonAction?.kind === "cancel" && cancellationReason.trim().length < 3)} className={`min-h-11 rounded-lg px-5 text-sm font-bold text-white disabled:opacity-50 ${lessonAction?.kind === "cancel" ? "bg-red-600" : lessonAction?.kind === "recover" ? "bg-emerald-600" : "bg-primary"}`}>{lessonActionSaving ? "Saving..." : lessonAction?.kind === "cancel" ? "Cancel & Move Forward" : lessonAction?.kind === "recover" ? "Recover & Restore" : "Save Content"}</button></ModalFooter>
        </form>
      </Modal>

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
            <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Course Launch Date</span><input type="date" required value={setupForm.startDate} onChange={(event) => updateSetupField("startDate", event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
            <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Lesson Time</span><input type="time" required value={setupForm.startTime} onChange={(event) => updateSetupField("startTime", event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
          </div>
          <fieldset><legend className="mb-1 text-xs font-bold uppercase text-muted-foreground">Lesson Days · {setupForm.weekdays.length} per week</legend><div className="grid grid-cols-7 gap-1">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label, day) => <button key={label} type="button" onClick={() => toggleSetupWeekday(day)} className={`h-10 rounded-lg text-[11px] font-bold ${setupForm.weekdays.includes(day) ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{label.slice(0, 2)}</button>)}</div></fieldset>
          <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Room</span><input value={setupForm.room} onChange={(event) => updateSetupField("room", event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" placeholder="Room 2" /></label>
          {hasExistingTimetable() ? <fieldset className="space-y-2 rounded-lg border border-foreground/10 bg-muted/30 p-3"><legend className="px-1 text-xs font-bold uppercase text-muted-foreground">Apply this change to</legend>{[["all","All lesson dates"],["from_date","Lessons from a specific date"],["remaining","Remaining scheduled lessons"]].map(([value,label]) => <label key={value} className="flex items-center gap-2 rounded-md p-2 text-sm font-semibold hover:bg-background"><input type="radio" name="changeScope" checked={setupForm.changeScope===value} onChange={() => updateSetupField("changeScope",value)} />{label}</label>)}{setupForm.changeScope==="from_date" ? <label className="block"><span className="mb-1 block text-xs font-bold text-muted-foreground">Effective from</span><input type="date" required value={setupForm.effectiveDate} onChange={(event) => updateSetupField("effectiveDate",event.target.value)} className="h-10 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label> : null}</fieldset> : null}
          </ModalBody>
          <ModalFooter className="flex justify-end gap-2">
            <button type="button" onClick={closeGroupSetup} disabled={setupSaving} className="min-h-11 rounded-lg bg-muted px-4 text-sm font-bold text-muted-foreground">Cancel</button>
            <button type="submit" disabled={setupSaving || !setupForm.startDate || !setupForm.startTime || setupForm.weekdays.length === 0 || (hasExistingTimetable() && !setupForm.changeScope)} className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 text-sm font-bold text-primary-foreground disabled:opacity-50">{setupSaving ? "Saving..." : "Save Timetable"}</button>
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

      {scheduleEdit && scheduleEdit.kind === "time" ? (
        <TimePopover
          ref={schedulePopRef}
          lesson={scheduleEdit.lesson}
          dateLabel={formatGradebookDate(scheduleEdit.lesson.date)}
          position={{ top: schedulePopTop, left: schedulePopLeft }}
          startValue={timeStartInput}
          endValue={timeEndInput}
          onStartChange={setTimeStartInput}
          onEndChange={setTimeEndInput}
          onClear={clearTime}
          onSave={saveTime}
          onClose={closeScheduleEdit}
          saving={scheduleSaving}
        />
      ) : null}
      {scheduleEdit && scheduleEdit.kind === "room" ? (
        <RoomPopover
          ref={schedulePopRef}
          lesson={scheduleEdit.lesson}
          dateLabel={formatGradebookDate(scheduleEdit.lesson.date)}
          position={{ top: schedulePopTop, left: schedulePopLeft }}
          value={roomInput}
          onChange={setRoomInput}
          onClear={clearRoom}
          onSave={saveRoom}
          onClose={closeScheduleEdit}
          saving={scheduleSaving}
        />
      ) : null}

    </div>
  );
}
