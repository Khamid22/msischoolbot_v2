import { useState, useEffect, useMemo, useRef } from "react";
import type { FormEvent, PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight, Clock, Filter, Plus, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { routes } from "@/shared/lib/routes";
import { useDismissibleLayer } from "@/shared/lib/useDismissibleLayer";
import { asNumber, asString } from "@/features/managementTypes";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";
import { fetchApiQuery, queryClient } from "@/shared/api/queryClient";
import { FieldLabel, TextInput, Select, weekdayLabels, timetableStartHour, timetableEndHour, isoDate, startOfWeek, addDays, formatWeekRange, timeToMinutes, formatSessionTime, lessonDateToIso, lessonStatus, scheduleTimeForLesson, ScheduleRow, SessionRow, LessonHistoryRow, RawTimetableBlock, TimetableLessonBlock, layoutSessionsForDay } from "./shared";
import { DEFAULT_CLASS_MINUTES, SCHEDULE_SNAP_MINUTES, clampNumber, lessonDurationMinutesForSchoolCode, snapToMinutes, snappedStartMinutes } from "./scheduleMath";

// The grid scales up when the week has many overlapping classes instead of
// squeezing those cards into unreadable strips.
const BASE_HOUR_PX = 70;
const TIME_COLUMN_PX = 60;

type BlockStatus = "scheduled" | "completed" | "cancelled";

/** A class the admin placed on the grid this session (optimistic, PATCH-backed). */
type PlacedBlock = {
  id: number;
  date: string; // ISO yyyy-mm-dd
  start: string; // HH:MM
  end: string; // HH:MM
  group_id: number;
  group_name: string;
  subject_name: string;
  teacher_name?: string;
  lesson_number?: string;
  lesson_topic?: string;
  status: BlockStatus;
};

type DragPayload = {
  id: number;
  durationMin: number;
  meta: Omit<PlacedBlock, "id" | "date" | "start" | "end">;
};

type PointerDrag = {
  pointerId: number;
  payload: DragPayload;
  startX: number;
  startY: number;
  x: number;
  y: number;
  label: string;
  moved: boolean;
  grabOffsetX: number;
  grabOffsetY: number;
  previewWidth: number;
  previewHeight: number;
  subjectName: string;
  status: BlockStatus;
};

type ResizeDrag = {
  pointerId: number;
  payload: DragPayload;
  dayIso: string;
  edge: "start" | "end";
  startY: number;
  originalStartMin: number;
  originalEndMin: number;
  previewStartMin: number;
  previewEndMin: number;
  label: string;
};

function minutesToLabel(totalMinutes: number) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function scheduleCardClass(subject: unknown, status: BlockStatus) {
  if (status === "cancelled") {
    return "border-red-300/70 bg-gradient-to-br from-red-500 to-rose-700 text-white shadow-red-950/20";
  }
  const normalizedSubject = asString(subject).toLowerCase();
  if (normalizedSubject.includes("english") || normalizedSubject.includes("eng")) {
    return status === "completed"
      ? "border-sky-300/70 bg-gradient-to-br from-sky-500 to-cyan-700 text-white shadow-sky-950/20"
      : "border-amber-300/70 bg-gradient-to-br from-amber-400 to-orange-600 text-white shadow-orange-950/20";
  }
  return status === "completed"
    ? "border-emerald-300/70 bg-gradient-to-br from-emerald-500 to-teal-700 text-white shadow-emerald-950/20"
    : "border-blue-300/70 bg-gradient-to-br from-blue-500 to-indigo-700 text-white shadow-blue-950/20";
}

function isScheduleSubjectOption(value: unknown) {
  const normalized = asString(value).toLowerCase();
  return Boolean(normalized) && !normalized.includes("chem");
}

function ScheduleFilterSelect({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <label className="relative inline-flex h-7 min-w-[7.5rem] items-center">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-7 w-full appearance-none rounded-md border border-foreground/10 bg-background/90 pl-2 pr-7 text-[11px] font-bold text-foreground shadow-sm outline-none transition focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 h-3.5 w-3.5 text-muted-foreground" />
    </label>
  );
}

function lessonDurationMinutes(lesson: LessonHistoryRow) {
  return lessonDurationMinutesForSchoolCode(lesson.school_code);
}

function overlapGridFor(count: number) {
  if (count <= 1) return { columns: 1, rows: 1 };
  const columns = Math.min(3, Math.max(2, Math.ceil(Math.sqrt(count))));
  return { columns, rows: Math.ceil(count / columns) };
}

function normalizeBlockStatus(value: unknown): BlockStatus {
  const normalized = asString(value).toLowerCase();
  if (normalized === "cancelled" || normalized === "canceled") return "cancelled";
  if (["completed", "complete", "done", "accomplished"].includes(normalized)) return "completed";
  return "scheduled";
}

export function SchedulePanel({ state }: { state: any }) {
  const props = state.props || {};
  const csrf: string = asString(props.csrfToken);
  const academicRoutes = state.academicRoutes || routes;
  const isTeacherMode = asString(state.adminMode).toLowerCase() === "teacher";
  const canDrag = !isTeacherMode;
  const groups = Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [];
  const teachers = Array.isArray(props.adminTeachers) ? props.adminTeachers : [];
  const initialSchedules = Array.isArray(props.adminAcademicSchedules) ? props.adminAcademicSchedules : [];
  const initialSessions = Array.isArray(props.adminAcademicSessions) ? props.adminAcademicSessions : [];
  const initialLessons = Array.isArray(props.adminAcademicLessons) ? props.adminAcademicLessons : [];
  const [schedules, setSchedules] = useState<ScheduleRow[]>(initialSchedules as ScheduleRow[]);
  const [sessions, setSessions] = useState<SessionRow[]>(initialSessions as SessionRow[]);
  const [lessons, setLessons] = useState<LessonHistoryRow[]>(initialLessons as LessonHistoryRow[]);
  const [placedBlocks, setPlacedBlocks] = useState<Record<number, PlacedBlock>>({});
  const [dropHint, setDropHint] = useState<{ day: string; startMin: number; durationMin: number } | null>(null);
  const [pointerDrag, setPointerDrag] = useState<PointerDrag | null>(null);
  const pointerDragRef = useRef<PointerDrag | null>(null);
  const [selectedLessonId, setSelectedLessonId] = useState<number | null>(null);
  const [resizeDrag, setResizeDrag] = useState<ResizeDrag | null>(null);
  const resizeDragRef = useRef<ResizeDrag | null>(null);
  const dayColumnRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const timetableScrollRef = useRef<HTMLDivElement | null>(null);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [createOpen, setCreateOpen] = useState(false);
  useDismissibleLayer({
    enabled: createOpen,
    onDismiss: () => setCreateOpen(false),
    dismissOnOutsidePointer: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [scheduleGroupFilter, setScheduleGroupFilter] = useState("all");
  const [scheduleSubjectFilter, setScheduleSubjectFilter] = useState("all");
  const [scheduleStatusFilter, setScheduleStatusFilter] = useState("all");
  const { toast, showToast, clearToast } = useFloatingToast();
  const [error, setError] = useState("");
  const [rangeLoading, setRangeLoading] = useState(false);
  const today = isoDate(new Date());
  const [form, setForm] = useState({
    groupId: asString(groups[0]?.id),
    teacherId: "",
    title: "",
    weekdays: ["1", "3"],
    lessonDurationMinutes: "90",
    startTime: "17:00",
    endTime: "18:30",
    startDate: today,
    endDate: isoDate(addDays(new Date(), 60)),
    room: "",
    onlineUrl: "",
  });

  useEffect(() => {
    setSchedules(initialSchedules as ScheduleRow[]);
    setSessions(initialSessions as SessionRow[]);
    setLessons(initialLessons as LessonHistoryRow[]);
  }, [props.adminAcademicSchedules, props.adminAcademicSessions, props.adminAcademicLessons]);

  const weekDays = useMemo(() => Array.from({ length: 7 }, (_item, index) => addDays(weekStart, index)), [weekStart]);
  const weekDateSet = useMemo(() => new Set(weekDays.map(isoDate)), [weekDays]);

  useEffect(() => {
    if (typeof academicRoutes.adminAcademicTimetableApi !== "function") return;
    const query = new URLSearchParams({
      date_from: isoDate(weekDays[0]),
      date_to: isoDate(weekDays[6]),
    });
    setRangeLoading(true);
    setError("");
    void fetchApiQuery<{ schedules?: ScheduleRow[]; sessions?: SessionRow[] }>(
      ["academic", "timetable", query.toString()],
      academicRoutes.adminAcademicTimetableApi(query.toString()),
    )
      .then((data) => {
        setSchedules(Array.isArray(data.schedules) ? data.schedules : []);
        setSessions(Array.isArray(data.sessions) ? data.sessions : []);
      })
      .catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : "Could not load this timetable week.");
      })
      .finally(() => setRangeLoading(false));
  }, [academicRoutes.adminAcademicTimetableApi, weekStart]);

  // Any lesson session that already carries explicit times (server sessions or
  // this session's drag placements) must not re-render from lesson history.
  const timedSessionIds = useMemo(() => {
    const ids = new Set<number>();
    sessions.forEach((session) => ids.add(Number(session.id)));
    Object.keys(placedBlocks).forEach((id) => ids.add(Number(id)));
    return ids;
  }, [sessions, placedBlocks]);

  const filteredSessions = useMemo(
    () =>
      sessions.filter((session) => {
        if (placedBlocks[Number(session.id)]) return false;
        const sessionIso = lessonDateToIso(asString(session.session_date)) || asString(session.session_date);
        if (!weekDateSet.has(sessionIso)) return false;
        return true;
      }),
    [sessions, weekDateSet, placedBlocks],
  );
  const recordedLessons = useMemo(
    () =>
      lessons.filter((lesson) => {
        if (timedSessionIds.has(Number(lesson.id))) return false;
        const lessonDate = lessonDateToIso(lesson.lesson_date);
        if (!lessonDate || !weekDateSet.has(lessonDate)) return false;
        if (asString(lesson.lesson_number).startsWith("S")) return false;
        return true;
      }),
    [lessons, weekDateSet, timedSessionIds],
  );
  const timedHistoryBlocks = useMemo(
    () =>
      recordedLessons.flatMap((lesson): RawTimetableBlock[] => {
        const inferredTime = scheduleTimeForLesson(lesson, schedules);
        const lessonDate = lessonDateToIso(lesson.lesson_date);
        if (!inferredTime || !lessonDate) return [];
        return [
          {
            id: `lesson-${lesson.id}`,
            group_id: Number(lesson.group_id),
            group_name: asString(lesson.group_name),
            subject_name: asString(lesson.subject_name),
            lesson_number: asString(lesson.lesson_number),
            lesson_topic: asString(lesson.lesson_topic),
            session_date: lessonDate,
            start_time: inferredTime.start_time,
            end_time: inferredTime.end_time,
            status: lessonStatus(lesson),
          },
        ];
      }),
    [recordedLessons, schedules],
  );
  const untimedLessons = useMemo(
    () => recordedLessons.filter((lesson) => !scheduleTimeForLesson(lesson, schedules)),
    [recordedLessons, schedules],
  );
  const scheduledBlocks = useMemo(
    () =>
      filteredSessions.map((session): RawTimetableBlock => {
        const sessionRecord = session as Record<string, unknown>;
        return {
          id: `session-${session.id}`,
          group_id: Number(session.group_id),
          group_name: asString(session.group_name),
          subject_name: asString(session.subject_name),
          teacher_name: asString(session.teacher_name),
          lesson_number: asString(sessionRecord.lesson_number || sessionRecord.source_label),
          lesson_topic: asString(sessionRecord.lesson_topic || sessionRecord.source_topic),
          session_date: lessonDateToIso(asString(session.session_date)) || asString(session.session_date),
          start_time: asString(session.start_time),
          end_time: asString(session.end_time),
          status: normalizeBlockStatus(session.status),
        };
      }),
    [filteredSessions],
  );
  const placedTimetableBlocks = useMemo(
    () =>
      Object.values(placedBlocks)
        .filter((block) => weekDateSet.has(block.date))
        .map((block): RawTimetableBlock => ({
          id: `session-${block.id}`,
          group_id: block.group_id,
          group_name: block.group_name,
          subject_name: block.subject_name,
          teacher_name: block.teacher_name,
          lesson_number: block.lesson_number,
          lesson_topic: block.lesson_topic,
          session_date: block.date,
          start_time: block.start,
          end_time: block.end,
          status: block.status,
        })),
    [placedBlocks, weekDateSet],
  );
  const timetableBlocks = useMemo(
    () => [...scheduledBlocks, ...placedTimetableBlocks, ...timedHistoryBlocks],
    [scheduledBlocks, placedTimetableBlocks, timedHistoryBlocks],
  );
  const allDayTimetableBlocks = useMemo(() => {
    const next: Record<string, TimetableLessonBlock[]> = {};
    weekDays.forEach((day) => {
      const dayIso = isoDate(day);
      next[dayIso] = layoutSessionsForDay(timetableBlocks.filter((session) => asString(session.session_date) === dayIso));
    });
    return next;
  }, [timetableBlocks, weekDays]);
  const filterOptions = useMemo(() => {
    const groupMap = new Map<string, string>();
    const subjectSet = new Set<string>();
    timetableBlocks.forEach((block) => {
      const groupId = String(block.group_id || "");
      if (groupId) groupMap.set(groupId, asString(block.group_name) || groupId);
      const subjectName = asString(block.subject_name);
      if (isScheduleSubjectOption(subjectName)) subjectSet.add(subjectName);
    });
    untimedLessons.forEach((lesson) => {
      const groupId = String(lesson.group_id || "");
      if (groupId) groupMap.set(groupId, asString(lesson.group_name) || groupId);
      const subjectName = asString(lesson.subject_name);
      if (isScheduleSubjectOption(subjectName)) subjectSet.add(subjectName);
    });
    return {
      groups: Array.from(groupMap.entries())
        .map(([value, label]) => ({ value, label }))
        .sort((left, right) => left.label.localeCompare(right.label, undefined, { numeric: true })),
      subjects: Array.from(subjectSet).sort((left, right) => left.localeCompare(right, undefined, { numeric: true })),
    };
  }, [timetableBlocks, untimedLessons]);
  const visibleTimetableBlocks = useMemo(
    () =>
      timetableBlocks.filter((block) => {
        if (scheduleGroupFilter !== "all" && String(block.group_id) !== scheduleGroupFilter) return false;
        if (scheduleSubjectFilter !== "all" && asString(block.subject_name) !== scheduleSubjectFilter) return false;
        if (scheduleStatusFilter !== "all" && block.status !== scheduleStatusFilter) return false;
        return true;
      }),
    [scheduleGroupFilter, scheduleStatusFilter, scheduleSubjectFilter, timetableBlocks],
  );
  const visibleUntimedLessons = useMemo(
    () =>
      untimedLessons.filter((lesson) => {
        if (scheduleGroupFilter !== "all" && String(lesson.group_id) !== scheduleGroupFilter) return false;
        if (scheduleSubjectFilter !== "all" && asString(lesson.subject_name) !== scheduleSubjectFilter) return false;
        if (scheduleStatusFilter !== "all" && lessonStatus(lesson) !== scheduleStatusFilter) return false;
        return true;
      }),
    [scheduleGroupFilter, scheduleStatusFilter, scheduleSubjectFilter, untimedLessons],
  );
  const dayTimetableBlocks = useMemo(() => {
    const next: Record<string, TimetableLessonBlock[]> = {};
    weekDays.forEach((day) => {
      const dayIso = isoDate(day);
      next[dayIso] = layoutSessionsForDay(visibleTimetableBlocks.filter((session) => asString(session.session_date) === dayIso));
    });
    return next;
  }, [visibleTimetableBlocks, weekDays]);
  const dayUntimedLessons = useMemo(() => {
    const next: Record<string, LessonHistoryRow[]> = {};
    weekDays.forEach((day) => {
      const dayIso = isoDate(day);
      next[dayIso] = visibleUntimedLessons.filter((lesson) => lessonDateToIso(lesson.lesson_date) === dayIso);
    });
    return next;
  }, [visibleUntimedLessons, weekDays]);
  const activeFilterCount = [scheduleGroupFilter, scheduleSubjectFilter, scheduleStatusFilter].filter((value) => value !== "all").length;

  useEffect(() => {
    if (scheduleSubjectFilter !== "all" && !filterOptions.subjects.includes(scheduleSubjectFilter)) {
      setScheduleSubjectFilter("all");
    }
  }, [filterOptions.subjects, scheduleSubjectFilter]);

  const busiestDayLoad = useMemo(() => {
    return weekDays.reduce((max, day) => {
      const dayIso = isoDate(day);
      return Math.max(max, (allDayTimetableBlocks[dayIso] || []).length);
    }, 0);
  }, [allDayTimetableBlocks, weekDays]);
  const busiestOverlap = useMemo(() => {
    return weekDays.reduce((max, day) => {
      const dayIso = isoDate(day);
      return Math.max(max, ...(allDayTimetableBlocks[dayIso] || []).map((session) => session.rowCount));
    }, 1);
  }, [allDayTimetableBlocks, weekDays]);
  const busiestOverlapGrid = overlapGridFor(busiestOverlap);
  const completedLessonCount = recordedLessons.filter((lesson) => lessonStatus(lesson) === "completed").length
    + placedTimetableBlocks.filter((block) => block.status === "completed").length;
  const cancelledLessonCount = recordedLessons.filter((lesson) => lessonStatus(lesson) === "cancelled").length
    + filteredSessions.filter((session) => ["cancelled", "canceled"].includes(asString(session.status).toLowerCase())).length;
  const activeSchedules = schedules.filter((schedule) => asString(schedule.status) !== "cancelled");

  // Full day range with a scrollable grid: nothing is compressed or hidden.
  const displayStartHour = timetableStartHour;
  const displayEndHour = timetableEndHour;
  const dayStartMin = displayStartHour * 60;
  const dayEndMin = displayEndHour * 60;
  const hourPx = Math.min(150, BASE_HOUR_PX + Math.max(0, busiestOverlapGrid.rows - 1) * 12 + Math.max(0, Math.min(busiestDayLoad - 7, 8)));
  const dayMinWidthPx = Math.min(240, Math.max(112, 96 + Math.min(busiestDayLoad, 8) * 6 + Math.max(0, busiestOverlapGrid.columns - 1) * 34));
  const gridTemplateColumns = `${TIME_COLUMN_PX}px repeat(7, minmax(${dayMinWidthPx}px, 1fr))`;
  const gridMinWidthPx = TIME_COLUMN_PX + dayMinWidthPx * 7;
  const gridViewportMaxPx = Math.min(1240, Math.max(760, 720 + Math.min(busiestDayLoad, 10) * 28));
  const gridHeightPx = (displayEndHour - displayStartHour) * hourPx;
  const hours = Array.from({ length: displayEndHour - displayStartHour + 1 }, (_item, index) => displayStartHour + index);

  function blockDragPayload(block: RawTimetableBlock): DragPayload {
    const startMin = timeToMinutes(asString(block.start_time));
    const endMin = timeToMinutes(asString(block.end_time));
    const durationMin = Number.isFinite(startMin) && Number.isFinite(endMin) && endMin > startMin
      ? endMin - startMin
      : DEFAULT_CLASS_MINUTES;
    const rawId = asString(block.id).replace(/^(session|lesson)-/, "");
    return {
      id: Number(rawId),
      durationMin,
      meta: {
        group_id: block.group_id,
        group_name: asString(block.group_name),
        subject_name: asString(block.subject_name),
        teacher_name: asString(block.teacher_name),
        lesson_number: asString(block.lesson_number),
        lesson_topic: asString(block.lesson_topic),
        status: block.status,
      },
    };
  }

  function lessonDragPayload(lesson: LessonHistoryRow): DragPayload {
    return {
      id: Number(lesson.id),
      durationMin: lessonDurationMinutes(lesson),
      meta: {
        group_id: Number(lesson.group_id),
        group_name: asString(lesson.group_name),
        subject_name: asString(lesson.subject_name),
        lesson_number: asString(lesson.lesson_number),
        lesson_topic: asString(lesson.lesson_topic),
        status: lessonStatus(lesson),
      },
    };
  }

  function snappedStartMinutesFromRect(clientY: number, rect: DOMRect, durationMin: number, grabOffsetY = 0) {
    return snappedStartMinutes({
      clientY,
      rectTop: rect.top,
      dayStartMin,
      dayEndMin,
      durationMin,
      hourPx,
      grabOffsetY,
    });
  }

  function dropTargetAtPoint(clientX: number, clientY: number, durationMin: number, grabOffsetY = 0) {
    for (const day of weekDays) {
      const dayIso = isoDate(day);
      const node = dayColumnRefs.current[dayIso];
      if (!node) continue;
      const rect = node.getBoundingClientRect();
      if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) continue;
      return {
        dayIso,
        startMin: snappedStartMinutesFromRect(clientY, rect, durationMin, grabOffsetY),
      };
    }
    return null;
  }

  function updateDropHint(clientX: number, clientY: number, drag: PointerDrag) {
    const target = dropTargetAtPoint(clientX, clientY, drag.payload.durationMin, drag.grabOffsetY);
    if (!target) {
      setDropHint(null);
      return;
    }
    setDropHint((current) =>
      current && current.day === target.dayIso && current.startMin === target.startMin
        ? current
        : { day: target.dayIso, startMin: target.startMin, durationMin: drag.payload.durationMin },
    );
  }

  function maybeScrollGrid(clientY: number) {
    const scroller = timetableScrollRef.current;
    if (!scroller) return;
    const rect = scroller.getBoundingClientRect();
    const edge = 44;
    if (clientY < rect.top + edge) {
      scroller.scrollTop -= Math.max(6, Math.round((rect.top + edge - clientY) / 2));
    } else if (clientY > rect.bottom - edge) {
      scroller.scrollTop += Math.max(6, Math.round((clientY - (rect.bottom - edge)) / 2));
    }
  }

  async function updatePayloadTime(payload: DragPayload, dayIso: string, startMin: number, endMin: number, message: string) {
    const start = minutesToLabel(startMin);
    const end = minutesToLabel(endMin);
    setError("");
    clearToast();

    const previous = placedBlocks[payload.id];
    const optimistic: PlacedBlock = { id: payload.id, date: dayIso, start, end, ...payload.meta };
    setPlacedBlocks((current) => ({ ...current, [payload.id]: optimistic }));
    setSelectedLessonId(payload.id);

    try {
      const response = await fetch(academicRoutes.adminAcademicLessonApi(payload.id), {
        method: "PATCH",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ lesson_date: dayIso, start_time: start, end_time: end }),
      });
      const data = await response.json();
      if (!apiSucceeded(response, data)) {
        throw new Error(apiErrorMessage(data, "Could not move the class."));
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["academic", "timetable"] }),
        queryClient.invalidateQueries({ queryKey: ["academic", "gradebook", payload.meta.group_id] }),
        queryClient.invalidateQueries({ queryKey: ["academic", "gradebook-trends", payload.meta.group_id] }),
      ]);
      showToast(message);
    } catch (dropError) {
      setPlacedBlocks((current) => {
        const next = { ...current };
        if (previous) next[payload.id] = previous;
        else delete next[payload.id];
        return next;
      });
      setError(dropError instanceof Error ? dropError.message : "Network error. Please try again.");
    }
  }

  async function placePayload(payload: DragPayload, dayIso: string, startMin: number) {
    const endMin = startMin + payload.durationMin;
    await updatePayloadTime(payload, dayIso, startMin, endMin, `${payload.meta.group_name} placed on ${dayIso} at ${minutesToLabel(startMin)}–${minutesToLabel(endMin)}.`);
  }

  function startPointerDrag(event: ReactPointerEvent<HTMLElement>, payload: DragPayload, label: string) {
    if (!canDrag) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const rect = event.currentTarget.getBoundingClientRect();
    const next = {
      pointerId: event.pointerId,
      payload,
      startX: event.clientX,
      startY: event.clientY,
      x: event.clientX,
      y: event.clientY,
      label,
      moved: false,
      grabOffsetX: event.clientX - rect.left,
      grabOffsetY: event.clientY - rect.top,
      previewWidth: rect.width,
      previewHeight: rect.height,
      subjectName: payload.meta.subject_name,
      status: payload.meta.status,
    };
    pointerDragRef.current = next;
    setPointerDrag(next);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function movePointerDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = pointerDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    event.preventDefault();
    maybeScrollGrid(event.clientY);
    const distance = Math.hypot(event.clientX - current.startX, event.clientY - current.startY);
    const moved = current.moved || distance > 5;
    const next = { ...current, x: event.clientX, y: event.clientY, moved };
    pointerDragRef.current = next;
    setPointerDrag(next);
    if (moved) {
      updateDropHint(event.clientX, event.clientY, next);
    }
  }

  function endPointerDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = pointerDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    event.preventDefault();
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    const target = dropTargetAtPoint(event.clientX, event.clientY, current.payload.durationMin, current.grabOffsetY);
    pointerDragRef.current = null;
    setPointerDrag(null);
    setDropHint(null);
    if (current.moved && target) {
      void placePayload(current.payload, target.dayIso, target.startMin);
    } else if (!current.moved) {
      setSelectedLessonId(current.payload.id);
    }
  }

  function cancelPointerDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = pointerDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    pointerDragRef.current = null;
    setPointerDrag(null);
    setDropHint(null);
  }

  function startResizeDrag(event: ReactPointerEvent<HTMLElement>, session: TimetableLessonBlock, edge: "start" | "end") {
    if (!canDrag) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const payload = blockDragPayload(session);
    const startMin = timeToMinutes(asString(session.start_time));
    const endMin = timeToMinutes(asString(session.end_time));
    if (!Number.isFinite(startMin) || !Number.isFinite(endMin) || endMin <= startMin) return;
    const next: ResizeDrag = {
      pointerId: event.pointerId,
      payload,
      dayIso: asString(session.session_date),
      edge,
      startY: event.clientY,
      originalStartMin: startMin,
      originalEndMin: endMin,
      previewStartMin: startMin,
      previewEndMin: endMin,
      label: asString(session.group_name),
    };
    resizeDragRef.current = next;
    setResizeDrag(next);
    setSelectedLessonId(payload.id);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function moveResizeDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = resizeDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    event.preventDefault();
    maybeScrollGrid(event.clientY);
    const deltaMinutes = snapToMinutes(((event.clientY - current.startY) / hourPx) * 60);
    let previewStartMin = current.originalStartMin;
    let previewEndMin = current.originalEndMin;
    if (current.edge === "start") {
      previewStartMin = clampNumber(snapToMinutes(current.originalStartMin + deltaMinutes), dayStartMin, current.originalEndMin - SCHEDULE_SNAP_MINUTES);
    } else {
      previewEndMin = clampNumber(snapToMinutes(current.originalEndMin + deltaMinutes), current.originalStartMin + SCHEDULE_SNAP_MINUTES, dayEndMin);
    }
    const next = { ...current, previewStartMin, previewEndMin };
    resizeDragRef.current = next;
    setResizeDrag(next);
  }

  function endResizeDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = resizeDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    event.preventDefault();
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    resizeDragRef.current = null;
    setResizeDrag(null);
    if (current.previewStartMin !== current.originalStartMin || current.previewEndMin !== current.originalEndMin) {
      void updatePayloadTime(
        current.payload,
        current.dayIso,
        current.previewStartMin,
        current.previewEndMin,
        `${current.label} updated to ${minutesToLabel(current.previewStartMin)}–${minutesToLabel(current.previewEndMin)}.`,
      );
    }
  }

  function cancelResizeDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = resizeDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    resizeDragRef.current = null;
    setResizeDrag(null);
  }

  function updateField(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function toggleWeekday(day: string) {
    setForm((current) => {
      const selected = new Set(current.weekdays);
      if (selected.has(day)) selected.delete(day);
      else selected.add(day);
      return { ...current, weekdays: Array.from(selected).sort() };
    });
  }

  async function submitSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    clearToast();
    try {
      const response = await fetch(academicRoutes.adminAcademicScheduleCreate, {
        method: "POST",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({
          group_id: Number(form.groupId),
          teacher_id: Number(form.teacherId || 0),
          title: form.title,
          weekdays: form.weekdays.map(Number),
          start_time: form.startTime,
          end_time: form.endTime,
          lesson_duration_minutes: Number(form.lessonDurationMinutes),
          start_date: form.startDate,
          end_date: form.endDate,
          room: form.room,
          online_url: form.onlineUrl,
        }),
      });
      const json = await response.json();
      if (!apiSucceeded(response, json)) {
        setError(apiErrorMessage(json, "Could not create schedule."));
        return;
      }
      const data = apiData<{
        schedule?: Record<string, unknown>;
        schedules?: ScheduleRow[];
        sessions?: SessionRow[];
        lessons?: LessonHistoryRow[];
      }>(json);
      setSchedules(Array.isArray(data.schedules) ? data.schedules : []);
      setSessions(Array.isArray(data.sessions) ? data.sessions : []);
      if (Array.isArray(data.lessons)) setLessons(data.lessons);
      void queryClient.invalidateQueries({ queryKey: ["academic", "timetable"] });
      showToast(`Schedule created. ${asNumber(data.schedule?.sessionCount)} lesson sessions generated.`);
      setCreateOpen(false);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      {pointerDrag?.moved ? (
        <div
          className={`pointer-events-none fixed z-[80] overflow-hidden rounded-md border px-1.5 py-1 text-[10px] shadow-2xl ring-2 ring-white/40 animate-in fade-in zoom-in-95 duration-100 motion-reduce:animate-none ${scheduleCardClass(pointerDrag.subjectName, pointerDrag.status)}`}
          style={{
            left: `${pointerDrag.x - pointerDrag.grabOffsetX}px`,
            top: `${pointerDrag.y - pointerDrag.grabOffsetY}px`,
            width: `${pointerDrag.previewWidth}px`,
            height: `${pointerDrag.previewHeight}px`,
          }}
        >
          <p className="truncate text-[0.62rem] font-black leading-tight tracking-wide">{pointerDrag.label}</p>
        </div>
      ) : null}
      <FloatingToast toast={toast} />
      <ChartCard
        title={isTeacherMode ? "Timetable" : "Academic Timetable"}
        subtitle={rangeLoading
          ? "Loading this timetable week…"
          : `${filteredSessions.length + placedTimetableBlocks.length} timed sessions · ${completedLessonCount} completed classes · ${cancelledLessonCount} cancelled · ${activeSchedules.length} active schedules`}
        icon={<CalendarDays className="h-4 w-4 text-info" />}
        headerActions={
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {!isTeacherMode ? (
              <button
                type="button"
                onClick={() => {
                  setError("");
                  clearToast();
                  setForm((current) => ({
                    ...current,
                    startDate: isoDate(weekStart),
                    endDate: isoDate(addDays(weekStart, 60)),
                  }));
                  setCreateOpen(true);
                }}
                className="inline-flex h-7 items-center gap-1.5 rounded-md bg-primary px-2.5 text-[11px] font-bold text-primary-foreground"
              >
                <Plus className="h-3 w-3" />
                Assign Time
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => setWeekStart((current) => addDays(current, -7))}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-foreground/10 hover:bg-muted"
              aria-label="Previous week"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setWeekStart(startOfWeek(new Date()))}
              className="h-7 rounded-md border border-foreground/10 px-2.5 text-[11px] font-bold hover:bg-muted"
            >
              This Week
            </button>
            <button
              type="button"
              onClick={() => setWeekStart((current) => addDays(current, 7))}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-foreground/10 hover:bg-muted"
              aria-label="Next week"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        }
      >
        {error ? (
          <p className="mb-2 rounded-md bg-destructive/10 px-2.5 py-1.5 text-[11px] font-semibold text-destructive">
            {error}
          </p>
        ) : null}
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <div className="inline-flex h-7 items-center gap-1.5 rounded-md bg-muted px-2.5 text-xs font-bold">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            {formatWeekRange(weekStart)}
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setFilterOpen((current) => !current)}
              className={`inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-[11px] font-bold ${activeFilterCount ? "border-primary/40 bg-primary/10 text-primary" : "border-foreground/10 bg-background hover:bg-muted"}`}
              aria-expanded={filterOpen}
            >
              <Filter className="h-3.5 w-3.5" />
              Filter
              {activeFilterCount ? (
                <span className="rounded-full bg-primary px-1.5 py-0.5 text-[9px] leading-none text-primary-foreground">
                  {activeFilterCount}
                </span>
              ) : null}
            </button>
            {filterOpen ? (
              <div className="inline-flex flex-wrap items-center gap-1.5 rounded-lg border border-foreground/10 bg-muted/40 p-1 shadow-sm animate-in fade-in slide-in-from-left-1 duration-150 motion-reduce:animate-none">
                <ScheduleFilterSelect label="Group filter" value={scheduleGroupFilter} onChange={setScheduleGroupFilter}>
                  <option value="all">All groups</option>
                  {filterOptions.groups.map((group) => (
                    <option key={group.value} value={group.value}>
                      {group.label}
                    </option>
                  ))}
                </ScheduleFilterSelect>
                <ScheduleFilterSelect label="Subject filter" value={scheduleSubjectFilter} onChange={setScheduleSubjectFilter}>
                  <option value="all">All subjects</option>
                  {filterOptions.subjects.map((subject) => (
                    <option key={subject} value={subject}>
                      {subject}
                    </option>
                  ))}
                </ScheduleFilterSelect>
                <ScheduleFilterSelect label="Status filter" value={scheduleStatusFilter} onChange={setScheduleStatusFilter}>
                  <option value="all">All statuses</option>
                  <option value="completed">Done</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="cancelled">Cancelled</option>
                </ScheduleFilterSelect>
                {activeFilterCount ? (
                  <button
                    type="button"
                    onClick={() => {
                      setScheduleGroupFilter("all");
                      setScheduleSubjectFilter("all");
                      setScheduleStatusFilter("all");
                    }}
                    className="inline-flex h-7 items-center gap-1 rounded-md bg-background px-2 text-[11px] font-bold text-muted-foreground shadow-sm hover:bg-foreground/10 hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                    Clear
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>

        <div
          ref={timetableScrollRef}
          className="miniapp-table-scroll rounded-lg border border-foreground/10 bg-background [scrollbar-gutter:stable]"
          onPointerDown={(event) => {
            const target = event.target as HTMLElement;
            if (!target.closest("[data-schedule-interactive='true']")) {
              setSelectedLessonId(null);
            }
          }}
          style={{
            height: `min(${gridViewportMaxPx}px, calc(var(--tg-app-height) - 8rem))`,
            maxHeight: `min(${gridViewportMaxPx}px, calc(var(--tg-app-height) - 8rem))`,
          }}
        >
          <div style={{ minWidth: `${gridMinWidthPx}px` }}>
            <div className="sticky top-0 z-40 grid border-b border-foreground/10 bg-muted/50 backdrop-blur" style={{ gridTemplateColumns }}>
              <div className="px-2 py-1.5 text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Time</div>
              {weekDays.map((day, index) => (
                <div key={isoDate(day)} className="border-l border-foreground/10 px-2 py-1.5">
                  <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">{weekdayLabels[index]}</p>
                  <p className="text-base font-bold leading-none">{day.getDate()}</p>
                </div>
              ))}
            </div>
            <div className="relative grid" style={{ gridTemplateColumns }}>
              <div className="relative border-r border-foreground/10 bg-muted/20" style={{ height: `${gridHeightPx}px` }}>
                {hours.map((hour) => (
                  <div
                    key={hour}
                    className="absolute left-0 right-0 border-t border-foreground/8 px-1.5 pt-1 text-right text-[10px] font-semibold text-muted-foreground"
                    style={{
                      top: `${(hour - displayStartHour) * hourPx}px`,
                      // Pull the final label above the bottom edge so it isn't clipped.
                      transform: hour === displayEndHour ? "translateY(-100%)" : undefined,
                    }}
                  >
                    {String(hour).padStart(2, "0")}:00
                  </div>
                ))}
              </div>
              {weekDays.map((day) => {
                  const dayIso = isoDate(day);
                  const daySessions = dayTimetableBlocks[dayIso] || [];
                  const hint = dropHint && dropHint.day === dayIso ? dropHint : null;
                  return (
                    <div
                      key={dayIso}
                      className="relative border-l border-foreground/10"
                      ref={(node) => {
                        dayColumnRefs.current[dayIso] = node;
                      }}
                      style={{ height: `${gridHeightPx}px` }}
                    >
                      {hours.map((hour) => (
                        <div
                          key={`${dayIso}-${hour}`}
                          className="absolute left-0 right-0 border-t border-foreground/8"
                          style={{ top: `${(hour - displayStartHour) * hourPx}px` }}
                        />
                      ))}
                      {daySessions.map((session) => {
                        const lessonId = Number(asString(session.id).replace(/^(session|lesson)-/, ""));
                        const isSelected = selectedLessonId === lessonId;
                        const activeResize = resizeDrag?.payload.id === lessonId ? resizeDrag : null;
                        const startMin = activeResize ? activeResize.previewStartMin : timeToMinutes(asString(session.start_time));
                        const endMin = activeResize ? activeResize.previewEndMin : timeToMinutes(asString(session.end_time));
                        const bandTop = ((session.bandStartMin - dayStartMin) / 60) * hourPx;
                        const bandHeight = Math.max(34, ((session.bandEndMin - session.bandStartMin) / 60) * hourPx);
                        const overlapGrid = overlapGridFor(session.rowCount);
                        const slotColumn = session.row % overlapGrid.columns;
                        const slotRow = Math.floor(session.row / overlapGrid.columns);
                        const rowHeight = Math.max(38, (bandHeight - 6) / overlapGrid.rows);
                        const columnWidth = 100 / overlapGrid.columns;
                        const exactTop = ((startMin - dayStartMin) / 60) * hourPx;
                        const exactHeight = Math.max(34, ((endMin - startMin) / 60) * hourPx - 2);
                        const useExactLayout = Boolean(activeResize);
                        const top = session.rowCount > 1 && !useExactLayout ? bandTop + slotRow * rowHeight : exactTop;
                        const height = session.rowCount > 1 && !useExactLayout ? rowHeight - 4 : exactHeight;
                        const left = session.rowCount > 1 ? `calc(${slotColumn * columnWidth}% + 4px)` : "4px";
                        const width = session.rowCount > 1 ? `calc(${columnWidth}% - 8px)` : undefined;
                        const toneLabel = session.status === "cancelled" ? "Cancelled" : session.status === "completed" ? "Done" : "Scheduled";
                        const compactCard = height < 52;
                        return (
                          <div
                            key={session.id}
                            onPointerDown={canDrag ? (event) => startPointerDrag(event, blockDragPayload(session), asString(session.group_name)) : undefined}
                            onPointerMove={canDrag ? movePointerDrag : undefined}
                            onPointerUp={canDrag ? endPointerDrag : undefined}
                            onPointerCancel={canDrag ? cancelPointerDrag : undefined}
                            data-schedule-interactive="true"
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                setSelectedLessonId(lessonId);
                              }
                            }}
                            tabIndex={0}
                            role="button"
                            aria-label={`${asString(session.group_name)} ${formatSessionTime(asString(session.start_time), asString(session.end_time))}`}
                            className={`absolute rounded-md border px-1.5 py-1 text-[10px] shadow-md transition-[box-shadow,filter] duration-150 hover:brightness-105 focus:outline-none ${isSelected ? "overflow-visible ring-2 ring-sky-300 ring-offset-1 ring-offset-background" : "overflow-hidden"} ${scheduleCardClass(session.subject_name, session.status)} ${canDrag ? "touch-none cursor-grab select-none active:cursor-grabbing" : ""}`}
                            style={{
                              top: `${Math.max(0, top)}px`,
                              height: `${Math.max(30, height)}px`,
                              left,
                              width,
                              right: session.rowCount > 1 ? undefined : "4px",
                              zIndex: isSelected ? 35 : session.rowCount > 1 ? 12 : 2,
                            }}
                          >
                            <div className="flex min-w-0 items-start justify-between gap-1">
                              <p className="truncate text-[clamp(0.56rem,0.8vw,0.68rem)] font-black leading-tight tracking-wide">{asString(session.group_name)}</p>
                            </div>
                            <p className="truncate text-[clamp(0.52rem,0.74vw,0.62rem)] font-semibold leading-tight text-white/90">{minutesToLabel(startMin)}–{minutesToLabel(endMin)}</p>
                            {!compactCard ? <p className="mt-0.5 inline-flex w-fit rounded-full bg-white/15 px-1 py-0.5 text-[8px] font-black uppercase leading-none tracking-wide text-white/85 ring-1 ring-white/20">{toneLabel}</p> : null}
                            {isSelected && canDrag ? (
                              <>
                                <button
                                  type="button"
                                  onPointerDown={(event) => startResizeDrag(event, session, "start")}
                                  onPointerMove={moveResizeDrag}
                                  onPointerUp={endResizeDrag}
                                  onPointerCancel={cancelResizeDrag}
                                  data-schedule-interactive="true"
                                  className="absolute inset-x-0 -top-1 z-30 h-3 cursor-ns-resize bg-transparent"
                                  aria-label="Adjust class start time"
                                />
                                <button
                                  type="button"
                                  onPointerDown={(event) => startResizeDrag(event, session, "end")}
                                  onPointerMove={moveResizeDrag}
                                  onPointerUp={endResizeDrag}
                                  onPointerCancel={cancelResizeDrag}
                                  data-schedule-interactive="true"
                                  className="absolute inset-x-0 -bottom-1 z-30 h-3 cursor-ns-resize bg-transparent"
                                  aria-label="Adjust class end time"
                                />
                              </>
                            ) : null}
                          </div>
                        );
                      })}
                      {hint ? (
                        <div
                          className="pointer-events-none absolute left-1 right-1 z-10 rounded-md border border-dashed border-primary/60 bg-primary/5 px-1.5 py-1"
                          style={{
                            top: `${((hint.startMin - dayStartMin) / 60) * hourPx}px`,
                            height: `${(hint.durationMin / 60) * hourPx - 2}px`,
                          }}
                        >
                          <p className="text-[9px] font-bold text-primary">
                            {minutesToLabel(hint.startMin)}–{minutesToLabel(hint.startMin + hint.durationMin)}
                          </p>
                        </div>
                      ) : null}
                    </div>
                  );
              })}
            </div>
          </div>
        </div>

        {visibleUntimedLessons.length ? (
          <section
            className="mt-3 rounded-xl border border-dashed border-amber-300/80 bg-amber-50/70 p-3 text-amber-950"
            aria-labelledby="unscheduled-lessons-title"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 shrink-0 text-amber-700" />
                  <h3 id="unscheduled-lessons-title" className="text-sm font-black">
                    Unscheduled
                  </h3>
                  <span className="rounded-full bg-amber-200/70 px-2 py-0.5 text-[10px] font-black tabular-nums">
                    {visibleUntimedLessons.length}
                  </span>
                </div>
                <p className="mt-1 text-xs font-semibold text-amber-900/80">
                  These lessons have a date but no real start or end time, so they are not shown on the timed grid.
                </p>
              </div>
              <p className="text-[11px] font-bold text-amber-800">
                {canDrag ? "Drag a card onto the timetable to assign its real time." : "Awaiting an assigned class time."}
              </p>
            </div>

            <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {weekDays.flatMap((day, dayIndex) => {
                const dayIso = isoDate(day);
                return (dayUntimedLessons[dayIso] || []).map((lesson) => {
                  const status = lessonStatus(lesson);
                  const selected = selectedLessonId === Number(lesson.id);
                  const groupName = asString(lesson.group_name) || "Group not set";
                  const subjectName = asString(lesson.subject_name) || "Subject not set";
                  return (
                    <article
                      key={`schedule-unscheduled-${lesson.id}`}
                      onPointerDown={canDrag ? (event) => startPointerDrag(event, lessonDragPayload(lesson), groupName) : undefined}
                      onPointerMove={canDrag ? movePointerDrag : undefined}
                      onPointerUp={canDrag ? endPointerDrag : undefined}
                      onPointerCancel={canDrag ? cancelPointerDrag : undefined}
                      onKeyDown={canDrag ? (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSelectedLessonId(Number(lesson.id));
                        }
                      } : undefined}
                      role={canDrag ? "button" : undefined}
                      tabIndex={canDrag ? 0 : undefined}
                      aria-label={`Unscheduled ${groupName}, ${subjectName}, ${dayIso}${canDrag ? ". Drag onto the timetable to assign a time." : "."}`}
                      className={`rounded-lg border bg-background p-3 text-foreground shadow-sm transition-[border-color,box-shadow] duration-150 motion-reduce:transition-none ${
                        status === "cancelled" ? "border-destructive/35" : "border-amber-300/80"
                      } ${selected ? "ring-2 ring-primary/40" : ""} ${canDrag ? "touch-none cursor-grab select-none hover:border-amber-500 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 active:cursor-grabbing" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-black">{groupName}</p>
                          <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{subjectName}</p>
                        </div>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-black uppercase tracking-wide ${
                          status === "cancelled" ? "bg-destructive/10 text-destructive" : "bg-amber-100 text-amber-800"
                        }`}>
                          {status === "cancelled" ? "Cancelled" : "No time"}
                        </span>
                      </div>
                      <p className="mt-2 text-[11px] font-bold text-muted-foreground">
                        {weekdayLabels[dayIndex]} · {dayIso} · Time not assigned
                      </p>
                      {asString(lesson.lesson_topic) ? (
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{asString(lesson.lesson_topic)}</p>
                      ) : null}
                    </article>
                  );
                });
              })}
            </div>
          </section>
        ) : null}
      </ChartCard>

      {createOpen ? (
        <div className="fixed inset-0 z-50 bg-foreground/45" onClick={() => setCreateOpen(false)} role="presentation">
          <aside
            className="flex h-full w-full max-w-md flex-col bg-surface shadow-card-hover"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="assign-class-time-title"
          >
            <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-5 py-4">
              <div>
                <h3 id="assign-class-time-title" className="text-base font-bold">Assign Class Time</h3>
                <p className="mt-1 text-xs text-muted-foreground">Creates a schedule rule and places matching past lessons by time.</p>
              </div>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                aria-label="Close schedule form"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form id="schedule-create-form" onSubmit={submitSchedule} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
              {error ? <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">{error}</p> : null}
              <label className="block">
                <FieldLabel>Group</FieldLabel>
                <Select value={form.groupId} onChange={(event) => updateField("groupId", event.target.value)} required>
                  {groups.map((group: Record<string, unknown>) => (
                    <option key={asNumber(group.id)} value={asString(group.id)}>
                      {asString(group.name)} · {asString(group.subject_name)} · {asString(group.school_code)}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block">
                <FieldLabel>Teacher</FieldLabel>
                <Select value={form.teacherId} onChange={(event) => updateField("teacherId", event.target.value)}>
                  <option value="">No teacher yet</option>
                  {teachers.map((teacher: Record<string, unknown>) => (
                    <option key={asNumber(teacher.id)} value={asString(teacher.id)}>
                      {asString(teacher.full_name)}
                    </option>
                  ))}
                </Select>
              </label>
              <label className="block">
                <FieldLabel>Title</FieldLabel>
                <TextInput value={form.title} onChange={(event) => updateField("title", event.target.value)} placeholder="Regular class" />
              </label>
              <div>
                <FieldLabel>Days</FieldLabel>
                <div className="grid grid-cols-7 gap-1">
                  {weekdayLabels.map((label, index) => {
                    const value = String(index);
                    const active = form.weekdays.includes(value);
                    return (
                      <button
                        key={label}
                        type="button"
                        onClick={() => toggleWeekday(value)}
                        className={`h-10 rounded-lg text-[11px] font-bold ${active ? "bg-foreground text-background" : "bg-muted text-muted-foreground hover:bg-foreground/10"}`}
                      >
                        {label.slice(0, 2)}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="block">
                  <FieldLabel>Start Time</FieldLabel>
                  <TextInput type="time" value={form.startTime} onChange={(event) => updateField("startTime", event.target.value)} required />
                </label>
                <label className="block">
                  <FieldLabel>Lesson Duration</FieldLabel>
                  <Select value={form.lessonDurationMinutes} onChange={(event) => updateField("lessonDurationMinutes", event.target.value)} required>
                    {[45, 60, 75, 90, 120].map((minutes) => <option key={minutes} value={minutes}>{minutes} minutes</option>)}
                  </Select>
                </label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="block">
                  <FieldLabel>Start Date</FieldLabel>
                  <TextInput type="date" value={form.startDate} onChange={(event) => updateField("startDate", event.target.value)} required />
                </label>
                <label className="block">
                  <FieldLabel>Predicted End Date</FieldLabel>
                  <TextInput type="date" value={form.endDate} onChange={(event) => updateField("endDate", event.target.value)} />
                  <span className="mt-1 block text-[11px] text-muted-foreground">Leave blank to calculate from the scheme of work.</span>
                </label>
              </div>
              <label className="block">
                <FieldLabel>Room</FieldLabel>
                <TextInput value={form.room} onChange={(event) => updateField("room", event.target.value)} placeholder="Room 2" />
              </label>
              <label className="block">
                <FieldLabel>Online Link</FieldLabel>
                <TextInput value={form.onlineUrl} onChange={(event) => updateField("onlineUrl", event.target.value)} placeholder="https://..." />
              </label>
            </form>
            <div className="border-t border-foreground/8 px-5 py-4">
              <button
                type="submit"
                form="schedule-create-form"
                disabled={submitting || !form.groupId || form.weekdays.length === 0}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-primary-foreground disabled:opacity-50"
              >
                <Plus className="h-4 w-4" />
                {submitting ? "Saving..." : "Save Time Rule"}
              </button>
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}
