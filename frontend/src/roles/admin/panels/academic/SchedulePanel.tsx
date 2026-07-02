import { useState, useEffect, useMemo } from "react";
import type { FormEvent } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Clock, Plus, X } from "lucide-react";
import { ChartCard } from "@/shared/ui/ChartCard";
import { routes } from "@/shared/lib/routes";
import { asNumber, asString, normalizeSubjectKey } from "../../shared";
import { jsonCsrfHeaders } from "@/shared/lib/api";
import { FieldLabel, TextInput, Select, weekdayLabels, timetableStartHour, timetableEndHour, isoDate, startOfWeek, addDays, formatWeekRange, timeToMinutes, formatSessionTime, lessonDateToIso, lessonStatus, subjectCode, subjectColorClass, scheduleTimeForLesson, sameSubjectName, ScheduleRow, SessionRow, LessonHistoryRow, RawTimetableBlock, layoutSessionsForDay } from "./shared";

export function SchedulePanel({ state }: { state: any }) {
  const props = state.props || {};
  const csrf: string = asString(props.csrfToken);
  const isTeacherMode = asString(state.adminMode).toLowerCase() === "teacher";
  const groups = Array.isArray(props.adminAcademicGroups) ? props.adminAcademicGroups : [];
  const teachers = Array.isArray(props.adminTeachers) ? props.adminTeachers : [];
  const initialSchedules = Array.isArray(props.adminAcademicSchedules) ? props.adminAcademicSchedules : [];
  const initialSessions = Array.isArray(props.adminAcademicSessions) ? props.adminAcademicSessions : [];
  const initialLessons = Array.isArray(props.adminAcademicLessons) ? props.adminAcademicLessons : [];
  const [schedules, setSchedules] = useState<ScheduleRow[]>(initialSchedules as ScheduleRow[]);
  const [sessions, setSessions] = useState<SessionRow[]>(initialSessions as SessionRow[]);
  const [lessons, setLessons] = useState<LessonHistoryRow[]>(initialLessons as LessonHistoryRow[]);
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
  const filteredSessions = useMemo(
    () =>
      sessions.filter((session) => {
        if (!weekDateSet.has(asString(session.session_date))) return false;
        if (subjectFilter !== "all" && !sameSubjectName(session.subject_name, subjectFilter)) return false;
        return true;
      }),
    [sessions, weekDateSet, subjectFilter],
  );
  const recordedLessons = useMemo(
    () =>
      lessons.filter((lesson) => {
        const lessonDate = lessonDateToIso(lesson.lesson_date);
        if (!lessonDate || !weekDateSet.has(lessonDate)) return false;
        if (asString(lesson.lesson_number).startsWith("S")) return false;
        if (subjectFilter !== "all" && !sameSubjectName(lesson.subject_name, subjectFilter)) return false;
        return true;
      }),
    [lessons, weekDateSet, subjectFilter],
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
        const normalizedStatus = asString(session.status).toLowerCase();
        const status = normalizedStatus === "cancelled" || normalizedStatus === "canceled"
          ? "cancelled"
          : normalizedStatus === "completed" || normalizedStatus === "complete" || normalizedStatus === "done" || normalizedStatus === "accomplished"
            ? "completed"
            : "scheduled";
        return {
          id: `session-${session.id}`,
          group_id: Number(session.group_id),
          group_name: asString(session.group_name),
          subject_name: asString(session.subject_name),
          teacher_name: asString(session.teacher_name),
          session_date: asString(session.session_date),
          start_time: asString(session.start_time),
          end_time: asString(session.end_time),
          status,
        };
      }),
    [filteredSessions],
  );
  const timetableBlocks = useMemo(
    () => [...scheduledBlocks, ...timedHistoryBlocks],
    [scheduledBlocks, timedHistoryBlocks],
  );
  const completedLessonCount = recordedLessons.filter((lesson) => lessonStatus(lesson) === "completed").length;
  const cancelledLessonCount = recordedLessons.filter((lesson) => lessonStatus(lesson) === "cancelled").length
    + filteredSessions.filter((session) => ["cancelled", "canceled"].includes(asString(session.status).toLowerCase())).length;
  const activeSchedules = schedules.filter((schedule) => asString(schedule.status) !== "cancelled");
  // Fit the visible hour range to the actual lessons so the grid isn't mostly empty.
  const { displayStartHour, displayEndHour } = useMemo(() => {
    let earliest = Infinity;
    let latest = -Infinity;
    for (const block of timetableBlocks) {
      const start = timeToMinutes(asString(block.start_time));
      const end = timeToMinutes(asString(block.end_time));
      if (Number.isFinite(start)) earliest = Math.min(earliest, start);
      if (Number.isFinite(end)) latest = Math.max(latest, end);
    }
    if (!Number.isFinite(earliest) || !Number.isFinite(latest)) {
      return { displayStartHour: timetableStartHour, displayEndHour: 18 };
    }
    const startHour = Math.max(timetableStartHour, Math.floor(earliest / 60));
    let endHour = Math.min(timetableEndHour, Math.ceil(latest / 60));
    // Keep a sensible minimum span so a day with one short class still reads as a calendar.
    if (endHour - startHour < 6) endHour = Math.min(timetableEndHour, startHour + 6);
    return { displayStartHour: startHour, displayEndHour: endHour };
  }, [timetableBlocks]);
  const hours = Array.from({ length: displayEndHour - displayStartHour + 1 }, (_item, index) => displayStartHour + index);

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
        subtitle={`${filteredSessions.length} upcoming sessions · ${completedLessonCount} completed classes · ${cancelledLessonCount} cancelled · ${activeSchedules.length} active schedules`}
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
                const subjectCounts = dayLessons.reduce<Record<string, number>>((acc, lesson) => {
                  const code = subjectCode(lesson.subject_name);
                  acc[code] = (acc[code] || 0) + 1;
                  return acc;
                }, {});
                return (
                  <div key={`${dayIso}-classes`} className="min-h-[58px] border-l border-foreground/10 p-1.5">
                    {dayLessons.length === 0 ? (
                      <p className="pt-3 text-center text-[10px] font-semibold text-muted-foreground/40">—</p>
                    ) : (
                      <div
                        className="space-y-1"
                        title={dayLessons
                          .slice(0, 12)
                          .map((lesson) => `${asString(lesson.group_name)} · ${asString(lesson.lesson_number)} · ${asString(lesson.lesson_topic)}`)
                          .join("\n")}
                      >
                        {completedCount ? (
                          <div className="rounded-md border border-emerald-500/20 bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-800">
                            {completedCount} completed
                          </div>
                        ) : null}
                        {cancelledCount ? (
                          <div className="rounded-md border border-red-500/20 bg-red-50 px-2 py-1 text-[10px] font-bold text-red-800">
                            {cancelledCount} cancelled
                          </div>
                        ) : null}
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(subjectCounts).slice(0, 3).map(([code, count]) => (
                            <span key={code} className="rounded bg-white px-1.5 py-0.5 text-[9px] font-bold text-foreground/60">
                              {code} {count}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="grid grid-cols-[72px_repeat(7,minmax(0,1fr))]">
              <div className="relative h-[min(720px,calc(var(--tg-app-height)-9rem))] min-h-[34rem] border-r border-foreground/10 bg-muted/20">
                {hours.map((hour) => (
                  <div
                    key={hour}
                    className="absolute left-0 right-0 border-t border-foreground/8 px-2 pt-1 text-right text-[11px] font-semibold text-muted-foreground"
                    style={{
                      top: `${((hour - displayStartHour) / (displayEndHour - displayStartHour)) * 100}%`,
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
                return (
                  <div key={dayIso} className="relative h-[min(720px,calc(var(--tg-app-height)-9rem))] min-h-[34rem] border-l border-foreground/10">
                    {hours.map((hour) => (
                      <div
                        key={`${dayIso}-${hour}`}
                        className="absolute left-0 right-0 border-t border-foreground/8"
                        style={{ top: `${((hour - displayStartHour) / (displayEndHour - displayStartHour)) * 100}%` }}
                      />
                    ))}
                    {daySessions.map((session) => {
                      const spanMinutes = (displayEndHour - displayStartHour) * 60;
                      // Overlapping classes share a band and stack as full-width rows.
                      const bandTop = ((session.bandStartMin - displayStartHour * 60) / spanMinutes) * 100;
                      const bandHeight = ((session.bandEndMin - session.bandStartMin) / spanMinutes) * 100;
                      const rowHeight = bandHeight / Math.max(1, session.rowCount);
                      const top = bandTop + session.row * rowHeight;
                      // Keep a readable floor for single blocks; stacked rows use their share of the band.
                      const height = session.rowCount > 1 ? rowHeight : Math.max(7, rowHeight);
                      const toneLabel = session.status === "cancelled" ? "Cancelled" : session.status === "completed" ? "Done" : "Scheduled";
                      return (
                        <div
                          key={session.id}
                          className={`absolute overflow-hidden rounded-lg border p-2 text-xs shadow-card ${subjectColorClass(session.subject_name, session.status)}`}
                          style={{
                            top: `${Math.max(0, top)}%`,
                            height: `calc(${Math.max(0, height)}% - 2px)`,
                            left: "4px",
                            right: "4px",
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
                  </div>
                );
              })}
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
