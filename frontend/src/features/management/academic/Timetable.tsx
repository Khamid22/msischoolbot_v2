import { forwardRef, useEffect, useMemo, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { Ban, ChevronLeft, ChevronRight, Clock, MapPin, Pencil, RotateCcw, X } from "lucide-react";
import { motion } from "@/shared/lib/motion";
import { Lesson, addDays, isoDate, startOfWeek, timeToMinutes, timetableEndHour, timetableStartHour, weekdayLabels } from "./shared";

/**
 * Presentational building blocks for the group Timetable tab. These components
 * are intentionally decoupled from data fetching / persistence — the parent
 * (GroupGradebook) owns lesson data, API calls, and date-grouping logic, and
 * passes already-derived values in as props. View/navigation state (which
 * day/week/month is on screen) is pure UI state and lives locally in
 * TimetableCard.
 */

export type TimetableDateGroup = {
  key: string;
  iso: string;
  display: string;
  weekday: string;
  lessons: Lesson[];
};

type ViewMode = "day" | "week" | "month";

const MOBILE_BREAKPOINT_PX = 640;

function useIsMobileViewport(breakpointPx = MOBILE_BREAKPOINT_PX) {
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== "undefined" && window.innerWidth < breakpointPx,
  );
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < breakpointPx);
    handler();
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, [breakpointPx]);
  return isMobile;
}

/* ------------------------------- Toolbar -------------------------------- */

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function shiftCursor(view: ViewMode, cursor: Date, direction: 1 | -1): Date {
  if (view === "day") return addDays(cursor, direction);
  if (view === "week") return addDays(cursor, direction * 7);
  const next = new Date(cursor);
  next.setMonth(next.getMonth() + direction);
  return next;
}

