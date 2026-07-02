import test from "node:test";
import assert from "node:assert/strict";
import {
  lessonDurationMinutesForSchoolCode,
  randomLessonStartMinutesForSeed,
  snappedStartMinutes,
} from "./scheduleMath.ts";

test("snappedStartMinutes keeps the grabbed card top aligned to the grid", () => {
  const withGrabOffset = snappedStartMinutes({
    clientY: 200,
    rectTop: 100,
    grabOffsetY: 40,
    dayStartMin: 8 * 60,
    dayEndMin: 20 * 60,
    durationMin: 80,
    hourPx: 120,
  });
  const pointerOnly = snappedStartMinutes({
    clientY: 200,
    rectTop: 100,
    grabOffsetY: 0,
    dayStartMin: 8 * 60,
    dayEndMin: 20 * 60,
    durationMin: 80,
    hourPx: 120,
  });

  assert.equal(withGrabOffset, 510);
  assert.equal(pointerOnly, 530);
});

test("snappedStartMinutes clamps above and below the visible school day", () => {
  const base = {
    rectTop: 100,
    dayStartMin: 8 * 60,
    dayEndMin: 20 * 60,
    durationMin: 80,
    hourPx: 120,
  };

  assert.equal(snappedStartMinutes({ ...base, clientY: 60 }), 480);
  assert.equal(snappedStartMinutes({ ...base, clientY: 2000 }), 1120);
});

test("lessonDurationMinutesForSchoolCode follows school-specific class lengths", () => {
  assert.equal(lessonDurationMinutesForSchoolCode("Sehriyo"), 40);
  assert.equal(lessonDurationMinutesForSchoolCode("school 5"), 80);
  assert.equal(lessonDurationMinutesForSchoolCode("School_5"), 80);
  assert.equal(lessonDurationMinutesForSchoolCode("unknown"), 80);
});

test("randomLessonStartMinutesForSeed is deterministic, snapped, and inside the day", () => {
  const start = randomLessonStartMinutesForSeed(77, 3, 8 * 60, 20 * 60, 40);
  assert.equal(start, randomLessonStartMinutesForSeed(77, 3, 8 * 60, 20 * 60, 40));
  assert.equal(start % 10, 0);
  assert.ok(start >= 8 * 60);
  assert.ok(start <= 20 * 60 - 40);
});
