import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  academicDirectorActiveNavFromPath,
  academicDirectorMobileNavConfig,
  academicDirectorNavConfig,
  headOfDepartmentActiveNavFromPath,
  headOfDepartmentMobileNavConfig,
  headOfDepartmentNavConfig,
} from "./academicNav.ts";

describe("Academic Director navigation", () => {
  it("desktop nav is Overview, Teacher Academy, Head of Departments, Timetable, Announcements, Profile", () => {
    assert.deepEqual(
      academicDirectorNavConfig.map((item) => item.label),
      ["Overview", "Teacher Academy", "Head of Departments", "Timetable", "Announcements", "Profile"],
    );
  });

  it("mobile nav is Overview, Academy, Schedule, News, Profile", () => {
    assert.deepEqual(
      academicDirectorMobileNavConfig.map((item) => item.label),
      ["Overview", "Academy", "Schedule", "News", "Profile"],
    );
  });

  it("every item links to a real path", () => {
    for (const item of academicDirectorNavConfig) {
      assert.match(item.href, /^\/academic-director/, `${item.label} href must be an academic-director path`);
    }
  });

  it("resolves the active item for each page URL", () => {
    assert.equal(academicDirectorActiveNavFromPath("/academic-director"), "overview");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/teacher-academy"), "academy");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/head-of-departments"), "departments");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/timetable"), "timetable");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/announcements"), "announcements");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/profile"), "profile");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director", "#academic-director-profile"), "profile");
  });
});

describe("Head of Department navigation", () => {
  it("desktop nav is Overview, Teacher Academy, Timetable, Announcements, Profile", () => {
    assert.deepEqual(
      headOfDepartmentNavConfig.map((item) => item.label),
      ["Overview", "Teacher Academy", "Timetable", "Announcements", "Profile"],
    );
  });

  it("mobile nav is Overview, Academy, Schedule, News, Profile", () => {
    assert.deepEqual(
      headOfDepartmentMobileNavConfig.map((item) => item.label),
      ["Overview", "Academy", "Schedule", "News", "Profile"],
    );
  });

  it("every item links to a real path", () => {
    for (const item of headOfDepartmentNavConfig) {
      assert.match(item.href, /^\/head-of-department/, `${item.label} href must be a head-of-department path`);
    }
  });

  it("resolves the active item for each page URL", () => {
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-department"), "overview");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-department/teacher-academy"), "academy");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-department/timetable"), "timetable");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-department/announcements"), "announcements");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-department/profile"), "profile");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-department", "#head-of-department-profile"), "profile");
  });
});

describe("mobile labels", () => {
  it("stays within 10 characters so the bottom nav never truncates", () => {
    for (const item of [...academicDirectorMobileNavConfig, ...headOfDepartmentMobileNavConfig]) {
      assert.ok(item.label.length <= 10, `mobile label "${item.label}" is too long for the bottom nav`);
    }
  });
});
