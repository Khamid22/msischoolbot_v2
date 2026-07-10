import test from "node:test";
import assert from "node:assert/strict";
import {
  isFutureInstant,
  officeHoursStartFrom,
  schoolDateKey,
  schoolDateKeyFromValue,
  schoolDayStartIso,
  schoolLocalDateTimeToIso,
  schoolWeekBounds,
} from "./schoolTime.ts";

test("school dates use Asia/Tashkent at UTC day boundaries", () => {
  assert.equal(schoolDateKey(new Date("2026-07-10T18:59:59Z")), "2026-07-10");
  assert.equal(schoolDateKey(new Date("2026-07-10T19:00:00Z")), "2026-07-11");
  assert.equal(schoolDateKeyFromValue("2026-07-10T20:00:00Z"), "2026-07-11");
  assert.equal(schoolDateKeyFromValue("2026-07-10T20:00:00"), "2026-07-10");
  assert.equal(schoolDateKeyFromValue("10/07/2026"), "2026-07-10");
});

test("schoolWeekBounds returns the actual Monday through Sunday school week", () => {
  assert.deepEqual(schoolWeekBounds(new Date("2026-07-10T12:00:00Z")), {
    start: "2026-07-06",
    end: "2026-07-12",
  });
});

test("office-hours lower bounds use school midnight and never include the past", () => {
  const now = new Date("2026-07-10T06:00:00Z"); // 11:00 in Tashkent
  assert.equal(schoolDayStartIso("2026-07-11"), "2026-07-11T00:00:00+05:00");
  assert.equal(officeHoursStartFrom("2026-07-11", now), "2026-07-11T00:00:00+05:00");
  assert.equal(officeHoursStartFrom("2026-07-10", now), now.toISOString());
  assert.equal(isFutureInstant("2026-07-10T06:00:01Z", now), true);
  assert.equal(isFutureInstant("2026-07-10T05:59:59Z", now), false);
});

test("school-local office-hours inputs become full UTC instants", () => {
  assert.equal(schoolLocalDateTimeToIso("2026-07-10", "09:30"), "2026-07-10T04:30:00.000Z");
  assert.equal(schoolLocalDateTimeToIso("2026-07-10", "24:00"), "");
  assert.equal(schoolLocalDateTimeToIso("not-a-date", "09:30"), "");
});
