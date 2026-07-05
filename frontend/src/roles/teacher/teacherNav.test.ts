import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { bottomNavActiveKey, teacherMobileTabKeys, type TeacherTabKey } from "./teacherNav.ts";

describe("teacherMobileTabKeys", () => {
  it("is exactly Home, Lessons (reports), Updates, Profile in order", () => {
    assert.deepEqual([...teacherMobileTabKeys], ["home", "reports", "updates", "profile"]);
  });
});

describe("bottomNavActiveKey", () => {
  it("returns the tab itself for tabs present in the bottom nav", () => {
    for (const key of teacherMobileTabKeys) {
      assert.equal(bottomNavActiveKey(key), key);
    }
  });

  it("maps career to profile so the Profile item stays highlighted", () => {
    assert.equal(bottomNavActiveKey("career"), "profile");
  });

  it("highlights nothing for timetable, which has no bottom-nav item", () => {
    assert.equal(bottomNavActiveKey("timetable"), null);
  });

  it("never highlights two items for one active tab", () => {
    const allTabs: TeacherTabKey[] = ["home", "reports", "timetable", "career", "updates", "profile"];
    for (const tab of allTabs) {
      const active = teacherMobileTabKeys.filter((key) => bottomNavActiveKey(tab) === key);
      assert.ok(active.length <= 1, `expected at most one active item for ${tab}`);
    }
  });
});
