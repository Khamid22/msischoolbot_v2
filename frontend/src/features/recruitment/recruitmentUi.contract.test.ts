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

  test("makes the whole card draggable without dotted handle or menu controls", () => {
    assert.match(pipeline, /<article[\s\S]*draggable=\{canMove\}/);
    assert.match(pipeline, /draggedCandidateRef/);
    assert.doesNotMatch(pipeline, /GripVertical/);
    assert.doesNotMatch(pipeline, /<ActionMenu/);
    assert.doesNotMatch(pipeline, /MoveCandidateDialog/);
    assert.doesNotMatch(pipeline, /The dragged candidate could not be read/);
    assert.doesNotMatch(pipeline, /Move candidate\s*<select/);
  });

  test("uses a single-stage mobile view and six compact desktop columns", () => {
    assert.match(pipeline, /md:hidden/);
    assert.match(pipeline, /grid min-w-\[1230px\] grid-cols-6/);
    assert.match(pipeline, /min-h-60/);
    assert.match(pipeline, /dragOverStage/);
  });

  test("reveals CRM outcome targets during a drag and confirms audited decisions", () => {
    assert.match(pipeline, /Candidate outcome drop targets/);
    assert.match(pipeline, /\["trash_bin", "on_hold", "candidate_withdrew", "rejected"\]/);
    assert.match(pipeline, /label: "Trash Bin"/);
    assert.match(pipeline, /border-blue-500\/40 bg-blue-500\/10/);
    assert.match(pipeline, /border-rose-300\/60 bg-rose-100\/60/);
    assert.match(pipeline, /move\.mutate\(\{ candidate, stage: decision \}\)/);
    assert.match(pipeline, /<OutcomeDialog/);
    assert.match(pipeline, /\/final-decisions/);
    assert.doesNotMatch(pipeline, /delete.*candidate/i);
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
    assert.match(profile, /value="trash_bin"/);
    assert.match(profile, /Trash Bin is recoverable/);
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

  test("uses the shared fading toast instead of a full-width warning banner", () => {
    assert.match(workspace, /useFloatingToast\(\)/);
    assert.match(workspace, /<FloatingToast toast=\{toast\}/);
    assert.doesNotMatch(workspace, /announcement \? <div/);
  });

  test("adds HR-only recruitment settings for dynamic sources and rejection reasons", () => {
    const settings = source("SettingsView.tsx");
    assert.match(workspace, /effectiveRole === "hr_manager"/);
    assert.match(workspace, /key: "settings", label: "Settings"/);
    assert.match(workspace, /<SettingsView/);
    assert.match(settings, /Candidate sources/);
    assert.match(settings, /Rejection reasons/);
    assert.match(settings, /RECRUITMENT_API}\/settings/);
  });

  test("uses a dedicated HR-only Trash Bin that cannot expose active candidates", () => {
    const trash = source("TrashBinView.tsx");
    assert.match(workspace, /effectiveRole === "hr_manager"/);
    assert.match(workspace, /key: "trash", label: "Trash Bin", href: `\$\{basePath\}\/trash`/);
    assert.match(workspace, /view === "trash" && effectiveRole === "hr_manager" \? <TrashBinView/);
    assert.match(trash, /stage: "trash_bin"/);
    assert.match(trash, /items\.filter\(\(candidate\) => candidate\.status === "trash_bin"\)/);
    assert.match(trash, /origin=trash/);
    assert.doesNotMatch(trash, /All stages|Candidate filters|filters\.stage/);
    assert.match(profile, /origin === "trash" \? `\$\{basePath\}\/trash/);
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
