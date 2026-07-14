import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Ban,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  MapPin,
  RotateCcw,
  Settings,
  UserRound,
} from "lucide-react";
import { routes } from "@/shared/lib/routes";
import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders } from "@/shared/lib/api";
import { queryClient } from "@/shared/api/queryClient";
import { motion } from "@/shared/lib/motion";
import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";
import { FloatingToast, useFloatingToast } from "@/shared/ui/FloatingToast";
import { calculateAdaptiveHourRange } from "./timetableMath";

type TimetableRoutes = Pick<
  typeof routes,
  | "adminAcademicGroupTimetableApi"
  | "adminAcademicLessonApi"
  | "adminAcademicLessonCancelApi"
  | "adminAcademicLessonRecoverApi"
>;

type TimetableRow = {
  id?: number;
  exception_id?: number;
  exception_key?: string;
  lesson_session_id?: number;
  lesson_number?: string;
  lesson_topic?: string;
  lesson_order?: number;
  session_date?: string;
  iso_date?: string;
  start_time?: string;
  end_time?: string;
  room?: string;
  status?: string;
  cancellation_reason?: string;
  has_academic_records?: boolean;
  is_cancellation?: boolean;
  can_recover?: boolean;
};

type ScheduleRow = {
  teacher_name?: string;
  weekdays?: string;
  start_time?: string;
  end_time?: string;
  room?: string;
};

type TimetablePayload = {
  from: string;
  to: string;
  range?: { from: string; to: string };
  activeSchedule?: ScheduleRow | null;
  schedules?: ScheduleRow[];
  sessions?: TimetableRow[];
  exceptions?: TimetableRow[];
  hasAcademicRecords?: boolean;
  unscheduledLessonCount?: number;
};

type TimetableItem = {
  key: string;
  lessonSessionId: number;
  exceptionId: number | null;
  lessonNumber: string;
  topic: string;
  order: number;
  isoDate: string;
  startTime: string;
  endTime: string;
  room: string;
  status: string;
  cancellationReason: string;
  isCancellation: boolean;
  canRecover: boolean;
  hasAcademicRecords: boolean;
};

type PrimaryMode = "agenda" | "calendar";
type CalendarMode = "week" | "month";
const SCHOOL_TIME_ZONE = "Asia/Tashkent";
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOUR_HEIGHT = 64;

function schoolTodayKey(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: SCHOOL_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value || "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function schoolNowMarker(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: SCHOOL_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(now);
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value || "";
  return `${value("year")}-${value("month")}-${value("day")}T${value("hour")}:${value("minute")}`;
}

function parseDateKey(value: string) {
  return new Date(`${value}T12:00:00`);
}

function dateKey(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function addDays(value: Date, amount: number) {
  const next = new Date(value);
  next.setDate(next.getDate() + amount);
  return next;
}

function startOfWeek(value: Date) {
  const weekday = (value.getDay() + 6) % 7;
  return addDays(value, -weekday);
}

function startOfMonth(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), 1, 12);
}

function endOfMonth(value: Date) {
  return new Date(value.getFullYear(), value.getMonth() + 1, 0, 12);
}

function shiftMonth(value: Date, amount: number) {
  return new Date(value.getFullYear(), value.getMonth() + amount, 1, 12);
}

function monthKey(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(value: Date) {
  return value.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function timeMinutes(value: string) {
  const [hour, minute] = value.split(":").map(Number);
  return Number.isFinite(hour) && Number.isFinite(minute) ? hour * 60 + minute : 0;
}

function rangeFor(mode: PrimaryMode, calendarMode: CalendarMode, cursorKey: string) {
  const cursor = parseDateKey(cursorKey);
  if (mode === "calendar" && calendarMode === "week") {
    const from = startOfWeek(cursor);
    return { from: dateKey(from), to: dateKey(addDays(from, 6)) };
  }
  if (mode === "calendar" && calendarMode === "month") {
    const from = startOfWeek(startOfMonth(cursor));
    return { from: dateKey(from), to: dateKey(addDays(from, 41)) };
  }
  return { from: dateKey(startOfMonth(cursor)), to: dateKey(endOfMonth(cursor)) };
}

function formatDay(value: string, withYear = false) {
  return parseDateKey(value).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: withYear ? "numeric" : undefined,
  });
}

