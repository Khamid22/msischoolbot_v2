import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test, { describe } from "node:test";

function source(name: string) {
  return readFileSync(new URL(`./${name}`, import.meta.url), "utf8");
}

function projectSource(relativePath: string) {
  return readFileSync(new URL(`../../${relativePath}`, import.meta.url), "utf8");
}

describe("compact recruitment pipeline", () => {
  const pipeline = source("PipelineView.tsx");

  test("uses drag plus an accessible menu instead of a permanent card selector", () => {
    assert.match(pipeline, /<ActionMenu items=\{items\}/);
    assert.match(pipeline, /draggable/);
    assert.match(pipeline, /MoveCandidateDialog/);
    assert.doesNotMatch(pipeline, /Move candidate\s*<select/);
  });

  test("uses a single-stage mobile view and six compact desktop columns", () => {
    assert.match(pipeline, /md:hidden/);
    assert.match(pipeline, /grid min-w-\[1230px\] grid-cols-6/);
    assert.match(pipeline, /min-h-60/);
    assert.match(pipeline, /dragOverStage/);
  });
});

describe("candidate navigation and progressive disclosure", () => {
  const profile = source("CandidateProfile.tsx");
  const list = source("CandidateListView.tsx");
  const workspace = source("RecruitmentWorkspace.tsx");

  test("exposes exactly the five URL-backed profile tabs", () => {
    for (const tab of ["overview", "evaluations", "documents", "hiring", "activity"]) {
      assert.match(profile, new RegExp(`key: "${tab}"`));
    }
    assert.match(profile, /url\.searchParams\.set\("tab", next\)/);
    assert.match(profile, /<Drawer/);
  });

  test("keeps only search and stage visible while advanced filters use a drawer", () => {
    assert.match(list, /title="Candidate filters"/);
    assert.match(list, /activeFilters/);
    assert.match(list, /replaceUrlParams\(\{ page, \.\.\.filters \}/);
  });

  test("opts Recruitment into adaptive collapsible navigation without a Profile nav item", () => {
    assert.match(workspace, /desktopSidebarMode="collapsible"/);
    assert.match(workspace, /desktopSidebarInitialState="adaptive"/);
    assert.doesNotMatch(workspace, /key: "profile", label: "Profile"/);
  });

  test("opens Academic Director Recruitment on a compact decision queue", () => {
    const decisions = source("DecisionQueueView.tsx");
    assert.match(workspace, /key: "decisions", label: "Decisions"/);
    assert.match(workspace, /view === "decisions" \? <DecisionQueueView/);
    assert.match(decisions, /\/decision-queue\?page=/);
    assert.match(decisions, /actionable_approval/);
    assert.match(decisions, /origin=decisions/);
  });
});

test("Admin workspace no longer exposes Recruitment navigation or routes", () => {
  const adminWorkspace = projectSource("internal_operations/pages/InternalOperations.tsx");
  const routes = projectSource("shared/lib/routes.ts");
  assert.doesNotMatch(adminWorkspace, /label: "Teacher Recruitment"/);
  assert.doesNotMatch(routes, /adminRecruitment/);
});

test("tasks use compact status tabs", () => {
  const tasks = source("TasksView.tsx");
  assert.match(tasks, /const taskTabs = \["open", "completed", "cancelled"\]/);
  assert.match(tasks, /role="tablist"/);
});
