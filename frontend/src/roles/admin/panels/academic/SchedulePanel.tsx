import { useState, useEffect, useMemo, useRef } from "react";
import type { FormEvent, PointerEvent as ReactPointerEvent } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Clock, Plus, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString } from "../../shared";
import { jsonCsrfHeaders } from "@/shared/lib/api";
import { FieldLabel, TextInput, Select, weekdayLabels, timetableStartHour, timetableEndHour, isoDate, startOfWeek, addDays, formatWeekRange, timeToMinutes, formatSessionTime, lessonDateToIso, lessonStatus, subjectCode, subjectColorClass, scheduleTimeForLesson, ScheduleRow, SessionRow, LessonHistoryRow, RawTimetableBlock, TimetableLessonBlock, layoutSessionsForDay } from "./shared";

// The grid scales up when the week has many overlapping classes instead of
// squeezing those cards into unreadable strips.
const BASE_HOUR_PX = 64;
const SNAP_MINUTES = 10;
const DEFAULT_CLASS_MINUTES = 80;
const TIME_COLUMN_PX = 72;

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
  subject: string;
  moved: boolean;
};

function minutesToLabel(totalMinutes: number) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function overlapGridFor(count: number) {
  if (count <= 1) return { columns: 1, rows: 1 };
  const columns = Math.min(3, Math.max(2, Math.ceil(Math.sqrt(count))));
  return { columns, rows: Math.ceil(count / columns) };
}

