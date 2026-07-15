import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const teacherHome = readFileSync(new URL("./pages/Home.tsx", import.meta.url), "utf8");

test("Teacher Academy uses its own responsive cabinet instead of an Admin preview", () => {
  assert.doesNotMatch(teacherHome, /AcademyTeacherPreview/);
  assert.doesNotMatch(teacherHome, /Default password|password equals login/i);
  assert.match(teacherHome, /Teacher Academy navigation/);
  assert.match(teacherHome, /fixed inset-x-0 bottom-0/);
  assert.match(teacherHome, /sticky top-0 hidden h-dvh w-56/);
  assert.match(teacherHome, /overflow-x-hidden/);
  assert.match(teacherHome, /var\(--app-bottom-inset\)/);
});

test("Teacher Academy restores its operational tabs and assessment details", () => {
  for (const tab of ["overview", "lessons", "timetable", "updates", "profile"]) {
    assert.match(teacherHome, new RegExp(`key: "${tab}"`));
  }
  assert.match(teacherHome, /Lessons & reports/);
  assert.match(teacherHome, /Assessment report/);
  assert.match(teacherHome, /Lesson schedule/);
  assert.match(teacherHome, /Recent activity/);
  assert.match(teacherHome, /Change password/);
});

test("Teacher Academy navigation and account actions keep accessible touch targets", () => {
  assert.match(teacherHome, /min-h-12/);
  assert.match(teacherHome, /min-h-11/);
  assert.match(teacherHome, /aria-current/);
  assert.match(teacherHome, /focus-visible:ring-2/);
  assert.match(teacherHome, /motion-reduce:transition-none/);
});