function normalizeItem(row: TimetableRow, cancellation: boolean): TimetableItem {
  const exceptionId = Number(row.exception_id || 0) || null;
  const lessonSessionId = Number(row.lesson_session_id || row.id || 0);
  return {
    key: cancellation ? row.exception_key || `lesson-exception:${exceptionId}` : `lesson-session:${lessonSessionId}`,
    lessonSessionId,
    exceptionId,
    lessonNumber: String(row.lesson_number || "Lesson"),
    topic: String(row.lesson_topic || ""),
    order: Number(row.lesson_order || 0),
    isoDate: String(row.iso_date || ""),
    startTime: String(row.start_time || "").slice(0, 5),
    endTime: String(row.end_time || "").slice(0, 5),
    room: String(row.room || ""),
    status: cancellation ? "cancelled" : String(row.status || "scheduled"),
    cancellationReason: String(row.cancellation_reason || ""),
    isCancellation: cancellation,
    canRecover: cancellation && row.can_recover !== false,
    hasAcademicRecords: Boolean(row.has_academic_records),
  };
}

function scheduleSummary(schedule?: ScheduleRow | null) {
  const weekdayNames = String(schedule?.weekdays || "")
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((value) => value >= 0 && value <= 6)
    .map((value) => WEEKDAYS[value]);
  return {
    teacher: String(schedule?.teacher_name || "No teacher"),
    days: weekdayNames.join(", ") || "No days",
    time: schedule?.start_time
      ? `${String(schedule.start_time).slice(0, 5)}${schedule.end_time ? `–${String(schedule.end_time).slice(0, 5)}` : ""}`
      : "No time",
    room: String(schedule?.room || "No room"),
  };
}

function StatusBadge({ item }: { item: TimetableItem }) {
  if (item.isCancellation) {
    return <span className="rounded-full bg-red-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-red-700">Cancelled</span>;
  }
  if (item.hasAcademicRecords) {
    return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700"><CheckCircle2 className="h-3 w-3" />Recorded</span>;
  }
  return <span className="rounded-full bg-primary/8 px-2 py-1 text-[10px] font-bold text-primary">Scheduled</span>;
}

