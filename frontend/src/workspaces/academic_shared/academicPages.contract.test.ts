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
  "RoleHome (AD/HOD overview + profile)": pageSource("workspaces/shared/RoleHome.tsx"),
  "AD AcademicWorkspace (groups/subjects/timetable)": pageSource("workspaces/academic_director/pages/AcademicWorkspace.tsx"),
  "AcademicDepartmentWorkspace (timetable/announcements)": pageSource("workspaces/academic_shared/AcademicDepartmentWorkspace.tsx"),
  "AD HeadOfDepartments": pageSource("workspaces/academic_director/pages/HeadOfDepartments.tsx"),
  "AD TeacherAcademy": pageSource("workspaces/academic_director/pages/TeacherAcademy.tsx"),
  "HOD TeacherAcademy": pageSource("workspaces/head_of_departments/pages/TeacherAcademy.tsx"),
};

describe("AD/HOD pages use the shared role shell — no admin chrome", () => {
  for (const [name, src] of Object.entries(rolePages)) {
    it(`${name} renders through a role PageShell`, () => {
      assert.match(src, /(AcademicDirectorPageShell|HeadOfDepartmentPageShell)/);
    });

    it(`${name} has no duplicate Admin sidebar or admin layout`, () => {
      assert.doesNotMatch(src, /InternalOperationsSidebar/);
      assert.doesNotMatch(src, /AdminEmbedLayout/);
      assert.doesNotMatch(src, /<aside/);
    });

    it(`${name} builds no bespoke page header`, () => {
      assert.doesNotMatch(src, /<header/);
    });
  }
});

describe("Recruitment stays inside the academic workspace navigation", () => {
  const shell = pageSource("workspaces/academic_shared/AcademicDirectorShell.tsx");
  const workspace = pageSource("features/recruitment/RecruitmentWorkspace.tsx");

  it("nests the role-scoped Recruitment pages under the academic sidebar", () => {
    for (const label of ["Candidates", "Schedule"]) {
      assert.match(shell, new RegExp(label));
    }
    assert.doesNotMatch(shell, /label: "Decisions"/);
    assert.doesNotMatch(shell, /label: "Assigned Candidates"/);
    assert.doesNotMatch(shell, /label: "Demo Schedule"/);
    assert.match(shell, /children: academicDirectorRecruitmentChildren/);
    assert.match(shell, /children: headOfDepartmentRecruitmentChildren/);
  });

  it("reuses the Academic Director and HOD shells for Recruitment content", () => {
    assert.match(workspace, /<AcademicDirectorPageShell/);
    assert.match(workspace, /<HeadOfDepartmentPageShell/);
    assert.match(workspace, /active="recruitment"/);
  });
});

describe("Head of Departments page", () => {
  const src = rolePages["AD HeadOfDepartments"];

  it("renders one responsive account card grid with the required fields and a View action", () => {
    assert.match(src, /grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3/);
    assert.match(src, /<DepartmentCard/);
    assert.doesNotMatch(src, /MobileCardList|ResponsiveTable|<table/);
    for (const field of ["accountName", "login", "roleLabel", "subjectLabel", "StatusBadge", "Updated", "View details"]) {
      assert.match(src, new RegExp(field), `account card is missing "${field}"`);
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

  it("uses the same responsive breakpoints for account and subject coverage grids", () => {
    const responsiveGrids = src.match(/grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3/g) || [];
    assert.equal(responsiveGrids.length, 2);
    assert.match(src, /Read-only records/);
  });

  it("opens details in the shared bottom sheet layer", () => {
    assert.match(src, /BottomSheet/);
  });

  it("keeps passwords protected and supports a reveal-once reset flow", () => {
    for (const token of [
      "Password access",
      "current password is protected",
      "Reset password",
      "Generate temporary password",
      "shown once",
      "Copy temporary password",
      "academicDirectorHeadOfDepartmentPasswordReset",
    ]) {
      assert.match(src, new RegExp(token, "i"));
    }
    assert.doesNotMatch(src, /password_hash/);
  });
});

describe("KPI grids", () => {
  it("overview and workspace pages use shared metric components", () => {
    assert.match(rolePages["RoleHome (AD/HOD overview + profile)"], /<MetricGrid>/);
    assert.match(rolePages["AcademicDepartmentWorkspace (timetable/announcements)"], /<MetricCard/);
  });
});

describe("Academic Director academic workspace", () => {
  const src = rolePages["AD AcademicWorkspace (groups/subjects/timetable)"];

  it("uses the shared academic panel with Academic Director API routes", () => {
    for (const token of [
      "AcademicPanel",
      "academicDirectorAcademicRoutes",
      "academicManagementGroupCreateApi",
      "academicManagementSchoolCreateApi",
      "academicManagementScheduleCreate",
      "academicManagementGradebookApi",
      "academicManagementGradebookTrendsApi",
    ]) {
      assert.match(src, new RegExp(token));
    }
    assert.doesNotMatch(src, /academyLessonEvents/);
  });
});

describe("Timetable and Announcements final workspace", () => {
  const src = rolePages["AcademicDepartmentWorkspace (timetable/announcements)"];

  it("timetable shows academy lessons only, with Today/Week view, filters, cards, and a table", () => {
    for (const token of [
      "TimetableRange",
      "today",
      "week",
      "Subject filter",
      "Teacher filter",
      "Schedule Academy Lesson",
      "Open Teacher Academy",
      "TimetableEventCard",
      "sortTimetableItems",
      "<ResponsiveTable",
      "academyLessonEvents",
    ]) {
      assert.match(src, new RegExp(token));
    }
    // Gradebook sessions and recurring schedule rules no longer feed this view.
    assert.doesNotMatch(src, /academicManagementSessions/);
    assert.doesNotMatch(src, /academicManagementSchedules/);
  });

  it("announcements render cards with KPI, audience, status, and priority", () => {
    for (const token of [
      "AnnouncementsContent",
      "Priority:",
      "Audience:",
      "Status:",
      "Pinned",
      "No announcements yet",
    ]) {
      assert.match(src, new RegExp(token));
    }
  });

  it("does not reintroduce truncated announcement labels", () => {
    assert.doesNotMatch(src, /Announc\.\.\./);
  });
});
