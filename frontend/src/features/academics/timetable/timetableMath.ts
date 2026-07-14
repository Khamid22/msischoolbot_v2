export type TimetableHourRange = { startHour: number; endHour: number };

function timeMinutes(value: string) {
  const [hour, minute] = value.split(":").map(Number);
  return Number.isFinite(hour) && Number.isFinite(minute) ? hour * 60 + minute : 0;
}

export function calculateAdaptiveHourRange(
  items: Array<{ startTime: string; endTime: string }>,
): TimetableHourRange {
  const timed = items.filter((item) => item.startTime && item.endTime);
  if (!timed.length) return { startHour: 8, endHour: 14 };
  let startHour = Math.floor(
    Math.min(...timed.map((item) => timeMinutes(item.startTime))) / 60,
  ) - 1;
  let endHour = Math.ceil(
    Math.max(...timed.map((item) => timeMinutes(item.endTime))) / 60,
  ) + 1;
  startHour = Math.max(6, startHour);
  endHour = Math.min(22, endHour);
  if (endHour - startHour < 6) {
    const missing = 6 - (endHour - startHour);
    startHour = Math.max(6, startHour - Math.ceil(missing / 2));
    endHour = Math.min(22, startHour + 6);
    startHour = Math.max(6, endHour - 6);
  }
  return { startHour, endHour };
}
