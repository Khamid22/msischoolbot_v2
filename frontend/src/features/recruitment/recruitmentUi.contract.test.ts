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

  test("uses a single-stage mobile view and eight independently scrolling desktop columns", () => {
    assert.match(pipeline, /md:hidden/);
    assert.match(pipeline, /grid min-w-\[1600px\] grid-cols-8/);
    assert.match(pipeline, /overflow-y-auto/);
    assert.match(pipeline, /h-\[calc\(100dvh-20rem\)\]/);
    assert.match(pipeline, /dragOverStage/);
  });

  test("reveals only Trash Bin and Reject targets during a drag", () => {
    assert.match(pipeline, /Candidate outcome drop targets/);
    assert.match(pipeline, /\["trash_bin", "rejected"\]/);
    assert.match(pipeline, /target === "trash_bin" \? "Trash Bin" : "Reject"/);
    assert.match(pipeline, /setRejectSelection/);
    assert.match(pipeline, /\/final-decisions/);
    assert.doesNotMatch(pipeline, /\["trash_bin", "on_hold", "candidate_withdrew", "rejected"\]/);
    assert.doesNotMatch(pipeline, /delete.*candidate/i);
  });

  test("moves first and schedules Interview or Demo from the yellow warning", () => {
    assert.match(pipeline, /<AppointmentForm/);
    assert.match(pipeline, /Interview not scheduled/);
    assert.match(pipeline, /Demo lesson not scheduled/);
    assert.match(pipeline, /\/appointments/);
    assert.doesNotMatch(pipeline, /\/scheduled-stage-moves/);
    assert.doesNotMatch(pipeline, /Schedule & move/);
    assert.match(pipeline, /appointmentConflictDetails/);
    assert.match(pipeline, /setScheduleSelection/);
  });

  test("renders the seven-segment filtered percentage summary without a chart dependency", () => {
    assert.match(pipeline, /const chartStages = \[/);
    for (const stage of ["new_candidate", "responded", "on_hold", "job_interview", "test_and_demo", "teacher_academy", "active_teacher"]) {
      assert.match(pipeline, new RegExp(`stage: "${stage}"`));
    }
    assert.match(pipeline, /Pipeline distribution\. Total/);
    assert.match(pipeline, /h-2\.5/);
    assert.match(pipeline, /100 - floorTotal/);
    assert.match(pipeline, /\{item\.percentage\}%/);
    assert.doesNotMatch(pipeline, /recharts|chart\.js/i);
  });
});

describe("candidate navigation and progressive disclosure", () => {
  const profile = source("CandidateProfile.tsx");
  const list = source("CandidateListView.tsx");
  const workspace = source("RecruitmentWorkspace.tsx");

  test("gives HR four URL-backed tabs, inline editing, voidable evaluations, and a history drawer", () => {
    for (const tab of ["overview", "evaluations", "documents", "hiring"]) {
      assert.match(profile, new RegExp(`key: "${tab}"`));
    }
    assert.match(profile, /const hrProfileTabs = profileTabs\.filter\(\(item\) => item\.key !== "activity"\)/);
    assert.match(profile, /url\.searchParams\.set\("tab", next\)/);
    assert.match(profile, /<Drawer/);
    assert.match(profile, /<InlineField/);
    assert.match(profile, /expected_version: candidate\.version/);
    assert.match(profile, /Void mistaken result/);
    assert.match(profile, /Read-only audit trail/);
    assert.match(profile, /value="trash_bin"/);
    assert.match(profile, /appointments are scheduled separately after the move/);
    assert.doesNotMatch(profile, /\/scheduled-stage-moves/);
    assert.match(profile, /candidate\.next_appointment/);
    assert.match(profile, /Upcoming appointments/);
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
    assert.ok(workspace.indexOf('key: "schedule"') < workspace.indexOf('key: "rejected"'));
    assert.ok(workspace.indexOf('key: "rejected"') < workspace.indexOf('key: "trash"'));
    assert.ok(workspace.indexOf('key: "trash"') < workspace.indexOf('key: "settings"'));
  });

  test("uses the lean HR navigation and dedicated Rejected/Withdrawn tabs", () => {
    const rejected = source("RejectedCandidatesView.tsx");
    const hrNav = workspace.match(/if \(effectiveRole === "hr_manager"\) return \[[\s\S]*?key: "settings"[\s\S]*?\];/)?.[0] || "";
    for (const label of ["Pipeline", "Schedule", "Rejected", "Trash Bin", "Settings"]) assert.match(hrNav, new RegExp(`label: "${label}"`));
    assert.doesNotMatch(hrNav, /label: "Candidates"|label: "Tasks"/);
    assert.match(rejected, /type OutcomeTab = "rejected" \| "candidate_withdrew"/);
    assert.match(rejected, /origin_stage/);
    assert.match(rejected, /reason_detail/);
  });

  test("opens Academic Director Recruitment on a compact decision queue", () => {
    const decisions = source("DecisionQueueView.tsx");
    assert.match(workspace, /key: "decisions", label: "Decisions"/);
    assert.match(workspace, /view === "decisions" \? <DecisionQueueView/);
    assert.match(decisions, /\/decision-queue\?page=/);
    assert.match(decisions, /actionable_approval/);
    assert.match(decisions, /origin=decisions/);
  });

  test("adds URL-backed agenda and week schedule views without a calendar dependency", () => {
    const schedule = source("ScheduleView.tsx");
    assert.match(workspace, /key: "schedule", label: "Schedule"/);
    assert.match(workspace, /view === "schedule" \? <ScheduleView/);
    assert.match(schedule, /mode === "week"/);
    assert.match(schedule, /md:hidden/);
    assert.match(schedule, /replaceUrlParams/);
    assert.match(schedule, /appointment_type/);
    assert.match(schedule, /responsible_account_id/);
    assert.match(schedule, /Asia\/Tashkent/);
    assert.match(schedule, /scheduleDayLabel\(day\)/);
    assert.match(schedule, /appointmentTimeLabel\(item\)/);
    assert.match(schedule, /min-w-\[70rem\]/);
    assert.doesNotMatch(schedule, /dateLabel\(schoolDayStartIso\(day\)\)/);
    assert.doesNotMatch(schedule, /fullcalendar|react-big-calendar|dnd-kit/i);
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