function lessonScatterStyle(lesson: LessonHistoryRow, index: number, count: number) {
  const columns = 7;
  const rows = Math.max(4, Math.ceil(Math.max(count, 1) / columns));
  const column = index % columns;
  const row = Math.floor(index / columns);
  const seed = Math.abs(Number(lesson.id) || index + 1);
  const jitterX = ((seed * 17) % 9) - 4;
  const jitterY = ((seed * 23) % 9) - 4;
  const rotation = ((seed * 13) % 9) - 4;

  return {
    left: `${Math.min(96, Math.max(4, ((column + 0.5) / columns) * 100 + jitterX * 0.55))}%`,
    top: `${Math.min(92, Math.max(8, ((row + 0.5) / rows) * 100 + jitterY * 1.1))}%`,
    transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
  };
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
  const dayColumnRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const timetableScrollRef = useRef<HTMLDivElement | null>(null);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { toast, showToast, clearToast } = useFloatingToast();
  const [error, setError] = useState("");
  const today = isoDate(new Date());
  const [form, setForm] = useState({
    groupId: asString(groups[0]?.id),
    teacherId: "",
    title: "",
    weekdays: ["1", "3"],
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
      filteredSessions.map((session): RawTimetableBlock => ({
        id: `session-${session.id}`,
        group_id: Number(session.group_id),
        group_name: asString(session.group_name),
        subject_name: asString(session.subject_name),
        teacher_name: asString(session.teacher_name),
        session_date: lessonDateToIso(asString(session.session_date)) || asString(session.session_date),
        start_time: asString(session.start_time),
        end_time: asString(session.end_time),
        status: normalizeBlockStatus(session.status),
      })),
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
  const dayTimetableBlocks = useMemo(() => {
    const next: Record<string, TimetableLessonBlock[]> = {};
    weekDays.forEach((day) => {
      const dayIso = isoDate(day);
      next[dayIso] = layoutSessionsForDay(timetableBlocks.filter((session) => asString(session.session_date) === dayIso));
    });
    return next;
  }, [timetableBlocks, weekDays]);
  const dayUntimedLessons = useMemo(() => {
    const next: Record<string, LessonHistoryRow[]> = {};
    weekDays.forEach((day) => {
      const dayIso = isoDate(day);
      next[dayIso] = untimedLessons.filter((lesson) => lessonDateToIso(lesson.lesson_date) === dayIso);
    });
    return next;
  }, [untimedLessons, weekDays]);
  const freeformLessons = useMemo(
    () => weekDays.flatMap((day) => dayUntimedLessons[isoDate(day)] || []),
    [dayUntimedLessons, weekDays],
  );
  const busiestDayLoad = useMemo(() => {
    return weekDays.reduce((max, day) => {
      const dayIso = isoDate(day);
      return Math.max(max, (dayTimetableBlocks[dayIso] || []).length + (dayUntimedLessons[dayIso] || []).length);
    }, 0);
  }, [dayTimetableBlocks, dayUntimedLessons, weekDays]);
  const busiestOverlap = useMemo(() => {
    return weekDays.reduce((max, day) => {
      const dayIso = isoDate(day);
      return Math.max(max, ...(dayTimetableBlocks[dayIso] || []).map((session) => session.rowCount));
    }, 1);
  }, [dayTimetableBlocks, weekDays]);
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
  const hourPx = Math.min(148, BASE_HOUR_PX + Math.max(0, busiestOverlapGrid.rows - 1) * 18 + Math.max(0, Math.min(busiestDayLoad - 7, 8)) * 2);
  const dayMinWidthPx = Math.min(360, Math.max(140, 118 + Math.min(busiestDayLoad, 8) * 10 + Math.max(0, busiestOverlapGrid.columns - 1) * 58));
  const gridTemplateColumns = `${TIME_COLUMN_PX}px repeat(7, minmax(${dayMinWidthPx}px, 1fr))`;
  const gridMinWidthPx = TIME_COLUMN_PX + dayMinWidthPx * 7;
  const gridViewportMaxPx = Math.min(880, Math.max(620, 560 + Math.min(busiestDayLoad, 10) * 26));
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
      durationMin: DEFAULT_CLASS_MINUTES,
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

  function snappedStartMinutesFromRect(clientY: number, rect: DOMRect, durationMin: number) {
    const offsetY = clientY - rect.top;
    const rawMinutes = dayStartMin + (offsetY / hourPx) * 60;
    const snapped = Math.round(rawMinutes / SNAP_MINUTES) * SNAP_MINUTES;
    return Math.max(dayStartMin, Math.min(snapped, dayEndMin - durationMin));
  }

  function dropTargetAtPoint(clientX: number, clientY: number, durationMin: number) {
    for (const day of weekDays) {
      const dayIso = isoDate(day);
      const node = dayColumnRefs.current[dayIso];
      if (!node) continue;
      const rect = node.getBoundingClientRect();
      if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) continue;
      return {
        dayIso,
        startMin: snappedStartMinutesFromRect(clientY, rect, durationMin),
      };
    }
    return null;
  }

  function updateDropHint(clientX: number, clientY: number, payload: DragPayload) {
    const target = dropTargetAtPoint(clientX, clientY, payload.durationMin);
    if (!target) {
      setDropHint(null);
      return;
    }
    setDropHint((current) =>
      current && current.day === target.dayIso && current.startMin === target.startMin
        ? current
        : { day: target.dayIso, startMin: target.startMin, durationMin: payload.durationMin },
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

  async function placePayload(payload: DragPayload, dayIso: string, startMin: number) {
    const start = minutesToLabel(startMin);
    const end = minutesToLabel(startMin + payload.durationMin);
    setError("");
    clearToast();

    const previous = placedBlocks[payload.id];
    const optimistic: PlacedBlock = { id: payload.id, date: dayIso, start, end, ...payload.meta };
    setPlacedBlocks((current) => ({ ...current, [payload.id]: optimistic }));

    try {
      const response = await fetch(routes.adminAcademicLessonApi(payload.id), {
        method: "PATCH",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({ lesson_date: dayIso, start_time: start, end_time: end }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(asString(data.message) || "Could not move the class.");
      }
      showToast(`${optimistic.group_name} placed on ${dayIso} at ${start}–${end}.`);
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

  function startPointerDrag(event: ReactPointerEvent<HTMLElement>, payload: DragPayload, label: string, subject: string) {
    if (!canDrag) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    const next = {
      pointerId: event.pointerId,
      payload,
      startX: event.clientX,
      startY: event.clientY,
      x: event.clientX,
      y: event.clientY,
      label,
      subject,
      moved: false,
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
      updateDropHint(event.clientX, event.clientY, current.payload);
    }
  }

  function endPointerDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = pointerDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    event.preventDefault();
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    const target = dropTargetAtPoint(event.clientX, event.clientY, current.payload.durationMin);
    pointerDragRef.current = null;
    setPointerDrag(null);
    setDropHint(null);
    if (current.moved && target) {
      void placePayload(current.payload, target.dayIso, target.startMin);
    }
  }

  function cancelPointerDrag(event: ReactPointerEvent<HTMLElement>) {
    const current = pointerDragRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    pointerDragRef.current = null;
    setPointerDrag(null);
    setDropHint(null);
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
      const response = await fetch(routes.adminAcademicScheduleCreate, {
        method: "POST",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify({
          group_id: Number(form.groupId),
          teacher_id: Number(form.teacherId || 0),
          title: form.title,
          weekdays: form.weekdays.map(Number),
          start_time: form.startTime,
          end_time: form.endTime,
          start_date: form.startDate,
          end_date: form.endDate,
          room: form.room,
          online_url: form.onlineUrl,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        setError(asString(data.message) || "Could not create schedule.");
        return;
      }
      setSchedules(Array.isArray(data.schedules) ? data.schedules : []);
      setSessions(Array.isArray(data.sessions) ? data.sessions : []);
      if (Array.isArray(data.lessons)) setLessons(data.lessons);
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
          className="pointer-events-none fixed z-[80] rounded-lg border border-foreground/10 bg-surface px-3 py-2 text-xs font-bold text-foreground shadow-card-hover animate-in fade-in zoom-in-95 duration-100 motion-reduce:animate-none"
          style={{
            left: `${pointerDrag.x}px`,
            top: `${pointerDrag.y}px`,
            transform: "translate(12px, 12px)",
          }}
        >
          <div className="flex items-center gap-2">
            <span className="max-w-28 truncate">{pointerDrag.label}</span>
            <span className="rounded bg-muted px-1.5 py-0.5 text-[9px] text-muted-foreground">
              {subjectCode(pointerDrag.subject)}
            </span>
          </div>
        </div>
      ) : null}
      <FloatingToast toast={toast} />
      <ChartCard
        title={isTeacherMode ? "Timetable" : "Academic Timetable"}
        subtitle={`${filteredSessions.length + placedTimetableBlocks.length} timed sessions · ${completedLessonCount} completed classes · ${cancelledLessonCount} cancelled · ${activeSchedules.length} active schedules`}
        icon={<CalendarDays className="h-4 w-4 text-info" />}
        headerActions={
          <div className="flex flex-wrap items-center justify-end gap-2">
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
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground"
              >
                <Plus className="h-3.5 w-3.5" />
                Assign Time
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => setWeekStart((current) => addDays(current, -7))}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
              aria-label="Previous week"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setWeekStart(startOfWeek(new Date()))}
              className="h-8 rounded-lg border border-foreground/10 px-3 text-xs font-bold hover:bg-muted"
            >
              This Week
            </button>
            <button
              type="button"
              onClick={() => setWeekStart((current) => addDays(current, 7))}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
              aria-label="Next week"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        }
      >
        {error ? (
          <p className="mb-3 rounded-lg bg-destructive/10 px-3 py-2 text-xs font-semibold text-destructive">
            {error}
          </p>
        ) : null}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm font-bold">
            <Clock className="h-4 w-4 text-muted-foreground" />
            {formatWeekRange(weekStart)}
          </div>
        </div>

        <div className="miniapp-table-scroll rounded-lg border border-foreground/10 bg-background">
          <div style={{ minWidth: `${gridMinWidthPx}px` }}>
            <div className="grid border-b border-foreground/10 bg-muted/40" style={{ gridTemplateColumns }}>
              <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Time</div>
              {weekDays.map((day, index) => (
                <div key={isoDate(day)} className="border-l border-foreground/10 px-3 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{weekdayLabels[index]}</p>
                  <p className="text-lg font-bold leading-none">{day.getDate()}</p>
                </div>
              ))}
            </div>
            <div
              ref={timetableScrollRef}
              className="miniapp-scroll overflow-y-auto"
              style={{ maxHeight: `min(${gridViewportMaxPx}px, calc(var(--tg-app-height) - 14rem))` }}
            >
              <div className="relative grid" style={{ gridTemplateColumns }}>
                <div className="relative border-r border-foreground/10 bg-muted/20" style={{ height: `${gridHeightPx}px` }}>
                  {hours.map((hour) => (
                    <div
                      key={hour}
                      className="absolute left-0 right-0 border-t border-foreground/8 px-2 pt-1 text-right text-[11px] font-semibold text-muted-foreground"
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
                        const startMin = timeToMinutes(asString(session.start_time));
                        const endMin = timeToMinutes(asString(session.end_time));
                        const bandTop = ((session.bandStartMin - dayStartMin) / 60) * hourPx;
                        const bandHeight = Math.max(34, ((session.bandEndMin - session.bandStartMin) / 60) * hourPx);
                        const overlapGrid = overlapGridFor(session.rowCount);
                        const slotColumn = session.row % overlapGrid.columns;
                        const slotRow = Math.floor(session.row / overlapGrid.columns);
                        const rowHeight = Math.max(38, (bandHeight - 6) / overlapGrid.rows);
                        const columnWidth = 100 / overlapGrid.columns;
                        const top = session.rowCount > 1 ? bandTop + slotRow * rowHeight : ((startMin - dayStartMin) / 60) * hourPx;
                        const height = session.rowCount > 1 ? rowHeight - 4 : Math.max(34, ((endMin - startMin) / 60) * hourPx - 2);
                        const left = session.rowCount > 1 ? `calc(${slotColumn * columnWidth}% + 4px)` : "4px";
                        const width = session.rowCount > 1 ? `calc(${columnWidth}% - 8px)` : undefined;
                        const toneLabel = session.status === "cancelled" ? "Cancelled" : session.status === "completed" ? "Done" : "Scheduled";
                        return (
                          <div
                            key={session.id}
                            onPointerDown={canDrag ? (event) => startPointerDrag(event, blockDragPayload(session), asString(session.group_name), asString(session.subject_name)) : undefined}
                            onPointerMove={canDrag ? movePointerDrag : undefined}
                            onPointerUp={canDrag ? endPointerDrag : undefined}
                            onPointerCancel={canDrag ? cancelPointerDrag : undefined}
                            className={`absolute overflow-hidden rounded-lg border p-2 text-xs shadow-card transition-transform hover:-translate-y-0.5 ${subjectColorClass(session.subject_name, session.status)} ${canDrag ? "touch-none cursor-grab select-none active:cursor-grabbing" : ""}`}
                            style={{
                              top: `${Math.max(0, top)}px`,
                              height: `${Math.max(30, height)}px`,
                              left,
                              width,
                              right: session.rowCount > 1 ? undefined : "4px",
                            }}
                            title={[
                              asString(session.group_name),
                              asString(session.subject_name),
                              formatSessionTime(asString(session.start_time), asString(session.end_time)),
                              asString(session.lesson_number),
                              asString(session.lesson_topic),
                              asString(session.teacher_name),
                            ].filter(Boolean).join(" · ")}
                          >
                            <div className="flex min-w-0 items-start justify-between gap-1">
                              <p className="truncate font-bold leading-tight">{asString(session.group_name)}</p>
                              <span className="shrink-0 rounded bg-white/80 px-1 text-[9px] font-bold text-foreground/55">
                                {subjectCode(session.subject_name)}
                              </span>
                            </div>
                            <p className="truncate text-[11px] font-semibold opacity-90">{formatSessionTime(asString(session.start_time), asString(session.end_time))}</p>
                            <p className="truncate text-[10px] font-bold uppercase tracking-wide opacity-80">{toneLabel}</p>
                          </div>
                        );
                      })}
                      {hint ? (
                        <div
                          className="pointer-events-none absolute left-1 right-1 z-10 rounded-lg border-2 border-dashed border-primary/60 bg-primary/5 px-2 py-1"
                          style={{
                            top: `${((hint.startMin - dayStartMin) / 60) * hourPx}px`,
                            height: `${(hint.durationMin / 60) * hourPx - 2}px`,
                          }}
                        >
                          <p className="text-[10px] font-bold text-primary">
                            {minutesToLabel(hint.startMin)}–{minutesToLabel(hint.startMin + hint.durationMin)}
                          </p>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
                {freeformLessons.length ? (
                  <div className="pointer-events-none absolute inset-y-0 right-0 z-20" style={{ left: `${TIME_COLUMN_PX}px` }}>
                    {freeformLessons.map((lesson, index) => {
                      const status = lessonStatus(lesson);
                      const statusClass = status === "cancelled"
                        ? "border-red-500/20 bg-red-50 text-red-800 shadow-red-900/5"
                        : "border-emerald-500/20 bg-white text-foreground/75 shadow-emerald-900/5";
                      return (
                        <button
                          key={`schedule-loose-${lesson.id}`}
                          type="button"
                          onPointerDown={canDrag ? (event) => startPointerDrag(event, lessonDragPayload(lesson), asString(lesson.group_name), asString(lesson.subject_name)) : undefined}
                          onPointerMove={canDrag ? movePointerDrag : undefined}
                          onPointerUp={canDrag ? endPointerDrag : undefined}
                          onPointerCancel={canDrag ? cancelPointerDrag : undefined}
                          title={`${asString(lesson.group_name)} · ${asString(lesson.lesson_number)} · ${asString(lesson.lesson_topic)}`}
                          aria-label={`Place ${asString(lesson.group_name)} ${asString(lesson.lesson_number)}`}
                          className={`pointer-events-auto absolute flex max-w-[150px] touch-none select-none items-center gap-1 rounded-lg border px-2 py-1 text-left text-[10px] font-bold shadow-card transition-transform hover:-translate-y-0.5 ${statusClass} ${canDrag ? "cursor-grab active:cursor-grabbing" : ""}`}
                          style={lessonScatterStyle(lesson, index, freeformLessons.length)}
                        >
                          <span className="min-w-0 truncate">{asString(lesson.group_name)}</span>
                          <span className="shrink-0 rounded bg-muted px-1 text-[9px] text-muted-foreground">
                            {subjectCode(lesson.subject_name)}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </ChartCard>

      {createOpen ? (
        <div className="fixed inset-0 z-50 bg-foreground/45" onClick={() => setCreateOpen(false)}>
          <aside
            className="flex h-full w-full max-w-md flex-col bg-surface shadow-card-hover"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3 border-b border-foreground/8 px-5 py-4">
              <div>
                <h3 className="text-base font-bold">Assign Class Time</h3>
                <p className="mt-1 text-xs text-muted-foreground">Creates a schedule rule and places matching past lessons by time.</p>
              </div>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg hover:bg-muted"
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
                  <FieldLabel>End Time</FieldLabel>
                  <TextInput type="time" value={form.endTime} onChange={(event) => updateField("endTime", event.target.value)} required />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="block">
                  <FieldLabel>Start Date</FieldLabel>
                  <TextInput type="date" value={form.startDate} onChange={(event) => updateField("startDate", event.target.value)} required />
                </label>
                <label className="block">
                  <FieldLabel>End Date</FieldLabel>
                  <TextInput type="date" value={form.endDate} onChange={(event) => updateField("endDate", event.target.value)} required />
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