function periodLabel(view: ViewMode, cursor: Date): string {
  if (view === "day") {
    return cursor.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  }
  if (view === "month") {
    return cursor.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  }
  return startOfWeek(cursor).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function TimetableToolbar({
  view,
  onViewChange,
  cursor,
  onCursorChange,
}: {
  view: ViewMode;
  onViewChange: (view: ViewMode) => void;
  cursor: Date;
  onCursorChange: (date: Date) => void;
}) {
  const todayLabel = view === "day" ? "Today" : view === "week" ? "This Week" : "This Month";
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-foreground/8 px-4 py-3">
      <p className="text-sm font-bold">{periodLabel(view, cursor)}</p>
      <div className="flex flex-wrap items-center gap-1.5">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onCursorChange(shiftCursor(view, cursor, -1))}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
            aria-label={`Previous ${view}`}
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => onCursorChange(new Date())}
            className="h-9 rounded-lg border border-foreground/10 px-3 text-xs font-bold hover:bg-muted"
          >
            {todayLabel}
          </button>
          <button
            type="button"
            onClick={() => onCursorChange(shiftCursor(view, cursor, 1))}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 hover:bg-muted"
            aria-label={`Next ${view}`}
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
        <div className="inline-flex rounded-lg border border-foreground/10 bg-muted/40 p-0.5">
          {(["day", "week", "month"] as ViewMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onViewChange(mode)}
              aria-pressed={view === mode}
              className={`h-8 rounded-md px-3 text-xs font-bold capitalize transition-colors ${
                view === mode ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* --------------------------- Week / Day grid ----------------------------- */

const HOUR_PX = 64;
const TIME_COL_PX = 52;
const DAY_COL_MIN_PX = 132;

type PositionedLesson = { lesson: Lesson; row: number; rowCount: number; startMin: number; endMin: number };

// Group-scoped overlaps are rare (usually 0-1 lesson/day) but this still
// clusters same-time-band lessons into side-by-side columns when they happen.
function layoutTimedLessons(lessons: Lesson[]): PositionedLesson[] {
  const sorted = [...lessons].sort(
    (a, b) => timeToMinutes(a.startTime || "") - timeToMinutes(b.startTime || ""),
  );
  const output: PositionedLesson[] = [];
  let cluster: Lesson[] = [];
  let clusterEnd = -1;
  function flush() {
    if (cluster.length === 0) return;
    const rowCount = cluster.length;
    cluster.forEach((lesson, index) => {
      output.push({
        lesson,
        row: index,
        rowCount,
        startMin: timeToMinutes(lesson.startTime || ""),
        endMin: timeToMinutes(lesson.endTime || ""),
      });
    });
    cluster = [];
    clusterEnd = -1;
  }
  sorted.forEach((lesson) => {
    const start = timeToMinutes(lesson.startTime || "");
    const end = timeToMinutes(lesson.endTime || "");
    if (cluster.length > 0 && start >= clusterEnd) flush();
    cluster.push(lesson);
    clusterEnd = Math.max(clusterEnd, end);
  });
  flush();
  return output;
}

function GridLessonCard({
  lesson,
  top,
  height,
  left,
  width,
  cancelled,
  canEdit,
  onOpenTime,
  onOpenRoom,
  onEditLesson,
  onCancelLesson,
  onRecoverLesson,
}: {
  lesson: Lesson;
  top: number;
  height: number;
  left: string;
  width: string;
  cancelled: boolean;
  canEdit: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>) => void;
  onOpenRoom: (e: ReactMouseEvent<HTMLButtonElement>) => void;
  onEditLesson: () => void;
  onCancelLesson: () => void;
  onRecoverLesson: () => void;
}) {
  const compact = height < 56;
  const hasTime = Boolean(lesson.startTime && lesson.endTime);
  const timeLabel = hasTime ? `${lesson.startTime}–${lesson.endTime}` : "";
  return (
    <div
      className={`absolute flex flex-col overflow-hidden rounded-lg border px-1.5 py-1 shadow-sm ${
        cancelled ? "border-red-300 bg-red-500 text-white" : "border-primary/25 bg-primary/10 text-primary"
      }`}
      style={{ top, height, left, width }}
      title={`${lesson.lessonNumber}${lesson.topic ? ` · ${lesson.topic}` : ""}`}
    >
      <p className="truncate text-[10.5px] font-black leading-tight">{lesson.lessonNumber}</p>
      {!compact && lesson.topic ? (
        <p className={`truncate text-[9.5px] font-medium leading-tight ${cancelled ? "text-white/85" : "text-primary/75"}`}>
          {lesson.topic}
        </p>
      ) : null}
      {cancelled ? (
        <div className="mt-auto flex items-center justify-between gap-1">
          <p className="truncate text-[9px] font-bold uppercase tracking-wide">Cancelled</p>
          {canEdit && lesson.canRecover ? <button type="button" onClick={onRecoverLesson} title="Recover lesson" className="rounded p-1 hover:bg-white/20"><RotateCcw className="h-3 w-3" /></button> : null}
        </div>
      ) : (
        <div className="mt-auto flex flex-wrap items-center gap-x-1.5 gap-y-0.5 pt-0.5">
          {canEdit ? (
            <button
              type="button"
              onClick={onOpenTime}
              title={`${lesson.lessonNumber} · edit class time`}
              className="inline-flex items-center gap-0.5 rounded px-0.5 text-[9px] font-bold hover:bg-primary/20"
            >
              <Clock className="h-2.5 w-2.5 shrink-0" />
              {timeLabel || "Set time"}
            </button>
          ) : timeLabel ? (
            <span className="inline-flex items-center gap-0.5 text-[9px] font-semibold opacity-85">
              <Clock className="h-2.5 w-2.5 shrink-0" />
              {timeLabel}
            </span>
          ) : null}
          {canEdit ? (
            <button
              type="button"
              onClick={onOpenRoom}
              title={`${lesson.lessonNumber} · edit room`}
              className="inline-flex min-w-0 items-center gap-0.5 truncate rounded px-0.5 text-[9px] font-bold hover:bg-primary/20"
            >
              <MapPin className="h-2.5 w-2.5 shrink-0" />
              <span className="min-w-0 truncate">{lesson.room || "Set room"}</span>
            </button>
          ) : lesson.room ? (
            <span className="inline-flex min-w-0 items-center gap-0.5 truncate text-[9px] font-semibold opacity-85">
              <MapPin className="h-2.5 w-2.5 shrink-0" />
              <span className="min-w-0 truncate">{lesson.room}</span>
            </span>
          ) : null}
          {canEdit ? <span className="ml-auto inline-flex gap-0.5"><button type="button" onClick={onEditLesson} title="Edit lesson content" className="rounded p-0.5 hover:bg-primary/20"><Pencil className="h-2.5 w-2.5" /></button><button type="button" onClick={onCancelLesson} title="Cancel lesson" className="rounded p-0.5 text-red-700 hover:bg-red-100"><Ban className="h-2.5 w-2.5" /></button></span> : null}
        </div>
      )}
    </div>
  );
}

function TimetableDayColumn({
  group,
  dayStartMin,
  dayEndMin,
  isLessonCancelled,
  canEdit,
  onOpenTime,
  onOpenRoom,
  onEditLesson,
  onCancelLesson,
  onRecoverLesson,
}: {
  group: TimetableDateGroup | undefined;
  dayStartMin: number;
  dayEndMin: number;
  isLessonCancelled: (lesson: Lesson) => boolean;
  canEdit: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onOpenRoom: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onEditLesson: (lesson: Lesson) => void;
  onCancelLesson: (lesson: Lesson) => void;
  onRecoverLesson: (lesson: Lesson) => void;
}) {
  const timed = (group?.lessons ?? []).filter((lesson) => lesson.startTime && lesson.endTime);
  const positioned = useMemo(() => layoutTimedLessons(timed), [timed]);
  const gridHeight = ((dayEndMin - dayStartMin) / 60) * HOUR_PX;
  const hourCount = Math.floor((dayEndMin - dayStartMin) / 60);

  return (
    <div className="relative border-l border-foreground/10" style={{ height: gridHeight }}>
      {Array.from({ length: hourCount + 1 }, (_, index) => (
        <div key={index} className="absolute left-0 right-0 border-t border-foreground/8" style={{ top: index * HOUR_PX }} />
      ))}
      {positioned.map(({ lesson, row, rowCount, startMin, endMin }) => {
        const top = ((startMin - dayStartMin) / 60) * HOUR_PX;
        const height = Math.max(44, ((endMin - startMin) / 60) * HOUR_PX - 2);
        const width = rowCount > 1 ? `calc(${100 / rowCount}% - 4px)` : "calc(100% - 4px)";
        const left = rowCount > 1 ? `calc(${(row * 100) / rowCount}% + 2px)` : "2px";
        return (
          <GridLessonCard
            key={lesson.id}
            lesson={lesson}
            top={Math.max(0, top)}
            height={height}
            left={left}
            width={width}
            cancelled={isLessonCancelled(lesson)}
            canEdit={canEdit}
            onOpenTime={(e) => onOpenTime(e, lesson)}
            onOpenRoom={(e) => onOpenRoom(e, lesson)}
            onEditLesson={() => onEditLesson(lesson)}
            onCancelLesson={() => onCancelLesson(lesson)}
            onRecoverLesson={() => onRecoverLesson(lesson)}
          />
        );
      })}
    </div>
  );
}

function UnscheduledDayCell({
  lessons,
  canEdit,
  onOpenTime,
  onOpenRoom,
}: {
  lessons: Lesson[];
  canEdit: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onOpenRoom: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
}) {
  if (lessons.length === 0) return <div className="border-l border-foreground/10" />;
  return (
    <div className="space-y-1 border-l border-foreground/10 px-1.5 py-1.5">
      {lessons.map((lesson) => (
        <div key={lesson.id} className="rounded-lg border border-dashed border-foreground/20 bg-background px-1.5 py-1">
          <p className="truncate text-[9.5px] font-bold">{lesson.lessonNumber}</p>
          {canEdit ? (
            <div className="mt-0.5 flex flex-wrap items-center gap-1">
              <button
                type="button"
                onClick={(e) => onOpenTime(e, lesson)}
                title={`${lesson.lessonNumber} · set class time`}
                className="inline-flex items-center gap-0.5 rounded-full border border-primary/25 bg-primary/8 px-1.5 py-0.5 text-[9px] font-bold text-primary hover:bg-primary/15"
              >
                <Clock className="h-2.5 w-2.5" />
                Set time
              </button>
              <button
                type="button"
                onClick={(e) => onOpenRoom(e, lesson)}
                title={`${lesson.lessonNumber} · set room`}
                className="inline-flex min-w-0 items-center gap-0.5 truncate rounded-full border border-foreground/12 bg-background px-1.5 py-0.5 text-[9px] font-bold text-muted-foreground hover:bg-muted"
              >
                <MapPin className="h-2.5 w-2.5 shrink-0" />
                <span className="min-w-0 truncate">{lesson.room || "Set room"}</span>
              </button>
            </div>
          ) : (
            <span className="mt-0.5 block text-[9px] font-semibold text-muted-foreground">
              No time set{lesson.room ? ` · ${lesson.room}` : ""}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function TimetableTimeGrid({
  days,
  groupsByIso,
  isLessonCancelled,
  canEdit,
  onOpenTime,
  onOpenRoom,
  onEditLesson,
  onCancelLesson,
  onRecoverLesson,
}: {
  days: Date[];
  groupsByIso: Map<string, TimetableDateGroup>;
  isLessonCancelled: (lesson: Lesson) => boolean;
  canEdit: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onOpenRoom: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onEditLesson: (lesson: Lesson) => void;
  onCancelLesson: (lesson: Lesson) => void;
  onRecoverLesson: (lesson: Lesson) => void;
}) {
  const dayStartMin = timetableStartHour * 60;
  const dayEndMin = timetableEndHour * 60;
  const hours = Array.from({ length: timetableEndHour - timetableStartHour + 1 }, (_, index) => timetableStartHour + index);
  const dayCount = days.length;
  const todayIso = isoDate(new Date());
  const gridTemplateColumns =
    dayCount === 1 ? `${TIME_COL_PX}px 1fr` : `${TIME_COL_PX}px repeat(${dayCount}, minmax(${DAY_COL_MIN_PX}px, 1fr))`;

  const dayEntries = days.map((day) => {
    const iso = isoDate(day);
    const group = groupsByIso.get(iso);
    const untimed = (group?.lessons ?? []).filter(
      (lesson) => !(lesson.startTime && lesson.endTime) && !isLessonCancelled(lesson),
    );
    return { day, iso, group, untimed };
  });
  const hasAnyUnscheduled = dayEntries.some((entry) => entry.untimed.length > 0);

  return (
    <div className="miniapp-table-scroll min-h-0 flex-1 [scrollbar-gutter:stable]">
      <div style={{ minWidth: dayCount === 1 ? undefined : TIME_COL_PX + dayCount * DAY_COL_MIN_PX }}>
        <div
          className="sticky top-0 z-20 grid border-b border-foreground/10 bg-surface/95 backdrop-blur"
          style={{ gridTemplateColumns }}
        >
          <div className="px-2 py-2 text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Time</div>
          {dayEntries.map(({ day, iso }) => {
            const isToday = iso === todayIso;
            return (
              <div key={iso} className={`border-l border-foreground/10 px-2 py-2 text-center ${isToday ? "bg-primary/5" : ""}`}>
                <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
                  {weekdayLabels[(day.getDay() + 6) % 7]}
                </p>
                <p className={`text-sm font-black leading-tight ${isToday ? "text-primary" : ""}`}>
                  {day.getDate()} {day.toLocaleDateString("en-US", { month: "short" })}
                </p>
              </div>
            );
          })}
        </div>
        {hasAnyUnscheduled ? (
          <div className="grid border-b border-foreground/10 bg-muted/20" style={{ gridTemplateColumns }}>
            <div className="px-2 py-1.5 text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Unscheduled</div>
            {dayEntries.map(({ iso, untimed }) => (
              <UnscheduledDayCell key={iso} lessons={untimed} canEdit={canEdit} onOpenTime={onOpenTime} onOpenRoom={onOpenRoom} />
            ))}
          </div>
        ) : null}
        <div className="grid" style={{ gridTemplateColumns }}>
          <div className="relative border-r border-foreground/10 bg-muted/10" style={{ height: ((dayEndMin - dayStartMin) / 60) * HOUR_PX }}>
            {hours.map((hour) => (
              <div
                key={hour}
                className="absolute left-0 right-0 border-t border-foreground/8 px-1.5 pt-1 text-right text-[9px] font-semibold text-muted-foreground"
                style={{
                  top: (hour - timetableStartHour) * HOUR_PX,
                  transform: hour === timetableEndHour ? "translateY(-100%)" : undefined,
                }}
              >
                {String(hour).padStart(2, "0")}:00
              </div>
            ))}
          </div>
          {dayEntries.map(({ iso, group }) => (
            <TimetableDayColumn
              key={iso}
              group={group}
              dayStartMin={dayStartMin}
              dayEndMin={dayEndMin}
              isLessonCancelled={isLessonCancelled}
              canEdit={canEdit}
              onOpenTime={onOpenTime}
              onOpenRoom={onOpenRoom}
              onEditLesson={onEditLesson}
              onCancelLesson={onCancelLesson}
              onRecoverLesson={onRecoverLesson}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/* --------------------------------- Month --------------------------------- */

function TimetableMonthView({
  cursor,
  groupsByIso,
  isLessonCancelled,
  canEdit,
  onOpenTime,
  onSelectDay,
}: {
  cursor: Date;
  groupsByIso: Map<string, TimetableDateGroup>;
  isLessonCancelled: (lesson: Lesson) => boolean;
  canEdit: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onSelectDay: (day: Date) => void;
}) {
  const days = useMemo(() => {
    const gridStart = startOfWeek(startOfMonth(cursor));
    return Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));
  }, [cursor]);
  const monthIndex = cursor.getMonth();
  const todayIso = isoDate(new Date());

  return (
    <div className="miniapp-table-scroll min-h-0 flex-1 p-3 [scrollbar-gutter:stable]">
      <div className="grid grid-cols-7 gap-1.5">
        {weekdayLabels.map((label) => (
          <div key={label} className="px-1 pb-1 text-center text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
        ))}
        {days.map((day) => {
          const iso = isoDate(day);
          const inMonth = day.getMonth() === monthIndex;
          const isToday = iso === todayIso;
          const lessons = groupsByIso.get(iso)?.lessons ?? [];
          const visible = lessons.slice(0, 2);
          const overflow = lessons.length - visible.length;
          return (
            <div
              key={iso}
              className={`min-h-[5.5rem] rounded-lg border p-1 ${inMonth ? "border-foreground/8 bg-background" : "border-transparent bg-muted/20"}`}
            >
              <button
                type="button"
                onClick={() => onSelectDay(day)}
                className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                  isToday ? "bg-primary text-primary-foreground" : inMonth ? "text-foreground hover:bg-muted" : "text-muted-foreground/50"
                }`}
              >
                {day.getDate()}
              </button>
              <div className="mt-1 space-y-0.5">
                {visible.map((lesson) => {
                  const cancelled = isLessonCancelled(lesson);
                  const hasTime = Boolean(lesson.startTime && lesson.endTime);
                  return (
                    <button
                      key={lesson.id}
                      type="button"
                      disabled={!canEdit || cancelled}
                      onClick={(e) => onOpenTime(e, lesson)}
                      title={`${lesson.lessonNumber}${hasTime ? ` · ${lesson.startTime}–${lesson.endTime}` : ""}`}
                      className={`block w-full truncate rounded px-1 py-0.5 text-left text-[9px] font-bold ${
                        cancelled ? "bg-red-100 text-red-700" : hasTime ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {hasTime ? `${lesson.startTime} ` : ""}
                      {lesson.lessonNumber}
                    </button>
                  );
                })}
                {overflow > 0 ? (
                  <button
                    type="button"
                    onClick={() => onSelectDay(day)}
                    className="block w-full truncate rounded px-1 py-0.5 text-left text-[9px] font-bold text-muted-foreground hover:text-foreground"
                  >
                    +{overflow} more
                  </button>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ----------------------------- Top-level card ----------------------------- */

export function TimetableCard({
  groups,
  isLessonCancelled,
  canEdit = true,
  onOpenTime,
  onOpenRoom,
  onEditLesson,
  onCancelLesson,
  onRecoverLesson,
}: {
  groups: TimetableDateGroup[];
  isLessonCancelled: (lesson: Lesson) => boolean;
  canEdit?: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onOpenRoom: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onEditLesson: (lesson: Lesson) => void;
  onCancelLesson: (lesson: Lesson) => void;
  onRecoverLesson: (lesson: Lesson) => void;
}) {
  const [view, setView] = useState<ViewMode>("week");
  const [cursor, setCursor] = useState<Date>(() => new Date());

  const firstScheduledIso = useMemo(
    () => groups.map((group) => group.iso).filter(Boolean).sort()[0] || "",
    [groups],
  );

  useEffect(() => {
    if (!firstScheduledIso) return;
    const firstLessonDate = new Date(`${firstScheduledIso}T00:00:00`);
    if (!Number.isNaN(firstLessonDate.getTime())) setCursor(firstLessonDate);
  }, [firstScheduledIso]);

  const groupsByIso = useMemo(() => {
    const map = new Map<string, TimetableDateGroup>();
    groups.forEach((group) => {
      if (group.iso) map.set(group.iso, group);
    });
    return map;
  }, [groups]);

  const undatedCount = groups.find((group) => !group.iso)?.lessons.length ?? 0;
  const datedLessonCount = groups.reduce((sum, group) => sum + (group.iso ? group.lessons.length : 0), 0);

  const days = useMemo(() => {
    if (view === "day") return [cursor];
    if (view === "week") {
      const start = startOfWeek(cursor);
      return Array.from({ length: 7 }, (_, index) => addDays(start, index));
    }
    return [];
  }, [view, cursor]);

  return (
    <div
      className={`flex min-h-0 flex-col overflow-hidden rounded-2xl border border-foreground/8 bg-surface shadow-card ${motion.panel}`}
      style={{
        height: "calc(var(--tg-app-height) - 11rem)",
        maxHeight: "78dvh",
        minHeight: "26rem",
      }}
    >
      <div className="shrink-0 px-4 pt-4">
        <p className="text-sm font-bold">Timetable</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {canEdit ? "Scheduled program lessons with class time and room · tap to edit" : "Scheduled program lessons with class time and room"}
        </p>
      </div>
      <TimetableToolbar view={view} onViewChange={setView} cursor={cursor} onCursorChange={setCursor} />
      {undatedCount > 0 ? (
        <p className="shrink-0 border-b border-foreground/8 bg-amber-50 px-4 py-1.5 text-[11px] font-semibold text-amber-800">
          {undatedCount} lesson{undatedCount > 1 ? "s" : ""} not yet placed — configure them from Timetable setup.
        </p>
      ) : null}
      {datedLessonCount === 0 ? (
        <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
          No timetable lessons yet.
        </div>
      ) : view === "month" ? (
        <TimetableMonthView
          cursor={cursor}
          groupsByIso={groupsByIso}
          isLessonCancelled={isLessonCancelled}
          canEdit={canEdit}
          onOpenTime={onOpenTime}
          onSelectDay={(day) => {
            setCursor(day);
            setView("day");
          }}
        />
      ) : (
        <TimetableTimeGrid
          days={days}
          groupsByIso={groupsByIso}
          isLessonCancelled={isLessonCancelled}
          canEdit={canEdit}
          onOpenTime={onOpenTime}
          onOpenRoom={onOpenRoom}
          onEditLesson={onEditLesson}
          onCancelLesson={onCancelLesson}
          onRecoverLesson={onRecoverLesson}
        />
      )}
    </div>
  );
}

/* --------------------------------- Popovers -------------------------------- */

type PopoverPosition = { top: number; left: number };

function PopoverShell({
  lesson,
  dateLabel,
  saving,
  onClose,
  children,
}: {
  lesson: Lesson;
  dateLabel: string;
  saving: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <>
      <div className="flex min-w-0 items-start justify-between gap-3 border-b border-foreground/8 px-4 py-3.5">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold">{lesson.lessonNumber}</p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{dateLabel}</p>
        </div>
        <button
          type="button"
          disabled={saving}
          onClick={onClose}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-muted disabled:opacity-40"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {children}
    </>
  );
}

function popoverContainerClass(isMobile: boolean) {
  return isMobile
    ? "fixed inset-x-0 bottom-0 z-[9999] w-full rounded-t-2xl border-t border-foreground/10 bg-surface shadow-xl animate-in slide-in-from-bottom duration-200 motion-reduce:animate-none"
    : "fixed z-[9999] w-[300px] max-w-[calc(100vw-1.5rem)] rounded-2xl border border-foreground/10 bg-surface shadow-xl animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none";
}

function PopoverActions({
  saving,
  onClear,
  onSave,
}: {
  saving: boolean;
  onClear: () => void;
  onSave: () => void;
}) {
  return (
    <div className="flex gap-2 pt-1">
      <button
        type="button"
        disabled={saving}
        onClick={onClear}
        className="h-10 shrink-0 rounded-full border border-foreground/12 bg-background px-4 text-xs font-bold text-muted-foreground hover:bg-muted disabled:opacity-50"
      >
        Clear
      </button>
      <button
        type="button"
        disabled={saving}
        onClick={onSave}
        className="h-10 flex-1 rounded-full bg-primary px-4 text-xs font-bold text-primary-foreground shadow-sm hover:opacity-90 disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </div>
  );
}

export const TimePopover = forwardRef<
  HTMLDivElement,
  {
    lesson: Lesson;
    dateLabel: string;
    position: PopoverPosition;
    startValue: string;
    endValue: string;
    onStartChange: (value: string) => void;
    onEndChange: (value: string) => void;
    onClear: () => void;
    onSave: () => void;
    onClose: () => void;
    saving: boolean;
  }
>(function TimePopover(
  { lesson, dateLabel, position, startValue, endValue, onStartChange, onEndChange, onClear, onSave, onClose, saving },
  ref,
) {
  const isMobile = useIsMobileViewport();
  return (
    <>
      {isMobile ? (
        <div
          className="fixed inset-0 z-[9998] bg-foreground/40 animate-in fade-in duration-150 motion-reduce:animate-none"
          onClick={saving ? undefined : onClose}
        />
      ) : null}
      <div
        ref={ref}
        style={isMobile ? undefined : { top: position.top, left: position.left }}
        className={popoverContainerClass(isMobile)}
      >
        <PopoverShell lesson={lesson} dateLabel={dateLabel} saving={saving} onClose={onClose}>
          <div className={`space-y-3 p-4 ${isMobile ? "pb-[max(1rem,env(safe-area-inset-bottom))]" : ""}`}>
            <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Class Time</p>
            <div className="flex items-center gap-2">
              <input
                type="time"
                value={startValue}
                onChange={(e) => onStartChange(e.target.value)}
                className="h-11 w-full min-w-0 rounded-xl border border-foreground/10 bg-background px-3 text-sm outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
              />
              <span className="shrink-0 text-xs font-semibold text-muted-foreground">–</span>
              <input
                type="time"
                value={endValue}
                onChange={(e) => onEndChange(e.target.value)}
                className="h-11 w-full min-w-0 rounded-xl border border-foreground/10 bg-background px-3 text-sm outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
              />
            </div>
            <PopoverActions saving={saving} onClear={onClear} onSave={onSave} />
          </div>
        </PopoverShell>
      </div>
    </>
  );
});

export const RoomPopover = forwardRef<
  HTMLDivElement,
  {
    lesson: Lesson;
    dateLabel: string;
    position: PopoverPosition;
    value: string;
    onChange: (value: string) => void;
    onClear: () => void;
    onSave: () => void;
    onClose: () => void;
    saving: boolean;
  }
>(function RoomPopover({ lesson, dateLabel, position, value, onChange, onClear, onSave, onClose, saving }, ref) {
  const isMobile = useIsMobileViewport();
  return (
    <>
      {isMobile ? (
        <div
          className="fixed inset-0 z-[9998] bg-foreground/40 animate-in fade-in duration-150 motion-reduce:animate-none"
          onClick={saving ? undefined : onClose}
        />
      ) : null}
      <div
        ref={ref}
        style={isMobile ? undefined : { top: position.top, left: position.left }}
        className={popoverContainerClass(isMobile)}
      >
        <PopoverShell lesson={lesson} dateLabel={dateLabel} saving={saving} onClose={onClose}>
          <div className={`space-y-3 p-4 ${isMobile ? "pb-[max(1rem,env(safe-area-inset-bottom))]" : ""}`}>
            <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Room</p>
            <input
              autoFocus
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSave()}
              placeholder="Room 2"
              className="h-11 w-full rounded-xl border border-foreground/10 bg-background px-3 text-sm outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
            />
            <PopoverActions saving={saving} onClear={onClear} onSave={onSave} />
          </div>
        </PopoverShell>
      </div>
    </>
  );
});
