export const SCHEDULE_SNAP_MINUTES = 10;
export const DEFAULT_CLASS_MINUTES = 80;

const SCHOOL_CLASS_MINUTES: Readonly<Record<string, number>> = {
  sehriyo: 40,
  school5: 80,
  "5": 80,
};

export type SnappedStartInput = {
  clientY: number;
  rectTop: number;
  dayStartMin: number;
  dayEndMin: number;
  durationMin: number;
  hourPx: number;
  grabOffsetY?: number;
  snapMinutes?: number;
};

export function clampNumber(value: number, min: number, max: number) {
  return Math.max(min, Math.min(value, max));
}

export function snapToMinutes(totalMinutes: number, snapMinutes = SCHEDULE_SNAP_MINUTES) {
  return Math.round(totalMinutes / snapMinutes) * snapMinutes;
}

export function snappedStartMinutes({
  clientY,
  rectTop,
  dayStartMin,
  dayEndMin,
  durationMin,
  hourPx,
  grabOffsetY = 0,
  snapMinutes = SCHEDULE_SNAP_MINUTES,
}: SnappedStartInput) {
  const offsetY = clientY - rectTop - grabOffsetY;
  const rawMinutes = dayStartMin + (offsetY / hourPx) * 60;
  const snapped = snapToMinutes(rawMinutes, snapMinutes);
  return clampNumber(snapped, dayStartMin, dayEndMin - durationMin);
}

export function lessonDurationMinutesForSchoolCode(value: unknown, defaultMinutes = DEFAULT_CLASS_MINUTES) {
  const schoolCode = String(value || "").toLowerCase().replace(/[\s_-]+/g, "");
  return SCHOOL_CLASS_MINUTES[schoolCode] ?? defaultMinutes;
}
