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
  it("desktop nav includes academic workspaces after Head of Departments", () => {
    assert.deepEqual(
      academicDirectorNavConfig.map((item) => item.label),
      [
        "Overview",
        "Teacher Academy",
        "Head of Departments",
        "Groups",
        "Subjects",
        "Academic Timetable",
        "Announcements",
        "Recruitment",
        "Profile",
      ],
    );
  });

  it("mobile nav includes the assigned-candidate recruitment entry", () => {
    assert.deepEqual(
      academicDirectorMobileNavConfig.map((item) => item.label),
      ["Overview", "Academy", "Groups", "Schedule", "Hiring", "Profile"],
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
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/groups"), "groups");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/subjects"), "subjects");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/timetable"), "timetable");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/announcements"), "announcements");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/recruitment"), "recruitment");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director/profile"), "profile");
    assert.equal(academicDirectorActiveNavFromPath("/academic-director", "#academic-director-profile"), "overview");
  });
});

describe("Head of Departments navigation", () => {
  it("desktop nav includes recruitment", () => {
    assert.deepEqual(
      headOfDepartmentNavConfig.map((item) => item.label),
      ["Overview", "Teacher Academy", "Timetable", "Announcements", "Recruitment", "Profile"],
    );
  });

  it("mobile nav includes assigned-candidate recruitment", () => {
    assert.deepEqual(
      headOfDepartmentMobileNavConfig.map((item) => item.label),
      ["Overview", "Academy", "Schedule", "News", "Hiring", "Profile"],
    );
  });

  it("every item links to a real path", () => {
    for (const item of headOfDepartmentNavConfig) {
      assert.match(item.href, /^\/head-of-departments/, `${item.label} href must be a head-of-departments path`);
    }
  });

  it("resolves the active item for each page URL", () => {
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-departments"), "overview");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-departments/teacher-academy"), "academy");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-departments/timetable"), "timetable");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-departments/announcements"), "announcements");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-departments/recruitment"), "recruitment");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-departments/profile"), "profile");
    assert.equal(headOfDepartmentActiveNavFromPath("/head-of-departments", "#head-of-department-profile"), "overview");
  });
});

describe("mobile labels", () => {
  it("stays within 10 characters so the bottom nav never truncates", () => {
    for (const item of [...academicDirectorMobileNavConfig, ...headOfDepartmentMobileNavConfig]) {
      assert.ok(item.label.length <= 10, `mobile label "${item.label}" is too long for the bottom nav`);
    }
  });
});
