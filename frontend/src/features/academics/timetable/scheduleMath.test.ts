import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  lessonDurationMinutesForSchoolCode,
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
  assert.equal(lessonDurationMinutesForSchoolCode("5"), 80);
  assert.equal(lessonDurationMinutesForSchoolCode("unknown"), 80);
  assert.equal(lessonDurationMinutesForSchoolCode("school 15", 55), 55);
  assert.equal(lessonDurationMinutesForSchoolCode("grade 5", 55), 55);
});

test("untimed lessons stay outside the clock grid until a real time is assigned", () => {
  const panel = readFileSync(new URL("./SchedulePanel.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(panel, /randomLessonStartMinutes/);
  assert.match(panel, />\s*Unscheduled\s*</);
  assert.match(panel, /Time not assigned/);
});
