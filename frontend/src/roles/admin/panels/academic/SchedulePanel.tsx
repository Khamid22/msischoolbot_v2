import { useState, useEffect, useMemo, useRef } from "react";
import type { DragEvent, FormEvent } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Clock, Plus, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, normalizeSubjectKey } from "../../shared";
import { jsonCsrfHeaders } from "@/shared/lib/api";
import { FieldLabel, TextInput, Select, weekdayLabels, timetableStartHour, timetableEndHour, isoDate, startOfWeek, addDays, formatWeekRange, timeToMinutes, formatSessionTime, lessonDateToIso, lessonStatus, subjectCode, subjectColorClass, scheduleTimeForLesson, sameSubjectName, ScheduleRow, SessionRow, LessonHistoryRow, RawTimetableBlock, layoutSessionsForDay } from "./shared";

// Fixed pixel height per hour keeps the grid readable at any range and makes
// drag placement math exact. The grid scrolls vertically inside the card.
const HOUR_PX = 64;
const SNAP_MINUTES = 10;
const DEFAULT_CLASS_MINUTES = 80;

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

function minutesToLabel(totalMinutes: number) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
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
  const dragPayloadRef = useRef<DragPayload | null>(null);
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
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
  const subjectOptions = useMemo(() => {
    const seen = new Set<string>();
    return groups
      .map((group: Record<string, unknown>) => asString(group.subject_name))
      .filter((subject: string) => {
        const key = normalizeSubjectKey(subject);
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .sort((left: string, right: string) => left.localeCompare(right));
  }, [groups]);

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
        if (subjectFilter !== "all" && !sameSubjectName(session.subject_name, subjectFilter)) return false;
        return true;
      }),
    [sessions, weekDateSet, subjectFilter, placedBlocks],
  );
  const recordedLessons = useMemo(
    () =>
      lessons.filter((lesson) => {
        if (timedSessionIds.has(Number(lesson.id))) return false;
        const lessonDate = lessonDateToIso(lesson.lesson_date);
        if (!lessonDate || !weekDateSet.has(lessonDate)) return false;
        if (asString(lesson.lesson_number).startsWith("S")) return false;
        if (subjectFilter !== "all" && !sameSubjectName(lesson.subject_name, subjectFilter)) return false;
        return true;
      }),
    [lessons, weekDateSet, subjectFilter, timedSessionIds],
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
        .filter((block) => subjectFilter === "all" || sameSubjectName(block.subject_name, subjectFilter))
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
    [placedBlocks, weekDateSet, subjectFilter],
  );
  const timetableBlocks = useMemo(
    () => [...scheduledBlocks, ...placedTimetableBlocks, ...timedHistoryBlocks],
    [scheduledBlocks, placedTimetableBlocks, timedHistoryBlocks],
  );
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
  const gridHeightPx = (displayEndHour - displayStartHour) * HOUR_PX;
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

  function startDrag(event: DragEvent, payload: DragPayload) {
    dragPayloadRef.current = payload;
    event.dataTransfer.effectAllowed = "move";
    // Firefox requires data for the drag to start.
    event.dataTransfer.setData("text/plain", String(payload.id));
  }

  function endDrag() {
    dragPayloadRef.current = null;
    setDropHint(null);
  }

  function snappedStartMinutes(event: DragEvent<HTMLDivElement>, durationMin: number) {
    const rect = event.currentTarget.getBoundingClientRect();
    const offsetY = event.clientY - rect.top;
    const rawMinutes = dayStartMin + (offsetY / HOUR_PX) * 60;
    const snapped = Math.round(rawMinutes / SNAP_MINUTES) * SNAP_MINUTES;
    return Math.max(dayStartMin, Math.min(snapped, dayEndMin - durationMin));
  }

  function handleColumnDragOver(event: DragEvent<HTMLDivElement>, dayIso: string) {
    const payload = dragPayloadRef.current;
    if (!payload) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    const startMin = snappedStartMinutes(event, payload.durationMin);
    setDropHint((current) =>
      current && current.day === dayIso && current.startMin === startMin
        ? current
        : { day: dayIso, startMin, durationMin: payload.durationMin },
    );
  }

  async function handleColumnDrop(event: DragEvent<HTMLDivElement>, dayIso: string) {
    const payload = dragPayloadRef.current;
    if (!payload) return;
    event.preventDefault();
    const startMin = snappedStartMinutes(event, payload.durationMin);
    const start = minutesToLabel(startMin);
    const end = minutesToLabel(startMin + payload.durationMin);
    endDrag();
    setError("");
    setMessage("");

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
      setMessage(`${optimistic.group_name} placed on ${dayIso} at ${start}–${end}.`);
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
    setMessage("");
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
      setMessage(`Schedule created. ${asNumber(data.schedule?.sessionCount)} lesson sessions generated.`);
      setCreateOpen(false);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
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
                  setMessage("");
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
        {message ? (
          <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700">
            {message}
          </p>
        ) : null}
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
          <Select value={subjectFilter} onChange={(event) => setSubjectFilter(event.target.value)} className="max-w-xs">
            <option value="all">All subjects</option>
            {subjectOptions.map((subject: string) => (
              <option key={subject} value={subject}>
                {subject}
              </option>
            ))}
          </Select>
        </div>
        {canDrag ? (
          <p className="mb-2 text-[11px] font-semibold text-muted-foreground">
            Drag any class card — including the unscheduled ones in the All-day row — onto the grid to set its day and time.
          </p>
        ) : null}

        <div className="miniapp-table-scroll rounded-lg border border-foreground/10 bg-background">
          <div className="min-w-[880px]">
            <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))] border-b border-foreground/10 bg-muted/40">
              <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Time</div>
              {weekDays.map((day, index) => (
                <div key={isoDate(day)} className="border-l border-foreground/10 px-3 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{weekdayLabels[index]}</p>
                  <p className="text-lg font-bold leading-none">{day.getDate()}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))] border-b border-foreground/10 bg-muted/15">
              <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                All-day
              </div>
              {weekDays.map((day) => {
                const dayIso = isoDate(day);
                const dayLessons = untimedLessons.filter((lesson) => lessonDateToIso(lesson.lesson_date) === dayIso);
                const completedCount = dayLessons.filter((lesson) => lessonStatus(lesson) === "completed").length;
                const cancelledCount = dayLessons.filter((lesson) => lessonStatus(lesson) === "cancelled").length;
                return (
                  <div key={`${dayIso}-classes`} className="min-h-[58px] border-l border-foreground/10 p-1.5">
                    {dayLessons.length === 0 ? (
                      <p className="pt-3 text-center text-[10px] font-semibold text-muted-foreground/40">—</p>
                    ) : (
                      <div className="space-y-1">
                        <div className="flex flex-wrap gap-1">
                          {completedCount ? (
                            <span className="rounded-md border border-emerald-500/20 bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-800">
                              {completedCount} completed
                            </span>
                          ) : null}
                          {cancelledCount ? (
                            <span className="rounded-md border border-red-500/20 bg-red-50 px-1.5 py-0.5 text-[9px] font-bold text-red-800">
                              {cancelledCount} cancelled
                            </span>
                          ) : null}
                        </div>
                        <div className="miniapp-scroll flex max-h-16 flex-wrap content-start gap-1 overflow-y-auto">
                          {dayLessons.map((lesson) => (
                            <span
                              key={`chip-${lesson.id}`}
                              draggable={canDrag}
                              onDragStart={canDrag ? (event) => startDrag(event, lessonDragPayload(lesson)) : undefined}
                              onDragEnd={canDrag ? endDrag : undefined}
                              title={`${asString(lesson.group_name)} · ${asString(lesson.lesson_number)} · ${asString(lesson.lesson_topic)}${canDrag ? "\nDrag onto the grid to set a time." : ""}`}
                              className={`rounded bg-white px-1.5 py-0.5 text-[9px] font-bold text-foreground/70 shadow-sm ${canDrag ? "cursor-grab active:cursor-grabbing" : ""}`}
                            >
                              {asString(lesson.group_name)} · {subjectCode(lesson.subject_name)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="miniapp-scroll max-h-[min(640px,calc(var(--tg-app-height)-16rem))] overflow-y-auto">
              <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))]">
                <div className="relative border-r border-foreground/10 bg-muted/20" style={{ height: `${gridHeightPx}px` }}>
                  {hours.map((hour) => (
                    <div
                      key={hour}
                      className="absolute left-0 right-0 border-t border-foreground/8 px-2 pt-1 text-right text-[11px] font-semibold text-muted-foreground"
                      style={{
                        top: `${(hour - displayStartHour) * HOUR_PX}px`,
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
                  const daySessions = layoutSessionsForDay(timetableBlocks.filter((session) => asString(session.session_date) === dayIso));
                  const hint = dropHint && dropHint.day === dayIso ? dropHint : null;
                  return (
                    <div
                      key={dayIso}
                      className="relative border-l border-foreground/10"
                      style={{ height: `${gridHeightPx}px` }}
                      onDragOver={canDrag ? (event) => handleColumnDragOver(event, dayIso) : undefined}
                      onDragLeave={canDrag ? () => setDropHint((current) => (current?.day === dayIso ? null : current)) : undefined}
                      onDrop={canDrag ? (event) => handleColumnDrop(event, dayIso) : undefined}
                    >
                      {hours.map((hour) => (
                        <div
                          key={`${dayIso}-${hour}`}
                          className="absolute left-0 right-0 border-t border-foreground/8"
                          style={{ top: `${(hour - displayStartHour) * HOUR_PX}px` }}
                        />
                      ))}
                      {daySessions.map((session) => {
                        const startMin = timeToMinutes(asString(session.start_time));
                        const endMin = timeToMinutes(asString(session.end_time));
                        const top = ((startMin - dayStartMin) / 60) * HOUR_PX;
                        const height = Math.max(26, ((endMin - startMin) / 60) * HOUR_PX);
                        // Overlapping classes sit side by side within the shared band.
                        const laneWidth = 100 / Math.max(1, session.rowCount);
                        const toneLabel = session.status === "cancelled" ? "Cancelled" : session.status === "completed" ? "Done" : "Scheduled";
                        return (
                          <div
                            key={session.id}
                            draggable={canDrag}
                            onDragStart={canDrag ? (event) => startDrag(event, blockDragPayload(session)) : undefined}
                            onDragEnd={canDrag ? endDrag : undefined}
                            className={`absolute overflow-hidden rounded-lg border p-2 text-xs shadow-card ${subjectColorClass(session.subject_name, session.status)} ${canDrag ? "cursor-grab active:cursor-grabbing" : ""}`}
                            style={{
                              top: `${Math.max(0, top)}px`,
                              height: `${height - 2}px`,
                              left: `calc(${session.row * laneWidth}% + 4px)`,
                              width: `calc(${laneWidth}% - 8px)`,
                            }}
                            title={[
                              asString(session.group_name),
                              asString(session.subject_name),
                              formatSessionTime(asString(session.start_time), asString(session.end_time)),
                              asString(session.lesson_number),
                              asString(session.lesson_topic),
                              asString(session.teacher_name),
                              canDrag ? "Drag to reschedule." : "",
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
                            top: `${((hint.startMin - dayStartMin) / 60) * HOUR_PX}px`,
                            height: `${(hint.durationMin / 60) * HOUR_PX - 2}px`,
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
