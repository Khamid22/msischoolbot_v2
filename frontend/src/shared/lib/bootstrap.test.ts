import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { inferPageFromPath, normalizePageName } from "./bootstrap.ts";

test("Teacher Academy teacher pages remain in the teacher workspace", () => {
  assert.equal(normalizePageName("teacher-home"), "teacher-home");
  assert.equal(inferPageFromPath("/teacher"), "teacher-home");
  assert.equal(inferPageFromPath("/teacher/"), "teacher-home");
});

test("every lazy page registered by App is accepted by the bootstrap normalizer", () => {
  const appSource = readFileSync(new URL("../../app/App.tsx", import.meta.url), "utf8");
  const pageMapSource = appSource.match(/const pageMap = \{([\s\S]*?)\} as const;/)?.[1] || "";
  const registeredPages = Array.from(
    pageMapSource.matchAll(/^\s{2}(?:"([^"]+)"|([a-z][\w-]*)):\s*lazy\(/gm),
    (match) => match[1] || match[2],
  );

  assert.ok(registeredPages.includes("teacher-home"));
  assert.ok(registeredPages.length > 0);
  for (const page of registeredPages) {
    assert.equal(normalizePageName(page), page, `${page} is missing from the bootstrap registry`);
  }
});

test("Teacher Home owns the missing-Academy-profile empty state", () => {
  const teacherHomeSource = readFileSync(
    new URL("../../workspaces/teacher/pages/Home.tsx", import.meta.url),
    "utf8",
  );

  assert.match(teacherHomeSource, /Your Academy profile isn't available yet\./);
  assert.doesNotMatch(teacherHomeSource, /Student Not Found/);
});
