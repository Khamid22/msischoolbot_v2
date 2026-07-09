import { forwardRef, useEffect, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { Clock, MapPin, X } from "lucide-react";
import { motion } from "@/shared/lib/motion";
import { Lesson } from "./shared";

/**
 * Presentational building blocks for the group Timetable tab. These components
 * are intentionally decoupled from data fetching / persistence — the parent
 * (GroupGradebook) owns state, API calls, and date-grouping logic, and passes
 * already-derived values in as props.
 */

export type TimetableDateGroup = {
  key: string;
  iso: string;
  display: string;
  weekday: string;
  lessons: Lesson[];
};

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

function monthDayFromIso(iso: string) {
  if (!iso) return { month: "—", day: "?" };
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return { month: "—", day: "?" };
  return {
    month: date.toLocaleDateString("en-US", { month: "short" }).toUpperCase(),
    day: date.getDate(),
  };
}

export function DateBadge({ iso, cancelled = false }: { iso: string; cancelled?: boolean }) {
  const { month, day } = monthDayFromIso(iso);
  return (
    <div
      className={`flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-2xl ${
        cancelled ? "bg-red-100 text-red-700" : "bg-primary/10 text-primary"
      }`}
    >
      <span className="text-[9px] font-bold uppercase leading-none">{month}</span>
      <span className="mt-0.5 text-base font-black leading-none">{day}</span>
    </div>
  );
}

// A single tint (navy, matching DateBadge) for "set" chips instead of mixing
// blue/green/etc — keeps the tab from drifting away from the app's accent.
function chipClass(isSet: boolean, canEdit: boolean) {
  const base = "inline-flex h-10 items-center gap-1.5 rounded-full border px-3 text-[11px] font-bold transition-[transform,opacity]";
  const interactive = canEdit ? "hover:-translate-y-px hover:opacity-85" : "cursor-default opacity-70";
  const tone = isSet ? "border-primary/25 bg-primary/8 text-primary" : "border-foreground/12 bg-background text-muted-foreground";
  return `${base} ${interactive} ${tone}`;
}

export function TimetableLessonRow({
  lesson,
  iso,
  cancelled,
  canEdit,
  onOpenTime,
  onOpenRoom,
}: {
  lesson: Lesson;
  iso: string;
  cancelled: boolean;
  canEdit: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>) => void;
  onOpenRoom: (e: ReactMouseEvent<HTMLButtonElement>) => void;
}) {
  const hasTime = Boolean(lesson.startTime && lesson.endTime);
  const hasRoom = Boolean(lesson.room);
  const timeLabel = hasTime ? `${lesson.startTime}–${lesson.endTime}` : "Set time";
  const roomLabel = hasRoom ? lesson.room : "Set room";

  return (
    <div
      className={`flex flex-col gap-3 rounded-2xl border px-3.5 py-3 shadow-sm sm:flex-row sm:items-center ${
        cancelled ? "border-red-200 bg-red-50/50" : "border-foreground/6 bg-muted/40"
      }`}
    >
      <div className="flex min-w-0 items-center gap-3">
        <DateBadge iso={iso} cancelled={cancelled} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">{lesson.lessonNumber}</p>
          <p className="mt-0.5 line-clamp-2 text-xs leading-snug text-muted-foreground">{lesson.topic || "—"}</p>
        </div>
      </div>
      {cancelled ? (
        <span className="inline-flex w-fit shrink-0 items-center rounded-full bg-red-100 px-2.5 py-1 text-[9px] font-bold uppercase tracking-wide text-red-700 shadow-sm sm:ml-auto">
          Cancelled
        </span>
      ) : canEdit ? (
        <div className="flex flex-wrap shrink-0 items-center gap-1.5 sm:ml-auto sm:flex-nowrap">
          <button
            type="button"
            onClick={onOpenTime}
            title={`${lesson.lessonNumber} · edit class time`}
            className={`max-w-[9.5rem] ${chipClass(hasTime, true)}`}
          >
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span className="min-w-0 truncate">{timeLabel}</span>
          </button>
          <button
            type="button"
            onClick={onOpenRoom}
            title={`${lesson.lessonNumber} · edit room`}
            className={`max-w-[9.5rem] ${chipClass(hasRoom, true)}`}
          >
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            <span className="min-w-0 truncate">{roomLabel}</span>
          </button>
        </div>
      ) : (
        // View-only roles (students/parents, or teachers without edit rights)
        // get plain labels — never a button that looks editable but isn't.
        <div className="flex flex-wrap shrink-0 items-center gap-3 text-xs font-semibold text-muted-foreground sm:ml-auto">
          <span className="inline-flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            {timeLabel}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            {roomLabel}
          </span>
        </div>
      )}
    </div>
  );
}

export function TimetableCard({
  groups,
  isLessonCancelled,
  canEdit = true,
  onOpenTime,
  onOpenRoom,
}: {
  groups: TimetableDateGroup[];
  isLessonCancelled: (lesson: Lesson) => boolean;
  canEdit?: boolean;
  onOpenTime: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
  onOpenRoom: (e: ReactMouseEvent<HTMLButtonElement>, lesson: Lesson) => void;
}) {
  return (
    <div
      className={`flex min-h-0 flex-col overflow-hidden rounded-2xl border border-foreground/8 bg-surface shadow-card ${motion.panel}`}
      style={{
        height: "calc(var(--tg-app-height) - 11rem)",
        maxHeight: "78dvh",
        minHeight: "26rem",
      }}
    >
      <div className="shrink-0 px-4 py-4">
        <p className="text-sm font-bold">Timetable</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {canEdit
            ? "Conducted lesson dates with class time and room · tap a chip to edit"
            : "Conducted lesson dates with class time and room"}
        </p>
      </div>
      <div className="h-px shrink-0 bg-foreground/8" />
      {groups.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
          No timetable lessons yet.
        </div>
      ) : (
        <div className="miniapp-table-scroll min-h-0 flex-1 space-y-5 px-4 py-4 [scrollbar-gutter:stable]">
          {groups.map((group) => (
            <div key={group.key}>
              <p className="sticky top-0 z-10 -mx-4 mb-2.5 bg-surface/95 px-4 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground backdrop-blur">
                {group.weekday ? `${group.weekday} · ${group.display}` : group.display}
              </p>
              <div className="space-y-2.5">
                {group.lessons.map((lesson) => (
                  <TimetableLessonRow
                    key={lesson.id}
                    lesson={lesson}
                    iso={group.iso}
                    cancelled={isLessonCancelled(lesson)}
                    canEdit={canEdit}
                    onOpenTime={(e) => onOpenTime(e, lesson)}
                    onOpenRoom={(e) => onOpenRoom(e, lesson)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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