function AgendaView({ items, onOpen }: { items: TimetableItem[]; onOpen: (item: TimetableItem) => void }) {
  const today = schoolTodayKey();
  const now = schoolNowMarker();
  const nextKey = items.find((item) => !item.isCancellation && `${item.isoDate}T${item.startTime || "23:59"}` >= now)?.key;
  const grouped = useMemo(() => {
    const result = new Map<string, TimetableItem[]>();
    items.forEach((item) => result.set(item.isoDate, [...(result.get(item.isoDate) || []), item]));
    return [...result.entries()];
  }, [items]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = Number(sessionStorage.getItem("group-timetable-agenda-scroll") || 0);
    if (scrollRef.current && saved) scrollRef.current.scrollTop = saved;
  }, []);

  return (
    <div
      ref={scrollRef}
      onScroll={(event) => sessionStorage.setItem("group-timetable-agenda-scroll", String(event.currentTarget.scrollTop))}
      className="miniapp-scroll max-h-[68dvh] space-y-5 overflow-y-auto px-3 py-4 animate-in fade-in slide-in-from-bottom-1 duration-300 motion-reduce:animate-none sm:px-5"
    >
      {grouped.map(([day, lessons]) => {
        const isToday = day === today;
        return (
          <section key={day} aria-labelledby={`agenda-${day}`}>
            <div className="mb-2 flex items-center gap-2">
              <h4 id={`agenda-${day}`} className={`text-xs font-black uppercase tracking-wide ${isToday ? "text-primary" : "text-muted-foreground"}`}>
                {isToday ? "Today · " : ""}{formatDay(day, true)}
              </h4>
              <span className="h-px flex-1 bg-foreground/8" />
            </div>
            <div className="space-y-2">
              {lessons.map((item) => {
                const upcoming = item.key === nextKey;
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => onOpen(item)}
                    className={`grid min-h-16 w-full grid-cols-[4.6rem_minmax(0,1fr)_auto] items-center gap-3 rounded-xl border px-3 py-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
                      item.isCancellation
                        ? "border-red-200 bg-red-50/70 hover:bg-red-50"
                        : upcoming
                          ? "border-primary/30 bg-primary/5 hover:bg-primary/8"
                          : "border-foreground/8 bg-background hover:bg-muted/50"
                    }`}
                  >
                    <span className={`text-sm font-black ${item.isCancellation ? "text-red-700" : "text-foreground"}`}>{item.startTime || "—"}</span>
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="truncate text-sm font-bold">{item.lessonNumber}</span>
                        {upcoming ? <span className="text-[10px] font-bold uppercase tracking-wide text-primary">Next</span> : null}
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-muted-foreground">{item.topic || "No topic"}</span>
                      <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-semibold text-muted-foreground">
                        {item.endTime ? <span className="inline-flex items-center gap-1"><Clock3 className="h-3 w-3" />{item.startTime}–{item.endTime}</span> : null}
                        <span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" />{item.room || "Room not set"}</span>
                        {item.cancellationReason ? <span className="text-red-700">{item.cancellationReason}</span> : null}
                      </span>
                    </span>
                    <StatusBadge item={item} />
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function WeekCalendar({
  cursorKey,
  items,
  fullDay,
  onCursorChange,
  onOpen,
}: {
  cursorKey: string;
  items: TimetableItem[];
  fullDay: boolean;
  onCursorChange: (value: string) => void;
  onOpen: (item: TimetableItem) => void;
}) {
  const [mobile, setMobile] = useState(() => window.innerWidth < 768);
  useEffect(() => {
    const onResize = () => setMobile(window.innerWidth < 768);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  const weekStart = startOfWeek(parseDateKey(cursorKey));
  const weekDays = Array.from({ length: 7 }, (_, index) => addDays(weekStart, index));
  const visibleDays = mobile ? [parseDateKey(cursorKey)] : weekDays;
  const visibleItems = items.filter((item) => visibleDays.some((day) => dateKey(day) === item.isoDate));
  const adaptive = calculateAdaptiveHourRange(visibleItems);
  const hours = fullDay ? { startHour: 8, endHour: 22 } : adaptive;
  const totalHeight = (hours.endHour - hours.startHour) * HOUR_HEIGHT;
  const today = schoolTodayKey();

  return (
    <div className="animate-in fade-in duration-300 motion-reduce:animate-none">
      {mobile ? (
        <div className="grid grid-cols-7 border-b border-foreground/8 px-2 py-2">
          {weekDays.map((day) => {
            const key = dateKey(day);
            const selected = key === cursorKey;
            return (
              <button key={key} type="button" onClick={() => onCursorChange(key)} className={`min-h-11 rounded-lg text-center ${selected ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`}>
                <span className="block text-[9px] font-bold uppercase">{WEEKDAYS[(day.getDay() + 6) % 7]}</span>
                <span className="block text-xs font-black">{day.getDate()}</span>
              </button>
            );
          })}
        </div>
      ) : null}
      <div className="miniapp-table-scroll max-h-[68dvh] overflow-auto">
        <div className="min-w-[44rem]" style={{ minWidth: mobile ? "100%" : undefined }}>
          <div className="sticky top-0 z-20 grid border-b border-foreground/8 bg-surface/95 backdrop-blur" style={{ gridTemplateColumns: `3.5rem repeat(${visibleDays.length}, minmax(0,1fr))` }}>
            <div />
            {visibleDays.map((day) => {
              const key = dateKey(day);
              return <div key={key} className={`border-l border-foreground/8 px-2 py-2 text-center ${key === today ? "bg-primary/5 text-primary" : ""}`}><span className="block text-[9px] font-bold uppercase text-muted-foreground">{WEEKDAYS[(day.getDay() + 6) % 7]}</span><span className="text-sm font-black">{day.getDate()} {day.toLocaleDateString("en-US", { month: "short" })}</span></div>;
            })}
          </div>
          <div className="grid" style={{ gridTemplateColumns: `3.5rem repeat(${visibleDays.length}, minmax(0,1fr))` }}>
            <div className="relative bg-muted/15" style={{ height: totalHeight }}>
              {Array.from({ length: hours.endHour - hours.startHour + 1 }, (_, index) => (
                <span key={index} className="absolute right-2 text-[9px] font-semibold text-muted-foreground" style={{ top: index * HOUR_HEIGHT - 6 }}>{String(hours.startHour + index).padStart(2, "0")}:00</span>
              ))}
            </div>
            {visibleDays.map((day) => {
              const key = dateKey(day);
              const dayItems = items.filter((item) => item.isoDate === key && item.startTime && item.endTime);
              return (
                <div key={key} className="relative border-l border-foreground/8" style={{ height: totalHeight }}>
                  {Array.from({ length: hours.endHour - hours.startHour + 1 }, (_, index) => <span key={index} className="absolute inset-x-0 border-t border-foreground/8" style={{ top: index * HOUR_HEIGHT }} />)}
                  {dayItems.map((item) => {
                    const top = ((timeMinutes(item.startTime) - hours.startHour * 60) / 60) * HOUR_HEIGHT;
                    const height = Math.max(44, ((timeMinutes(item.endTime) - timeMinutes(item.startTime)) / 60) * HOUR_HEIGHT - 3);
                    if (top + height < 0 || top > totalHeight) return null;
                    return (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => onOpen(item)}
                        className={`absolute inset-x-1 z-10 overflow-hidden rounded-lg border px-2 py-1 text-left shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${item.isCancellation ? "border-red-300 bg-red-100 text-red-800" : "border-primary/25 bg-primary/10 text-primary"}`}
                        style={{ top: Math.max(1, top), height }}
                      >
                        <span className="block truncate text-[10px] font-black">{item.lessonNumber}</span>
                        <span className="block truncate text-[9px] font-semibold opacity-80">{item.topic || (item.isCancellation ? item.cancellationReason : "Scheduled lesson")}</span>
                        <span className="absolute bottom-1 left-2 text-[9px] font-bold">{item.startTime}–{item.endTime}</span>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function MonthCalendar({ cursorKey, items, onSelectDay }: { cursorKey: string; items: TimetableItem[]; onSelectDay: (value: string) => void }) {
  const cursor = parseDateKey(cursorKey);
  const gridStart = startOfWeek(startOfMonth(cursor));
  const days = Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));
  const today = schoolTodayKey();
  return (
    <div className="miniapp-table-scroll overflow-x-auto p-2 animate-in fade-in duration-300 motion-reduce:animate-none sm:p-4">
      <div className="min-w-[42rem]">
        <div className="grid grid-cols-7">{WEEKDAYS.map((day) => <div key={day} className="pb-2 text-center text-[10px] font-bold uppercase tracking-wide text-muted-foreground">{day}</div>)}</div>
        <div className="grid grid-cols-7 overflow-hidden rounded-xl border border-foreground/8">
          {days.map((day) => {
            const key = dateKey(day);
            const dayItems = items.filter((item) => item.isoDate === key);
            const cancellations = dayItems.filter((item) => item.isCancellation).length;
            const recorded = dayItems.filter((item) => item.hasAcademicRecords && !item.isCancellation).length;
            const outside = day.getMonth() !== cursor.getMonth();
            return (
              <button key={key} type="button" onClick={() => onSelectDay(key)} className={`min-h-24 border-b border-r border-foreground/8 p-2 text-left hover:bg-muted/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 ${outside ? "bg-muted/20 text-muted-foreground" : "bg-background"}`}>
                <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-black ${key === today ? "bg-primary text-primary-foreground" : ""}`}>{day.getDate()}</span>
                {dayItems.length ? <span className="mt-2 block text-xs font-bold">{dayItems.length} lesson{dayItems.length === 1 ? "" : "s"}</span> : null}
                <span className="mt-1 flex gap-1" aria-label={`${cancellations} cancelled, ${recorded} recorded`}>
                  {dayItems.slice(0, 4).map((item) => <span key={item.key} className={`h-2 w-2 rounded-full ${item.isCancellation ? "bg-red-500" : item.hasAcademicRecords ? "bg-emerald-500" : "bg-primary"}`} />)}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function LessonDetailsSheet({
  item,
  groupId,
  csrf,
  academicRoutes,
  onClose,
  onSaved,
}: {
  item: TimetableItem | null;
  groupId: number;
  csrf: string;
  academicRoutes: TimetableRoutes;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const [date, setDate] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [room, setRoom] = useState("");
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [flow, setFlow] = useState<"edit" | "cancel" | "recover">("edit");
  const [reason, setReason] = useState("");
  const [allowRecorded, setAllowRecorded] = useState(false);
  const [recordedConflict, setRecordedConflict] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const initialRef = useRef("");

  useEffect(() => {
    if (!item) return;
    setDate(item.isoDate);
    setStartTime(item.startTime);
    setEndTime(item.endTime);
    setRoom(item.room);
    setName(item.lessonNumber);
    setTopic(item.topic);
    setFlow(item.isCancellation ? "recover" : "edit");
    setReason("");
    setAllowRecorded(false);
    setRecordedConflict(false);
    setError("");
    initialRef.current = JSON.stringify({ date: item.isoDate, startTime: item.startTime, endTime: item.endTime, room: item.room, name: item.lessonNumber, topic: item.topic, flow: item.isCancellation ? "recover" : "edit", reason: "" });
  }, [item]);

  const currentSnapshot = JSON.stringify({ date, startTime, endTime, room, name, topic, flow, reason });
  const dirty = Boolean(item) && currentSnapshot !== initialRef.current;
  const requiresRecordedConfirmation = Boolean(item?.hasAcademicRecords || recordedConflict);

  function requestClose() {
    if (saving) return;
    if (dirty && !window.confirm("Discard your unsaved timetable changes?")) return;
    onClose();
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!item || saving) return;
    if (requiresRecordedConfirmation && !allowRecorded) {
      setError("Confirm that existing academic records must remain attached before continuing.");
      return;
    }
    if (flow === "edit") {
      if (!date || !startTime || !endTime || !name.trim()) {
        setError("Date, start time, end time, and lesson name are required.");
        return;
      }
      if (endTime <= startTime) {
        setError("End time must be after the start time.");
        return;
      }
    }
    if (flow === "cancel" && reason.trim().length < 3) {
      setError("Enter a cancellation reason of at least 3 characters.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const endpoint = flow === "edit"
        ? academicRoutes.adminAcademicLessonApi(item.lessonSessionId)
        : flow === "cancel"
          ? academicRoutes.adminAcademicLessonCancelApi(item.lessonSessionId)
          : academicRoutes.adminAcademicLessonRecoverApi(item.lessonSessionId);
      const body = flow === "edit"
        ? { date, start_time: startTime, end_time: endTime, room: room.trim(), lesson_name: name.trim(), topic: topic.trim(), allow_recorded_lesson_changes: allowRecorded }
        : flow === "cancel"
          ? { reason: reason.trim(), allow_recorded_lesson_changes: allowRecorded }
          : { allow_recorded_lesson_changes: allowRecorded };
      const response = await fetch(endpoint, {
        method: flow === "edit" ? "PATCH" : "POST",
        headers: jsonCsrfHeaders(csrf),
        body: JSON.stringify(body),
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) {
        const message = apiErrorMessage(json, "Unable to update this lesson.");
        if (response.status === 409 && /attendance|homework|record/i.test(message)) setRecordedConflict(true);
        setError(message);
        return;
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["academic", "timetable"] }),
        queryClient.invalidateQueries({ queryKey: ["academic", "gradebook"] }),
        queryClient.invalidateQueries({ queryKey: ["academic", "gradebook-trends", groupId] }),
      ]);
      onSaved(flow === "edit" ? "Lesson updated." : flow === "cancel" ? "Lesson cancelled and the timetable moved forward." : "Lesson recovered and the timetable restored.");
    } catch {
      setError("Network error while updating this lesson.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={Boolean(item)}
      onClose={requestClose}
      title={flow === "cancel" ? "Cancel lesson" : flow === "recover" ? "Recover lesson" : "Lesson details"}
      subtitle={item ? `${formatDay(item.isoDate, true)} · ${item.lessonNumber}` : undefined}
      size="md"
      desktopPlacement="right"
      mobileMode="fullscreen"
      closeOnOutsideClick={!saving}
      closeOnEscape={!saving}
      panelClassName="sm:max-w-md"
    >
      <form onSubmit={submit} className="flex min-h-0 flex-1 flex-col">
        <ModalBody className="space-y-4">
          {error ? <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">{error}</p> : null}
          {item?.hasAcademicRecords ? <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><span><strong>Academic records exist.</strong> Attendance and homework will stay attached to lesson ID {item.lessonSessionId}.</span></div> : null}
          {flow === "edit" ? (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Lesson date</span><input type="date" required value={date} onChange={(event) => setDate(event.target.value)} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
                <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Room</span><input value={room} onChange={(event) => setRoom(event.target.value)} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" placeholder="Room 2" /></label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Start time</span><input type="time" required value={startTime} onChange={(event) => setStartTime(event.target.value)} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
                <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">End time</span><input type="time" required value={endTime} onChange={(event) => setEndTime(event.target.value)} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
              </div>
              <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Lesson name</span><input required value={name} onChange={(event) => setName(event.target.value)} className="h-11 w-full rounded-lg border border-foreground/10 bg-background px-3 text-sm" /></label>
              <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Topic</span><textarea rows={4} value={topic} onChange={(event) => setTopic(event.target.value)} className="w-full resize-none rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm" /></label>
              <button type="button" onClick={() => { setFlow("cancel"); setError(""); }} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-red-200 text-sm font-bold text-red-700 hover:bg-red-50"><Ban className="h-4 w-4" />Cancel this lesson</button>
            </>
          ) : flow === "cancel" ? (
            <>
              <div className="rounded-lg border border-foreground/8 bg-muted/30 p-3"><p className="text-sm font-bold">{item?.lessonNumber}</p><p className="mt-1 text-xs text-muted-foreground">A cancelled placeholder stays here. This lesson and the following sequence move to the next valid teaching slots.</p></div>
              <label><span className="mb-1 block text-xs font-bold uppercase text-muted-foreground">Cancellation reason</span><textarea autoFocus required minLength={3} rows={4} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="For example: school closed" className="w-full resize-none rounded-lg border border-foreground/10 bg-background px-3 py-2 text-sm" /></label>
              <button type="button" onClick={() => { setFlow("edit"); setReason(""); setError(""); }} className="min-h-11 w-full rounded-lg bg-muted text-sm font-bold text-muted-foreground">Back to lesson details</button>
            </>
          ) : (
            <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950"><p className="font-bold">Restore {item?.lessonNumber} to {item ? formatDay(item.isoDate, true) : "its original date"}?</p><p className="text-xs">The active cancelled placeholder will disappear, later lessons move back, and the audit history remains.</p>{item?.cancellationReason ? <p className="text-xs"><strong>Cancellation reason:</strong> {item.cancellationReason}</p> : null}</div>
          )}
          {requiresRecordedConfirmation ? (
            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
              <input type="checkbox" checked={allowRecorded} onChange={(event) => setAllowRecorded(event.target.checked)} className="mt-0.5 h-4 w-4 accent-primary" />
              <span><strong>I understand this lesson has academic records.</strong><span className="mt-1 block text-xs">Keep every record attached to the same lesson while applying this timetable change.</span></span>
            </label>
          ) : null}
        </ModalBody>
        <ModalFooter className="flex justify-end gap-2">
          <button type="button" disabled={saving} onClick={requestClose} className="min-h-11 rounded-lg bg-muted px-4 text-sm font-bold text-muted-foreground disabled:opacity-50">Close</button>
          <button type="submit" disabled={saving || (requiresRecordedConfirmation && !allowRecorded) || (flow === "edit" && !dirty) || (flow === "cancel" && reason.trim().length < 3)} className={`min-h-11 rounded-lg px-5 text-sm font-bold text-white disabled:opacity-50 ${flow === "cancel" ? "bg-red-600" : flow === "recover" ? "bg-emerald-600" : "bg-primary"}`}>
            {saving ? "Saving…" : flow === "cancel" ? "Cancel & Move Forward" : flow === "recover" ? "Recover Lesson" : "Save Lesson"}
          </button>
        </ModalFooter>
      </form>
    </Modal>
  );
}

export function ModernGroupTimetable({
  groupId,
  csrf,
  academicRoutes,
  onChangeSchedule,
}: {
  groupId: number;
  csrf: string;
  academicRoutes: TimetableRoutes;
  onChangeSchedule: () => void;
}) {
  const [mode, setMode] = useState<PrimaryMode>("agenda");
  const [calendarMode, setCalendarMode] = useState<CalendarMode>("week");
  const [cursorKey, setCursorKey] = useState(schoolTodayKey);
  const [fullDay, setFullDay] = useState(false);
  const [selected, setSelected] = useState<TimetableItem | null>(null);
  const { toast, showToast } = useFloatingToast();
  const range = useMemo(() => rangeFor(mode, calendarMode, cursorKey), [mode, calendarMode, cursorKey]);
  const query = useQuery({
    queryKey: ["academic", "timetable", groupId, range.from, range.to],
    queryFn: async ({ signal }) => {
      const params = new URLSearchParams({ date_from: range.from, date_to: range.to });
      const response = await fetch(academicRoutes.adminAcademicGroupTimetableApi(groupId, params.toString()), {
        signal,
        cache: "no-store",
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const json = await response.json().catch(() => ({}));
      if (!apiSucceeded(response, json)) throw new Error(apiErrorMessage(json, "Unable to load the timetable."));
      return apiData<TimetablePayload>(json);
    },
  });
  const items = useMemo(() => [
    ...(query.data?.sessions || []).map((row) => normalizeItem(row, false)),
    ...(query.data?.exceptions || []).map((row) => normalizeItem(row, true)),
  ].filter((item) => item.isoDate).sort((left, right) => left.isoDate.localeCompare(right.isoDate) || left.startTime.localeCompare(right.startTime) || Number(left.isCancellation) - Number(right.isCancellation) || left.order - right.order), [query.data]);
  const schedule = query.data?.activeSchedule || query.data?.schedules?.[0] || null;
  const summary = scheduleSummary(schedule);
  const selectedMonth = monthKey(parseDateKey(cursorKey));
  const monthOptions = useMemo(() => {
    const center = startOfMonth(parseDateKey(cursorKey));
    return Array.from({ length: 73 }, (_, index) => shiftMonth(center, index - 36));
  }, [cursorKey]);

  function movePeriod(direction: -1 | 1) {
    const cursor = parseDateKey(cursorKey);
    if (mode === "calendar" && calendarMode === "week") setCursorKey(dateKey(addDays(cursor, direction * 7)));
    else setCursorKey(dateKey(shiftMonth(cursor, direction)));
  }

  function openWeek(day: string) {
    setCursorKey(day);
    setMode("calendar");
    setCalendarMode("week");
  }

  function selectMonth(value: string) {
    setCursorKey(`${value}-01`);
  }

  return (
    <>
      <section className="overflow-hidden rounded-2xl border border-foreground/8 bg-surface shadow-card">
        <div className="border-b border-foreground/8 px-4 py-4 sm:px-5">
          <div><h3 className="text-base font-black">Lesson Timetable</h3><p className="mt-0.5 text-xs text-muted-foreground">Timetable dates flow directly into the Gradebook.</p></div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 flex-wrap gap-2 text-[11px] font-semibold text-muted-foreground">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1.5"><UserRound className="h-3.5 w-3.5" />{summary.teacher}</span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1.5"><CalendarDays className="h-3.5 w-3.5" />{summary.days}</span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1.5"><Clock3 className="h-3.5 w-3.5" />{summary.time}</span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1.5"><MapPin className="h-3.5 w-3.5" />{summary.room}</span>
            </div>
            <button type="button" onClick={onChangeSchedule} className={`ml-auto inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 text-[11px] font-bold text-primary hover:bg-primary/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 sm:min-h-9 ${motion.button}`}><Settings className="h-3.5 w-3.5" />Configure</button>
          </div>
        </div>
        <div className="flex flex-col gap-3 border-b border-foreground/8 px-3 py-3 lg:flex-row lg:items-center lg:justify-between sm:px-5">
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={() => movePeriod(-1)} aria-label="Previous period" className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 sm:h-9 sm:w-9 ${motion.button}`}><ChevronLeft className="h-4 w-4" /></button>
            <label className="relative min-w-0">
              <span className="sr-only">Select timetable month</span>
              <CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <select value={selectedMonth} onChange={(event) => selectMonth(event.target.value)} className="h-11 w-[10.75rem] cursor-pointer appearance-none rounded-xl border border-foreground/10 bg-surface pl-10 pr-9 text-sm font-black text-foreground outline-none transition-colors hover:bg-muted/50 focus:border-primary/30 focus:ring-2 focus:ring-primary/20 sm:h-9 sm:w-[12rem]">
                {monthOptions.map((month) => <option key={monthKey(month)} value={monthKey(month)}>{monthLabel(month)}</option>)}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground" />
            </label>
            <button type="button" onClick={() => movePeriod(1)} aria-label="Next period" className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 sm:h-9 sm:w-9 ${motion.button}`}><ChevronRight className="h-4 w-4" /></button>
            <button type="button" onClick={() => setCursorKey(schoolTodayKey())} className={`min-h-11 rounded-lg border border-foreground/10 px-2.5 text-[11px] font-bold hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 sm:min-h-9 ${motion.button}`}>Today</button>
          </div>
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <div className="inline-flex rounded-lg border border-foreground/10 bg-muted/40 p-0.5">
              {(["agenda", "calendar"] as PrimaryMode[]).map((value) => <button key={value} type="button" aria-pressed={mode === value} onClick={() => setMode(value)} className={`min-h-11 rounded-md px-3 text-[11px] font-bold capitalize focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 sm:min-h-9 ${motion.button} ${mode === value ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>{value}</button>)}
            </div>
            {mode === "calendar" ? <div className="inline-flex rounded-lg border border-foreground/10 bg-muted/40 p-0.5">{(["week", "month"] as CalendarMode[]).map((value) => <button key={value} type="button" onClick={() => setCalendarMode(value)} aria-pressed={calendarMode === value} className={`min-h-11 rounded-md px-2.5 text-[11px] font-bold capitalize focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 sm:min-h-9 ${motion.button} ${calendarMode === value ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>{value}</button>)}</div> : null}
            {mode === "calendar" && calendarMode === "week" ? <button type="button" aria-pressed={fullDay} onClick={() => setFullDay((value) => !value)} className={`min-h-11 rounded-lg border px-2.5 text-[11px] font-bold focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 sm:min-h-9 ${motion.button} ${fullDay ? "border-primary/30 bg-primary/8 text-primary" : "border-foreground/10 text-muted-foreground"}`}>{fullDay ? "Adaptive hours" : "Show full day"}</button> : null}
          </div>
        </div>
        {Number(query.data?.unscheduledLessonCount || 0) > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-900">
            <span>{query.data?.unscheduledLessonCount} program lesson{query.data?.unscheduledLessonCount === 1 ? " is" : "s are"} not placed on the timetable.</span>
            <button type="button" onClick={onChangeSchedule} className="min-h-10 rounded-lg px-3 font-bold text-amber-950 hover:bg-amber-100">Review setup</button>
          </div>
        ) : null}
        {query.isPending ? (
          <div className="space-y-2 p-5" aria-label="Loading timetable"><div className="h-16 animate-pulse rounded-xl bg-muted" /><div className="h-16 animate-pulse rounded-xl bg-muted/70" /><div className="h-16 animate-pulse rounded-xl bg-muted/50" /></div>
        ) : query.isError ? (
          <div className="px-6 py-14 text-center"><AlertTriangle className="mx-auto h-7 w-7 text-red-600" /><p className="mt-2 text-sm font-bold">Timetable could not be loaded</p><p className="mt-1 text-xs text-muted-foreground">{query.error instanceof Error ? query.error.message : "Try again."}</p><button type="button" onClick={() => void query.refetch()} className="mt-4 min-h-11 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground">Try again</button></div>
        ) : !schedule ? (
          <div className="px-6 py-16 text-center"><CalendarDays className="mx-auto h-8 w-8 text-muted-foreground" /><p className="mt-3 text-sm font-bold">Timetable not configured</p><p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">Set teaching days and lesson time to place the subject program automatically.</p><button type="button" onClick={onChangeSchedule} className="mt-4 min-h-11 rounded-lg bg-primary px-4 text-sm font-bold text-primary-foreground">Set Up Timetable</button></div>
        ) : !items.length ? (
          <div className="px-6 py-14 text-center"><CalendarDays className="mx-auto h-7 w-7 text-muted-foreground" /><p className="mt-2 text-sm font-bold">No lessons in this period</p><p className="mt-1 text-xs text-muted-foreground">Use the arrows or Today to open another period.</p></div>
        ) : mode === "agenda" ? (
          <AgendaView items={items} onOpen={setSelected} />
        ) : calendarMode === "month" ? (
          <MonthCalendar cursorKey={cursorKey} items={items} onSelectDay={openWeek} />
        ) : (
          <WeekCalendar cursorKey={cursorKey} items={items} fullDay={fullDay} onCursorChange={setCursorKey} onOpen={setSelected} />
        )}
      </section>
      <LessonDetailsSheet item={selected} groupId={groupId} csrf={csrf} academicRoutes={academicRoutes} onClose={() => setSelected(null)} onSaved={(message) => { setSelected(null); showToast(message); }} />
      <FloatingToast toast={toast} />
    </>
  );
}
