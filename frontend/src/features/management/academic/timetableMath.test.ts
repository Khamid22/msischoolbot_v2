import test from "node:test";
import assert from "node:assert/strict";
import { calculateAdaptiveHourRange } from "./timetableMath.ts";

test("adaptive timetable includes an hour of context and at least six hours", () => {
  assert.deepEqual(
    calculateAdaptiveHourRange([{ startTime: "14:00", endTime: "15:20" }]),
    { startHour: 12, endHour: 18 },
  );
});

test("adaptive timetable clamps early and late lessons to school hours", () => {
  assert.deepEqual(
    calculateAdaptiveHourRange([
      { startTime: "06:30", endTime: "07:30" },
      { startTime: "20:30", endTime: "21:30" },
    ]),
    { startHour: 6, endHour: 22 },
  );
});

test("adaptive timetable has a useful empty fallback", () => {
  assert.deepEqual(calculateAdaptiveHourRange([]), { startHour: 8, endHour: 14 });
});
