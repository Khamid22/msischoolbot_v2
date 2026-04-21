const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function parseDateParts(rawValue: string) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return null;
  }

  const isoMatch = value.match(/^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$/);
  if (isoMatch) {
    const year = Number(isoMatch[1]);
    const month = Number(isoMatch[2]);
    const day = Number(isoMatch[3]);
    return { day, month, year };
  }

  const dayMonthMatch = value.match(/^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?$/);
  if (!dayMonthMatch) {
    return null;
  }

  const day = Number(dayMonthMatch[1]);
  const month = Number(dayMonthMatch[2]);
  const yearToken = String(dayMonthMatch[3] || "").trim();
  let year = new Date().getFullYear();
  if (yearToken) {
    const parsedYear = Number(yearToken);
    year = yearToken.length <= 2 ? 2000 + parsedYear : parsedYear;
  }

  return { day, month, year };
}

function isValidDate(day: number, month: number, year: number) {
  if (!Number.isFinite(day) || !Number.isFinite(month) || !Number.isFinite(year)) {
    return false;
  }
  if (month < 1 || month > 12 || day < 1 || day > 31 || year < 1900 || year > 2200) {
    return false;
  }
  const candidate = new Date(year, month - 1, day);
  return (
    candidate.getFullYear() === year
    && candidate.getMonth() === month - 1
    && candidate.getDate() === day
  );
}

export function formatLessonDateDisplay(rawValue: string) {
  const original = String(rawValue || "").trim();
  if (!original) {
    return original;
  }

  const parsed = parseDateParts(original);
  if (!parsed || !isValidDate(parsed.day, parsed.month, parsed.year)) {
    return original;
  }

  const monthName = MONTH_NAMES[parsed.month - 1];
  return `${monthName} ${parsed.day}, ${parsed.year}`;
}
