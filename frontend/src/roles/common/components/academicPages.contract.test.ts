import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

/**
 * Contract tests for the Academic Director / Head of Department pages
 * (Phase 2). Like sharedUiContract.test.ts, structural requirements are
 * asserted against page source because the repo has no DOM test runner.
 */
function pageSource(relativePath: string): string {
  return readFileSync(new URL(`../../${relativePath}`, import.meta.url), "utf8");
}

const rolePages = {
  "RoleHome (AD/HOD overview + profile)": pageSource("common/pages/RoleHome.tsx"),
  "AcademicDepartmentWorkspace (timetable/announcements)": pageSource("common/pages/AcademicDepartmentWorkspace.tsx"),
  "AD HeadOfDepartments": pageSource("academic_director/pages/HeadOfDepartments.tsx"),
  "AD TeacherAcademy": pageSource("academic_director/pages/TeacherAcademy.tsx"),
  "HOD TeacherAcademy": pageSource("head_of_department/pages/TeacherAcademy.tsx"),
};

describe("AD/HOD pages use the shared role shell — no admin chrome", () => {
  for (const [name, src] of Object.entries(rolePages)) {
    it(`${name} renders through a role PageShell`, () => {
      assert.match(src, /(AcademicDirectorPageShell|HeadOfDepartmentPageShell)/);
    });

    it(`${name} has no duplicate Admin sidebar or admin layout`, () => {
      assert.doesNotMatch(src, /AdminSidebar/);
      assert.doesNotMatch(src, /AdminEmbedLayout/);
      assert.doesNotMatch(src, /<aside/);
    });

    it(`${name} builds no bespoke page header`, () => {
      assert.doesNotMatch(src, /<header/);
    });
  }
});

describe("Head of Departments page", () => {
  const src = rolePages["AD HeadOfDepartments"];

  it("renders mobile cards with the required fields and a View action", () => {
    assert.match(src, /<MobileCardList/);
    for (const field of ["accountName", "login", "roleLabel", "subjectLabel", "StatusBadge", "Updated", "View"]) {
      assert.match(src, new RegExp(field), `mobile card is missing "${field}"`);
    }
  });

  it("uses the responsive KPI grid", () => {
    assert.match(src, /<MetricGrid>/);
  });

  it("gates the New HOD CTA to the Academic Director role", () => {
    assert.match(src, /isDirector/);
    assert.match(src, /academic_director/);
    assert.match(src, /New HOD/);
  });

  it("has a Subject Coverage section and an empty state", () => {
    assert.match(src, /Subject Coverage/);
    assert.match(src, /<EmptyState/);
  });

  it("keeps the desktop action column visible instead of a clipped Read-only pill", () => {
    assert.doesNotMatch(src, /table-fixed/);
    assert.match(src, /whitespace-nowrap px-4 py-3 text-right/);
  });

  it("opens details in the shared bottom sheet layer", () => {
    assert.match(src, /BottomSheet/);
  });
});

describe("KPI grids", () => {
  it("overview and workspace pages use MetricGrid (2 columns on mobile)", () => {
    assert.match(rolePages["RoleHome (AD/HOD overview + profile)"], /<MetricGrid>/);
    assert.match(rolePages["AcademicDepartmentWorkspace (timetable/announcements)"], /<MetricGrid>/);
  });
});
