export const SCHEDULE_SNAP_MINUTES = 10;
export const DEFAULT_CLASS_MINUTES = 80;

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
  if (schoolCode.includes("sehriyo")) return 40;
  if (schoolCode.includes("school5") || schoolCode.includes("5")) return 80;
  return defaultMinutes;
}

export function randomLessonStartMinutesForSeed(
  id: unknown,
  index: number,
  startMin: number,
  endMin: number,
  durationMin: number,
  snapMinutes = SCHEDULE_SNAP_MINUTES,
) {
  const available = Math.max(snapMinutes, endMin - startMin - durationMin);
  const slots = Math.max(1, Math.floor(available / snapMinutes));
  const seed = Math.abs((Number(id) || index + 1) * 37 + index * 19);
  return startMin + (seed % slots) * snapMinutes;
}
