import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  activeTeacherMobileTabKeys,
  bottomNavActiveKey,
  mobileTabKeysFor,
  teacherMobileTabKeys,
  type TeacherTabKey,
} from "./teacherNav.ts";

describe("teacherMobileTabKeys", () => {
  it("academy nav is exactly Home, Lessons (reports), Updates, Profile in order", () => {
    assert.deepEqual([...teacherMobileTabKeys], ["home", "reports", "updates", "profile"]);
  });

  it("active teacher nav is exactly Home, Reports, Timetable, Profile in order", () => {
    assert.deepEqual([...activeTeacherMobileTabKeys], ["home", "reports", "timetable", "profile"]);
  });

  it("mobileTabKeysFor returns the matching mode", () => {
    assert.equal(mobileTabKeysFor("academy"), teacherMobileTabKeys);
    assert.equal(mobileTabKeysFor("active"), activeTeacherMobileTabKeys);
  });
});

describe("bottomNavActiveKey", () => {
  it("returns the tab itself for tabs present in the bottom nav", () => {
    for (const key of teacherMobileTabKeys) {
      assert.equal(bottomNavActiveKey(key), key);
    }
    for (const key of activeTeacherMobileTabKeys) {
      assert.equal(bottomNavActiveKey(key, "active"), key);
    }
  });

  it("maps career to profile so the Profile item stays highlighted", () => {
    assert.equal(bottomNavActiveKey("career"), "profile");
    assert.equal(bottomNavActiveKey("career", "active"), "profile");
  });

  it("highlights nothing for timetable in academy mode, which has no bottom-nav item", () => {
    assert.equal(bottomNavActiveKey("timetable"), null);
  });

  it("highlights timetable for active teachers, whose bottom nav includes it", () => {
    assert.equal(bottomNavActiveKey("timetable", "active"), "timetable");
  });

  it("highlights nothing for updates in active mode, which has no bottom-nav item", () => {
    assert.equal(bottomNavActiveKey("updates", "active"), null);
  });

  it("never highlights two items for one active tab", () => {
    const allTabs: TeacherTabKey[] = ["home", "reports", "timetable", "career", "updates", "profile"];
    for (const mode of ["academy", "active"] as const) {
      for (const tab of allTabs) {
        const active = mobileTabKeysFor(mode).filter((key) => bottomNavActiveKey(tab, mode) === key);
        assert.ok(active.length <= 1, `expected at most one active item for ${tab} in ${mode}`);
      }
    }
  });
});
