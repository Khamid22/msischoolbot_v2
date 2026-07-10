export const SCHOOL_TIME_ZONE = "Asia/Tashkent";
export const SCHOOL_UTC_OFFSET = "+05:00";

const DATE_KEY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

function pad2(value: number) {
  return String(value).padStart(2, "0");
}

function validDateKey(value: string) {
  const match = value.match(DATE_KEY_PATTERN);
  if (!match) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

/** Return the school-local calendar date for an instant, independent of browser timezone. */
export function schoolDateKey(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: SCHOOL_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

/**
 * Normalize dates from workbook-style strings and API timestamps.
 * A timestamp carrying Z/offset is converted to the school calendar day;
 * a date-only or timezone-less database date keeps its declared day.
 */
export function schoolDateKeyFromValue(value: unknown) {
  const raw = String(value ?? "").trim();
  if (!raw) return "";

  const ddmmyyyy = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (ddmmyyyy) {
    const key = `${ddmmyyyy[3]}-${pad2(Number(ddmmyyyy[2]))}-${pad2(Number(ddmmyyyy[1]))}`;
    return validDateKey(key) ? key : "";
  }

  const dateOnly = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (dateOnly) {
    const key = `${dateOnly[1]}-${pad2(Number(dateOnly[2]))}-${pad2(Number(dateOnly[3]))}`;
    return validDateKey(key) ? key : "";
  }

  const dateTimePrefix = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})[T\s]/);
  const hasExplicitZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
  if (dateTimePrefix && !hasExplicitZone) {
    const key = `${dateTimePrefix[1]}-${pad2(Number(dateTimePrefix[2]))}-${pad2(Number(dateTimePrefix[3]))}`;
    return validDateKey(key) ? key : "";
  }

  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? "" : schoolDateKey(parsed);
}

export function addDaysToDateKey(dateKey: string, days: number) {
  if (!validDateKey(dateKey)) return "";
  const date = new Date(`${dateKey}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** Monday-through-Sunday school-local week containing the supplied instant. */
export function schoolWeekBounds(reference = new Date()) {
  const today = schoolDateKey(reference);
  const weekday = new Date(`${today}T00:00:00Z`).getUTCDay();
  const daysSinceMonday = (weekday + 6) % 7;
  const start = addDaysToDateKey(today, -daysSinceMonday);
  return { start, end: addDaysToDateKey(start, 6) };
}

/** Midnight at the school in a Postgres-safe timestamptz representation. */
export function schoolDayStartIso(dateKey: string) {
  return validDateKey(dateKey) ? `${dateKey}T00:00:00${SCHOOL_UTC_OFFSET}` : "";
}

/** Convert a school-local date and HH:mm value into a full UTC instant. */
export function schoolLocalDateTimeToIso(dateKey: string, time: string) {
  if (!validDateKey(dateKey) || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time)) return "";
  const parsed = new Date(`${dateKey}T${time}:00${SCHOOL_UTC_OFFSET}`);
  return Number.isNaN(parsed.getTime()) ? "" : parsed.toISOString();
}

/**
 * Office-hours results never start in the past. A future selected day begins
 * at school midnight; today or a past day begins at the current instant.
 */
export function officeHoursStartFrom(dateKey: string, now = new Date()) {
  const schoolMidnight = schoolDayStartIso(dateKey);
  if (schoolMidnight && Date.parse(schoolMidnight) > now.getTime()) return schoolMidnight;
  return now.toISOString();
}

export function isFutureInstant(value: unknown, now = new Date()) {
  const timestamp = Date.parse(String(value ?? ""));
  return Number.isFinite(timestamp) && timestamp > now.getTime();
}
