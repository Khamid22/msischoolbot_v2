/**
 * Parse a metric without confusing an explicit zero with missing data.
 * Empty strings are treated as missing because APIs commonly serialize an
 * unrecorded score that way.
 */
export function finiteMetricOrNull(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string" && !value.trim()) return null;

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Average all recorded finite values, including valid zero scores. */
export function averageRecordedMetrics(values: unknown[]): number | null {
  const recorded = values
    .map(finiteMetricOrNull)
    .filter((value): value is number => value !== null);

  if (!recorded.length) return null;
  return recorded.reduce((sum, value) => sum + value, 0) / recorded.length;
}
