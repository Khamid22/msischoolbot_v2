import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test, { describe } from "node:test";

import {
  academyTrainingRows,
  academyTrainingSummary,
  type AcademyTrainingAssessment,
  type AcademyTrainingLesson,
} from "./model.ts";

function source(name: string) {
  return readFileSync(new URL(`./${name}`, import.meta.url), "utf8");
}

function projectSource(relativePath: string) {
  return readFileSync(new URL(`../../${relativePath}`, import.meta.url), "utf8");
}

describe("compact recruitment pipeline", () => {
  const pipeline = source("PipelineView.tsx");

  test("makes the whole card draggable without dotted handle or move menu", () => {
    assert.match(pipeline, /<article[\s\S]*draggable=\{canMove\}/);
    assert.match(pipeline, /draggedCandidateRef/);
    assert.doesNotMatch(pipeline, /GripVertical/);
    assert.doesNotMatch(pipeline, /MoveCandidateDialog/);
    assert.doesNotMatch(pipeline, /The dragged candidate could not be read/);
    assert.doesNotMatch(pipeline, /Move candidate\s*<select/);
    // The only card menu is the appointment 3-dot (reschedule/cancel).
    assert.match(pipeline, /label="Appointment actions"/);
  });

  test("uses a single-stage compact view and a dynamically scrollable desktop board", () => {
    assert.match(pipeline, /xl:hidden/);
    assert.match(pipeline, /data\.columns\.map/);
    assert.match(pipeline, /gridTemplateColumns: `repeat\(\$\{data\.columns\.length\}/);
    assert.match(pipeline, /minWidth: `max\(100%, \$\{data\.columns\.length \* 15\}rem\)`/);
    assert.match(pipeline, /pipeline-board-scroll/);
    assert.match(pipeline, /overflow-x-clip/);
    assert.match(pipeline, /overscroll-x-contain/);
    assert.match(pipeline, /xl:block/);
    assert.match(pipeline, /w-full min-w-0 overflow-hidden border/);
    assert.match(pipeline, /compact \? "rounded-md" : "rounded-lg"/);
    assert.match(pipeline, /overflow-y-auto/);
    assert.match(pipeline, /h-\[calc\(100dvh-9\.75rem\)\]/);
    assert.match(pipeline, /rounded-xl border border-border bg-card px-3 py-1\.5/);
    assert.match(pipeline, /rounded-t-xl border-x border-t/);
    assert.doesNotMatch(pipeline, /max-h-\[52rem\]/);
    assert.match(pipeline, /dragOverStage/);
  });

  test("keeps chart and compact search together with accessible popover behavior", () => {
    assert.match(pipeline, /<PipelineSummary[\s\S]*action=\{/);
    assert.match(pipeline, /aria-label=\{`Search and filters/);
    assert.match(pipeline, /useDismissibleLayer/);
    assert.match(pipeline, /searchInputRef\.current\?\.focus/);
    assert.match(pipeline, /aria-expanded=\{searchOpen\}/);
    assert.match(pipeline, /Search candidates/);
    assert.doesNotMatch(pipeline, /rounded-xl border border-border bg-card p-3[\s\S]{0,220}>Search</);
  });

  test("keeps horizontal board movement contained without taking over vertically scrollable columns", () => {
    assert.match(pipeline, /boardPanRef/);
    assert.match(pipeline, /data-candidate-card/);
    assert.match(pipeline, /data-pipeline-column-scroll/);
    assert.match(pipeline, /Math\.abs\(deltaX\) < 6/);
    assert.match(pipeline, /onPointerMove=\{moveBoardPan\}/);
    assert.match(pipeline, /addEventListener\("wheel", scrollWheelBoard, \{ passive: false \}\)/);
    assert.doesNotMatch(pipeline, /onWheel=\{scrollWheelBoard\}/);
    assert.match(pipeline, /smoothScrollBoardBy/);
    assert.match(pipeline, /prefers-reduced-motion: reduce/);
    assert.match(pipeline, /columnScroller && verticalIntent && !event\.shiftKey/);
    assert.doesNotMatch(pipeline, /columnCanScroll/);
    assert.doesNotMatch(pipeline, /columnScroller\.scrollTop \+ columnScroller\.clientHeight/);
    assert.match(pipeline, /\["ArrowLeft", "ArrowRight"\]/);
    assert.match(pipeline, /\[data-candidate-card\], a, button, input, select, textarea/);
  });

  test("places the HR-only add action in New Candidate headers", () => {
    assert.match(pipeline, /canAddCandidate && onAddCandidate/);
    assert.match(pipeline, /stage\.stage_key === "new_candidate"/);
    assert.match(pipeline, /mobileStage === "new_candidate"/);
    assert.match(pipeline, /aria-label="Add candidate"/);
  });

  test("keeps the original application date visible in custom pipeline stages", () => {
    assert.match(pipeline, /let detailLabel = "Applied"/);
    assert.match(pipeline, /let detailValue = dateLabel\(candidate\.application_date\)/);
    assert.doesNotMatch(pipeline, /candidate\.status === "new_candidate"\) \{ detailLabel = "Applied"/);
  });

  test("keeps optimistic card moves in the canonical column order", () => {
    assert.match(pipeline, /function sortPipelineCards\(stageKey: string/);
    assert.match(pipeline, /\["job_interview", "test_and_demo"\]\.includes\(stageKey\)/);
    assert.match(pipeline, /sortableTime\(leftAppointment\.starts_at\) - sortableTime\(rightAppointment\.starts_at\)/);
    assert.match(pipeline, /pipelineCardRecency\(right\) - pipelineCardRecency\(left\)/);
    assert.match(pipeline, /stages\[stage\] = sortPipelineCards\(stage,/);
  });

  test("reveals Trash Bin, Reject, and Candidate Withdraw targets during a drag", () => {
    assert.match(pipeline, /Candidate outcome drop targets/);
    assert.match(pipeline, /\["trash_bin", "rejected", "candidate_withdrew"\]/);
    assert.match(pipeline, /target === "rejected" \? "Reject" : "Withdraw"/);
    assert.match(pipeline, /setRejectSelection/);
    assert.match(pipeline, /setWithdrawSelection/);
    assert.match(pipeline, /\/final-decisions/);
    assert.doesNotMatch(pipeline, /on_hold|On Hold/);
    assert.doesNotMatch(pipeline, /delete.*candidate/i);
  });

  test("schedules Interview or Demo from the yellow warning without date restrictions", () => {
    assert.match(pipeline, /<AppointmentForm/);
    assert.match(pipeline, /Interview not scheduled/);
    assert.match(pipeline, /Demo lesson not scheduled/);
    assert.match(pipeline, /\/appointments/);
    assert.doesNotMatch(pipeline, /\/scheduled-stage-moves/);
    assert.doesNotMatch(pipeline, /Schedule & move/);
    assert.doesNotMatch(pipeline, /appointmentConflictDetails/);
    assert.match(pipeline, /setScheduleSelection/);
  });

  test("renders a dynamic summary with canonical teacher totals and one-decimal percentages", () => {
    assert.match(pipeline, /function PipelineSummary\(\{ counts, stages/);
    assert.match(pipeline, /const active = data\?\.columns/);
    assert.match(pipeline, /\["teacher_academy", "active_teacher"\]/);
    assert.match(pipeline, /Pipeline distribution\. Total/);
    assert.match(pipeline, /h-2 min-w-0/);
    assert.match(pipeline, /useCanonicalTeacherRosterTotals/);
    assert.match(pipeline, /teacher_academy: teacherRosterTotals\.teacher_academy/);
    assert.match(pipeline, /active_teacher: teacherRosterTotals\.active_teacher/);
    assert.match(pipeline, /\.toFixed\(1\)/);
    assert.match(pipeline, /\{item\.percentage\}%/);
    assert.doesNotMatch(pipeline, /floorTotal|roundedUp/);
    assert.doesNotMatch(pipeline, /recharts|chart\.js/i);
  });

  test("shows semantic appointment progress and overdue card states", () => {
    assert.match(pipeline, /appointment\?\.is_overdue/);
    assert.match(pipeline, /border-red-400 bg-red-50/);
    assert.match(pipeline, /border-amber-400 bg-amber-50/);
    assert.match(pipeline, /border-emerald-400 bg-emerald-50/);
    assert.match(pipeline, /candidate\.current_sla/);
    assert.match(pipeline, /SLA overdue/);
    assert.match(pipeline, /Evaluator:/);
    assert.match(pipeline, /Topic:/);
    assert.match(pipeline, /overdue \? "Overdue" : "Scheduled"/);
  });

  test("manages dynamic columns in an HR-only drawer with CEO read-only access", () => {
    const workspace = source("RecruitmentWorkspace.tsx");
    assert.match(pipeline, /RECRUITMENT_API}\/pipeline-stages/);
    assert.match(pipeline, /Add workflow stage/);
    assert.match(pipeline, /StageColorPicker/);
    assert.match(pipeline, /SLA after application/);
    assert.match(pipeline, /Move candidates to/);
    assert.match(pipeline, /expected_version: stage\.version/);
    assert.match(pipeline, /stage\.stage_kind === "custom"/);
    assert.match(pipeline, /Only the HR Manager can change pipeline columns/);
    assert.match(workspace, /canViewStageConfiguration=\{\["hr_manager", "ceo"\]\.includes\(effectiveRole\)\}/);
  });
});

describe("recruitment scheduling and browser appointment reminders", () => {
  const appointmentForm = source("AppointmentForm.tsx");
  const model = source("model.ts");
  const pipeline = source("PipelineView.tsx");
  const profile = source("CandidateProfile.tsx");
  const notifications = source("RecruitmentNotifications.tsx");
  const browserReminders = source("BrowserRecruitmentReminders.tsx");
  const workspace = source("RecruitmentWorkspace.tsx");
  const app = projectSource("app/App.tsx");

  test("uses compact date/time controls, auto-assigns HR interviews, and omits scheduling notes", () => {
    assert.match(appointmentForm, /type="date"/);
    assert.match(appointmentForm, /type="time"/);
    assert.match(appointmentForm, /step=\{60\}/);
    assert.doesNotMatch(appointmentForm, /Appointment time|Asia\/Tashkent \(UTC\+5\)/);
    assert.doesNotMatch(appointmentForm, /Responsible interviewer/);
    assert.match(appointmentForm, /demo \? \([\s\S]*Demo evaluator/);
    assert.match(appointmentForm, /Conference link \(optional\)/);
    assert.match(appointmentForm, /Location \(optional\)/);
    assert.doesNotMatch(appointmentForm, /name="note"|>Notes</);
    assert.doesNotMatch(appointmentForm, /Historical result|historical_result|duration_minutes/);
    assert.doesNotMatch(appointmentForm, /min=/);
  });

  test("includes HR staff in the shared demo evaluator role contract", () => {
    assert.match(model, /function isDemoEvaluatorRole/);
    assert.match(model, /\["hr_manager", "academic_director", "head_of_department"\]/);
    assert.match(appointmentForm, /isDemoEvaluatorRole\(person\.role\)/);
    assert.match(pipeline, /isDemoEvaluatorRole\(person\.role\)/);
    assert.match(profile, /isDemoEvaluatorRole\(person\.role\)/);
  });

  test("keeps pipeline-only cards compact and warns about missing subject knowledge", () => {
    assert.match(pipeline, /compact=\{compact\}/);
    assert.match(pipeline, /space-y-1\.5/);
    assert.match(pipeline, /px-2\.5 pb-1\.5 pt-2/);
    assert.match(pipeline, /Subject test missing\/not passed/);
    assert.match(profile, /Subject test missing\/not passed/);
  });

  test("shows generic recruitment notifications and unread recruitment badges", () => {
    assert.match(notifications, /notifications\/unread-count/);
    assert.match(notifications, /Recruitment notifications/);
    assert.match(notifications, /notifications\/\$\{id\}\/read/);
    assert.match(notifications, /unread_only=true/);
    assert.match(notifications, /onMutate/);
    assert.match(notifications, /setQueryData<NotificationPage>/);
    assert.match(notifications, /event\.preventDefault\(\)/);
    assert.match(notifications, /window\.location\.assign/);
    assert.match(notifications, /refetchInterval: 30_000/);
    assert.match(workspace, /badge: notificationUnread/);
  });

  test("uses profile-enabled browser alerts, a top-right toast, and a fixed two-tone preview", () => {
    assert.ok(!existsSync(new URL("./TelegramConnectionCard.tsx", import.meta.url)));
    assert.match(browserReminders, /notifications\/browser-preference/);
    assert.match(browserReminders, /notifications\/browser-alerts\?limit=10/);
    assert.match(browserReminders, /refetchIntervalInBackground: true/);
    assert.match(browserReminders, /notifications\/browser-test/);
    assert.match(browserReminders, /Notification\.requestPermission\(\)/);
    assert.match(browserReminders, /new Notification\(alert\.title/);
    assert.match(browserReminders, /659\.25/);
    assert.match(browserReminders, /880/);
    assert.match(browserReminders, /lg:top-\[4\.5rem\]/);
    assert.match(browserReminders, /Open candidate/);
    assert.match(browserReminders, /At least one MSI portal tab must remain open/);
    assert.match(workspace, /BrowserReminderPreferencesCard/);
    assert.match(app, /<BrowserRecruitmentReminders/);
  });

  test("can undo an accidental appointment start before rescheduling", () => {
    const interviewSession = source("InterviewSessionModal.tsx");
    const demoSession = source("DemoSessionModal.tsx");
    for (const session of [interviewSession, demoSession]) {
      assert.match(session, /\/undo-start/);
      assert.match(session, /Cancel start/);
      assert.match(session, /Restore schedule/);
      assert.match(session, /Keep active/);
      assert.match(session, /pre_start_starts_at/);
    }
    assert.match(pipeline, /Undo start & reschedule/);
    assert.match(pipeline, /Original schedule restored\. Choose a new date and time/);
    assert.match(profile, /Undo accidental start/);
    assert.match(profile, /\/undo-start/);
    assert.match(model, /can_undo_start\?: boolean/);
  });
});

describe("candidate navigation and progressive disclosure", () => {
  const profile = source("CandidateProfile.tsx");
  const list = source("CandidateListView.tsx");
  const workspace = source("RecruitmentWorkspace.tsx");

  test("gives HR URL-backed profile tabs, inline editing, deletable evaluations, and a history drawer", () => {
    for (const tab of ["overview", "evaluations", "documents", "hiring"]) {
      assert.match(profile, new RegExp(`key: "${tab}"`));
    }
    assert.match(profile, /const hrProfileTabs = profileTabs\.filter\(\(item\) => item\.key !== "activity" && item\.key !== "hiring"\)/);
    assert.match(profile, /key: "training"/);
    assert.match(profile, /detail\.data\?\.academy[\s\S]*\[\.\.\.hrProfileTabs, trainingProfileTab\]/);
    assert.match(profile, /tab === "training" && role === "hr_manager" && candidate\.academy/);
    assert.match(profile, /url\.searchParams\.set\("tab", next\)/);
    assert.match(profile, /<Drawer/);
    assert.match(profile, /<InlineField/);
    assert.match(profile, /education_background/);
    assert.match(profile, /Education background/);
    assert.match(profile, /expected_version: candidate\.version/);
    assert.match(profile, /Delete evaluation/);
    assert.match(profile, /permanently/);
    assert.match(profile, /method: "DELETE"/);
    assert.match(profile, /Read-only audit trail/);
    assert.doesNotMatch(profile, /kind: "move_candidate"/);
    assert.doesNotMatch(profile, /kind: "record_interview"/);
    assert.doesNotMatch(profile, /kind: "record_demo"/);
    assert.match(profile, /Candidate Withdraw/);
    assert.match(profile, /View History/);
    assert.doesNotMatch(profile, /\/scheduled-stage-moves/);
    assert.match(profile, /candidate\.next_appointment/);
    assert.doesNotMatch(profile, /title="Upcoming appointments"/);
    assert.match(profile, /<InterviewSessionModal/);
    assert.match(profile, /title="Job Interviews"/);
    assert.match(profile, /latestDetails=\{\[/);
    assert.match(profile, /Interview notes/);
    for (const field of [
      "English level",
      "Education background",
      "Teaching experience",
      "Interests",
      "Motivation",
    ]) {
      assert.match(profile, new RegExp(`label: "${field}"`));
    }
    assert.match(profile, /can_add_subject_test/);
    assert.match(profile, /Record subject test/);
  });

  test("renders canonical Academy training details in a responsive expandable table", () => {
    assert.match(profile, /title="Academy training"/);
    assert.match(profile, /Start date/);
    assert.match(profile, /Assigned/);
    assert.match(profile, /Passed/);
    assert.match(profile, /Failed/);
    assert.match(profile, /Avg score/);
    assert.match(profile, /Assigned Topics/);
    assert.match(profile, /Evaluated Date/);
    assert.match(profile, /Evaluated By/);
    assert.match(profile, /Average Score/);
    assert.match(profile, /Head Of \$\{academyDepartmentName\(subject, position\)\} Department/);
    assert.doesNotMatch(profile, /Assignment \/ schedule/);
    assert.match(profile, /overflow-x-auto overscroll-x-contain/);
    assert.match(profile, /space-y-2 lg:hidden/);
    assert.match(profile, /Awaiting evaluation/);
    assert.match(profile, /section_feedback/);
    assert.match(profile, /Assessment criteria/);
    assert.match(profile, /Lesson areas/);
    assert.match(profile, /areas_for_improvement/);
    assert.match(profile, /final_recommendation/);
    assert.match(profile, /role="progressbar"/);
    assert.match(profile, /role=\{assessment \? "button" : undefined\}/);
    assert.doesNotMatch(profile, />Read-only</);
    const trainingPanel =
      profile.split("function TrainingPanel")[1]?.split("function OutcomeFields")[0] || "";
    assert.doesNotMatch(
      trainingPanel,
      /onSave|mutation\.mutate|ActionMenu/,
    );
  });

  test("starts assigned demos with overwrite confirmation and records Pass or Fail", () => {
    const demoSession = source("DemoSessionModal.tsx");
    assert.match(profile, /<DemoSessionModal/);
    assert.match(demoSession, /Start demo lesson now\?/);
    assert.match(demoSession, /scheduled date and time will be overwritten/);
    assert.match(demoSession, />\s*Cancel\s*</);
    assert.match(demoSession, />[\s\S]*Proceed\s*</);
    assert.match(demoSession, /complete\.mutate\("passed"\)/);
    assert.match(demoSession, /complete\.mutate\("failed"\)/);
    assert.match(demoSession, /Evaluator notes/);
    assert.doesNotMatch(demoSession, /Score \(0–10\)|Criterion result|Academic recommendation/);
    assert.match(
      profile,
      /scheduledAppointments\.find\([\s\S]*appointment_type === "demo_lesson"/,
    );
  });

  test("records a compact subject percentage and Passed or Failed status", () => {
    const testFields = profile.split('case "record_test":')[1]?.split('case "record_demo":')[0] || "";
    assert.match(profile, /open=\{action\?\.kind === "record_test"\}/);
    assert.match(profile, /title="Record subject test"/);
    assert.match(profile, /subjectTestPaperTitle\(candidate\)/);
    assert.match(testFields, /Subject test/);
    assert.match(testFields, /Percentage/);
    assert.match(testFields, /Status/);
    assert.match(testFields, /value="passed">Passed/);
    assert.match(testFields, /value="failed">Failed/);
    assert.doesNotMatch(testFields, /Paper \/ version|Maximum score|Topic result|Notes/);
    assert.match(profile, /maximum_score: 100/);
    assert.match(profile, /<SubjectTestList/);
  });

  test("keeps inline editors dimensionally stable and protects unsaved field changes", () => {
    assert.match(profile, /relative h-16 min-h-16 min-w-0/);
    assert.match(profile, /absolute inset-x-0 top-0 z-20/);
    assert.match(profile, /activeInlineField/);
    assert.match(profile, /pendingInlineField/);
    assert.match(profile, /inlineFieldDirty/);
    assert.match(profile, /useDismissibleLayer/);
    assert.match(profile, /onRequestDismiss: requestInlineDismiss/);
    assert.match(profile, /data-inline-edit-trigger/);
    assert.match(profile, /confirmInlineClose/);
    assert.match(profile, /Discard unsaved change\?/);
    assert.match(profile, /Discard & continue/);
    assert.match(profile, /Keep editing/);
    assert.doesNotMatch(profile, /const \[editing, setEditing\]/);
  });

  test("keeps only search and stage visible while advanced filters use a drawer", () => {
    assert.match(list, /title="Candidate filters"/);
    assert.match(list, /activeFilters/);
    assert.match(list, /replaceUrlParams\(\{ page, \.\.\.filters \}/);
  });

  test("opts Recruitment into adaptive collapsible navigation without a Profile nav item", () => {
    assert.match(workspace, /desktopSidebarMode="collapsible"/);
    assert.match(workspace, /desktopSidebarInitialState="adaptive"/);
    assert.match(workspace, /<AcademicDirectorPageShell/);
    assert.match(workspace, /<HeadOfDepartmentPageShell/);
    assert.match(workspace, /recruitmentView=\{academicRecruitmentView\}/);
    assert.doesNotMatch(workspace, /key: "profile", label: "Profile"/);
  });

  test("keeps Add Candidate compact and centered instead of fullscreen", () => {
    assert.match(workspace, /title="Add candidate" size="lg" mobileMode="sheet"/);
    assert.doesNotMatch(workspace, /title="Add candidate"[^>]*mobileMode="fullscreen"/);
    assert.match(workspace, /name="candidate_cv" type="file"/);
    assert.match(workspace, /documentData\.append\("document_type", "cv"\)/);
    assert.match(workspace, /Candidate and CV added/);
    assert.match(workspace, /CV must be 20 MB or smaller/);
  });

  test("opens documents directly while keeping permission-scoped replace and remove controls", () => {
    const documentPanel = profile.split('{tab === "documents" ? (')[1]?.split('{tab === "hiring" ? (')[0] || "";
    assert.match(documentPanel, /href=\{`\$\{RECRUITMENT_API\}\/candidates\/\$\{candidateId\}\/documents\/\$\{text\(document\.id\)\}\/open`\}/);
    assert.match(documentPanel, /target="_blank"/);
    assert.match(documentPanel, /rel="noopener noreferrer"/);
    assert.match(documentPanel, /role === "hr_manager" && permissions\?\.can_manage_documents/);
    assert.match(documentPanel, /<IconButton label=\{`Replace/);
    assert.match(documentPanel, /<IconButton label=\{`Remove/);
    assert.doesNotMatch(documentPanel, /<ActionMenu/);
    assert.doesNotMatch(documentPanel, /Download|download=true/);
  });

  test("uses the shared fading toast instead of a full-width warning banner", () => {
    assert.match(workspace, /useFloatingToast\(\)/);
    assert.match(workspace, /<FloatingToast toast=\{toast\}/);
    assert.doesNotMatch(workspace, /announcement \? <div/);
  });

  test("adds HR-only immutable analytics dimensions and dependent subsources", () => {
    const settings = source("SettingsView.tsx");
    const pipeline = source("PipelineView.tsx");
    assert.match(workspace, /effectiveRole === "hr_manager"/);
    assert.match(workspace, /key: "settings", label: "Settings"/);
    assert.match(workspace, /<SettingsView/);
    assert.match(settings, /Candidate sources/);
    assert.match(settings, /Source details/);
    assert.match(settings, /Teacher positions/);
    assert.match(settings, /English levels/);
    assert.match(settings, /Expected salary/);
    assert.match(settings, /Teaching experience/);
    assert.match(settings, /parent_id/);
    assert.match(settings, /Rejection reasons/);
    assert.match(settings, /RECRUITMENT_API}\/settings/);
    assert.match(settings, /Stage SLA targets/);
    assert.match(settings, /sla-rules/);
    assert.match(settings, /Appointment reminder timing/);
    assert.match(settings, /settings\/appointment-reminders/);
    assert.match(settings, /Short-notice appointments/);
    assert.match(workspace, /name="position_option_id"/);
    assert.match(profile, /position_option_id/);
    assert.match(pipeline, /option_categories\.position/);
  });

  test("gives Settings inline rename, restore of removed options, usage counts, grouped subsources, and board-matching SLA labels", () => {
    const settings = source("SettingsView.tsx");
    // Inline rename via PATCH, not delete-and-readd.
    assert.match(settings, /RECRUITMENT_API\}\/settings\/\$\{setting\.id\}`,\s*\n\s*body: \{ label \}/);
    assert.match(settings, /startRename/);
    // Removed options stay visible and restorable instead of disappearing.
    assert.match(settings, /Show removed/);
    assert.match(settings, /\/restore`/);
    // Usage counts shown on rows and surfaced in the delete confirmation.
    assert.match(settings, /usage_count/);
    assert.match(settings, /Used by/);
    // Source details are grouped under their parent source, not a flat list.
    assert.match(settings, /groupByParent/);
    assert.match(settings, /No source/);
    // SLA stage names reuse the same labels as the pipeline board.
    assert.match(settings, /rule\.stage_label \|\| humanize\(rule\.stage\)/);
    // CEO sees the option panels (read-only), not a hidden section.
    assert.doesNotMatch(settings, /!settings\.data\.read_only \? <div className="grid/);
    assert.match(settings, /readOnly=\{settings\.data\.read_only\}/);
  });

  test("adds an essential HR and CEO recruitment analytics dashboard", () => {
    const analytics = source("AnalyticsView.tsx");
    assert.match(workspace, /key: "analytics", label: "Analytics"/);
    assert.match(workspace, /<AnalyticsView/);
    assert.match(analytics, /\/api\/v1\/hr\/analytics/);
    assert.match(analytics, /Applications/);
    assert.match(analytics, /Final Decision/);
    assert.match(analytics, /Teacher Academy/);
    assert.match(analytics, /Active Teachers/);
    assert.match(analytics, /Job Interviews/);
    assert.match(analytics, /Demo Lessons/);
    assert.match(analytics, /Subject Tests/);
    assert.match(analytics, /academy_total/);
    assert.match(analytics, /Total \{numberValue/);
    assert.match(analytics, /Current active pipeline/);
    assert.match(analytics, /SLA overdue now/);
    assert.match(analytics, /type="month"/);
    assert.match(analytics, /disabled=\{selectedMonth >= currentMonth\}/);
    assert.match(analytics, /Live snapshot/);
    assert.match(analytics, /Recruitment journey/);
    assert.match(analytics, /Applicant sources/);
    assert.match(analytics, /Applications by position/);
    assert.match(analytics, /Stage time and SLA/);
    assert.match(analytics, /Source quality/);
    assert.match(analytics, /Recent candidates/);
    assert.match(analytics, /Recent activity/);
    assert.match(analytics, /<Drawer/);
    assert.match(analytics, /roleIsHr/);
    assert.match(analytics, /motion-reduce/);
    assert.doesNotMatch(analytics, /Current Vacanc|Recruitment cost|Salary budget/);
  });

  test("uses a dedicated HR-only Trash Bin that cannot expose active candidates", () => {
    const trash = source("TrashBinView.tsx");
    assert.match(workspace, /effectiveRole === "hr_manager"/);
    assert.match(workspace, /key: "trash", label: "Trash Bin", href: `\$\{basePath\}\/trash`/);
    assert.match(workspace, /view === "trash" && effectiveRole === "hr_manager" \? <TrashBinView/);
    assert.match(trash, /stage: "trash_bin"/);
    assert.match(trash, /ClosedCandidateActions/);
    assert.match(trash, /EMPTY TRASH BIN/);
    assert.match(trash, /useViewportPageSize/);
    assert.match(trash, /origin=trash/);
    assert.doesNotMatch(trash, /filters\.stage/);
    assert.match(profile, /origin === "trash" \? `\$\{basePath\}\/trash/);
    assert.ok(workspace.indexOf('key: "schedule"') < workspace.indexOf('key: "rejected"'));
    assert.ok(workspace.indexOf('key: "rejected"') < workspace.indexOf('key: "trash"'));
    assert.ok(workspace.indexOf('key: "trash"') < workspace.indexOf('key: "settings"'));
  });

  test("uses the lean HR navigation and dedicated Rejected/Withdrawn tabs", () => {
    const rejected = source("RejectedCandidatesView.tsx");
    const hrNav = workspace.match(/if \(effectiveRole === "hr_manager"\) return \[[\s\S]*?key: "settings"[\s\S]*?\];/)?.[0] || "";
    for (const label of ["Pipeline", "Teachers", "Analytics", "Schedule", "Rejected", "Trash Bin", "Settings"]) assert.match(hrNav, new RegExp(`label: "${label}"`));
    assert.doesNotMatch(hrNav, /label: "Candidates"|label: "Tasks"/);
    assert.match(rejected, /type OutcomeTab = "rejected" \| "candidate_withdrew"/);
    assert.match(rejected, /origin_stage/);
    assert.match(rejected, /reason_detail/);
    assert.match(rejected, /ClosedCandidateActions/);
    assert.match(rejected, /useViewportPageSize/);
  });

  test("moves Academy and Active outcomes into a dedicated Teachers switcher", () => {
    const teachers = source("TeachersView.tsx");
    const roster = projectSource("features/teacher-academy/TeacherAcademyRoster.tsx");
    const academyPanel = projectSource("features/teacher-academy/TeacherAcademyPanel.tsx");
    const pipeline = source("PipelineView.tsx");
    assert.match(workspace, /key: "teachers", label: "Teachers"/);
    assert.match(teachers, /teacher_academy/);
    assert.match(teachers, /active_teacher/);
    assert.match(teachers, /Teacher Academy/);
    assert.match(teachers, /Active Teachers/);
    assert.match(teachers, /role="tablist"/);
    assert.match(teachers, /role="tab"/);
    assert.match(teachers, /TeacherAcademyRoster/);
    assert.match(roster, /recruitment_candidate_id/);
    assert.match(roster, /Added to Teacher Academy/);
    assert.match(roster, /Academy status/);
    assert.match(roster, /assigned_count/);
    assert.match(roster, /passed_count/);
    assert.match(roster, /Delete to Trash Bin/);
    assert.match(roster, /Reject teacher/);
    assert.match(roster, /teachers\/\$\{closeSelection\?\.teacher\.kind\}\/\$\{closeSelection\?\.teacher\.record_id\}\/close/);
    assert.match(roster, /All subjects/);
    assert.match(roster, /teacher_subject/);
    assert.match(roster, /teacher_sort/);
    assert.match(roster, /teacher_page/);
    assert.match(roster, /DESKTOP_MIN_PAGE_SIZE = 10/);
    assert.match(roster, /MOBILE_PAGE_SIZE = 5/);
    assert.match(roster, /group h-12 cursor-pointer/);
    assert.match(roster, />Actions<\/th>/);
    assert.doesNotMatch(roster, /<th[^>]*>Account<\/th>/);
    assert.doesNotMatch(roster, /<dt[^>]*>Account<\/dt>/);
    assert.match(roster, /toolbarLeading/);
    assert.match(teachers, /toolbarLeading=\{teacherTabs\}/);
    assert.match(roster, /ResponsiveTable/);
    assert.match(roster, /MobileCardList/);
    assert.match(academyPanel, /<TeacherAcademyRoster/);
    assert.doesNotMatch(teachers, /min-h-20/);
    assert.doesNotMatch(teachers, /TeacherCard/);
    assert.doesNotMatch(pipeline, /boardStages.*teacher_academy/);
  });

  test("opens Academic Director Recruitment on a compact decision queue", () => {
    const decisions = source("DecisionQueueView.tsx");
    assert.match(workspace, /key: "decisions", label: "Decisions"/);
    assert.match(workspace, /view === "decisions" \? <DecisionQueueView/);
    assert.match(decisions, /\/decision-queue\?page=/);
    assert.match(decisions, /actionable_approval/);
    assert.match(decisions, /origin=decisions/);
  });

  test("limits Head of Department Recruitment to assigned operational work", () => {
    const hodNav = workspace.match(/if \(effectiveRole === "head_of_department"\) return \[[\s\S]*?\];/)?.[0] || "";
    for (const label of ["Assigned Candidates", "Assigned Schedule"]) assert.match(hodNav, new RegExp(`label: "${label}"`));
    assert.doesNotMatch(hodNav, /Pipeline|Analytics|Rejected|Trash Bin|Settings|Decisions|Tasks/);
  });

  test("adds an action-first URL-backed day and week schedule without a calendar dependency", () => {
    const schedule = source("ScheduleView.tsx");
    assert.match(workspace, /key: "schedule", label: "Schedule"/);
    assert.match(workspace, /view === "schedule" \? <ScheduleView/);
    assert.match(workspace, /Manage upcoming sessions and review evaluation history/);
    assert.match(schedule, /type ScheduleMode = "day" \| "week"/);
    assert.match(schedule, /type ScheduleSection = "queue" \| "history"/);
    assert.match(schedule, /mode === "week"/);
    assert.match(schedule, /queueStatusFilter = "scheduled,in_progress"/);
    assert.match(schedule, /historyStatusFilter = "passed,failed,not_conducted"/);
    assert.match(schedule, /schedule_section/);
    assert.match(schedule, /replaceUrlParams/);
    assert.match(schedule, /appointment_type/);
    assert.match(schedule, /responsible_account_id/);
    assert.match(schedule, /Asia\/Tashkent/);
    assert.match(schedule, /scheduleDayLabel\(day\)/);
    assert.match(schedule, /appointmentTimeLabel\(item\)/);
    assert.match(schedule, /type="date"/);
    assert.match(schedule, /Work Queue/);
    assert.match(schedule, /History/);
    assert.match(schedule, /overdue.*appointment/);
    assert.match(schedule, /not_conducted/);
    assert.match(schedule, /Passed/);
    assert.match(schedule, /Failed/);
    assert.match(schedule, /Overdue/);
    assert.match(schedule, /evaluated_by_name/);
    assert.match(schedule, /Array\.from\(\{ length: 6 \}/);
    assert.match(schedule, /addDaysToDateKey\(fullWeekBounds\.start, 5\)/);
    assert.match(schedule, /grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-6/);
    assert.match(schedule, /xl:overflow-y-auto/);
    assert.match(schedule, /InterviewSessionModal/);
    assert.match(schedule, /DemoSessionModal/);
    assert.match(schedule, /item\.can_start/);
    assert.match(schedule, /item\.can_resume/);
    assert.match(schedule, /placeholderData: keepPreviousData/);
    assert.doesNotMatch(schedule, /Completed/);
    assert.doesNotMatch(schedule, /overflow-x-auto|min-w-\[84rem\]/);
    assert.doesNotMatch(schedule, /fullcalendar|react-big-calendar|dnd-kit/i);
  });
});

describe("Academy training data matching", () => {
  test("matches only the newest assessment to each assignment without duplicating lessons", () => {
    const lessons: AcademyTrainingLesson[] = [
      { id: 11, lesson_number: "1", lesson_topic: "Fractions" },
      { id: 12, lesson_number: "2", lesson_topic: "Algebra" },
      { id: 12, lesson_number: "2", lesson_topic: "Duplicate payload row" },
    ];
    const assessments: AcademyTrainingAssessment[] = [
      {
        id: 21,
        lesson_assignment_id: 11,
        assessment_datetime: "2026-07-18T09:00:00Z",
        weighted_overall_score: 6.5,
        decision: "needs_improvement",
      },
      {
        id: 22,
        lesson_assignment_id: 11,
        assessment_datetime: "2026-07-19T09:00:00Z",
        weighted_overall_score: 8,
        decision: "passed",
      },
      {
        id: 23,
        lesson_assignment_id: null,
        weighted_overall_score: 10,
        decision: "passed",
      },
    ];

    const rows = academyTrainingRows(lessons, assessments);
    assert.equal(rows.length, 2);
    assert.equal(rows[0].assessment?.id, 22);
    assert.equal(rows[1].assessment, null);
    assert.deepEqual(academyTrainingSummary(rows), {
      assigned: 2,
      evaluated: 1,
      passed: 1,
      failed: 0,
      averageScore: 8,
      completionPercentage: 50,
      isComplete: false,
      canPromote: false,
    });
  });

  test("sorts evaluated lessons from the oldest evaluation to the most recent", () => {
    const rows = academyTrainingRows(
      [
        { id: 71, sequence_no: 1, lesson_topic: "First assigned" },
        { id: 72, sequence_no: 2, lesson_topic: "Second assigned" },
        { id: 73, sequence_no: 3, lesson_topic: "Not evaluated" },
      ],
      [
        {
          id: 82,
          lesson_assignment_id: 71,
          assessment_datetime: "2026-07-20T09:00:00Z",
          decision: "passed",
        },
        {
          id: 81,
          lesson_assignment_id: 72,
          assessment_datetime: "2026-07-08T09:00:00Z",
          decision: "passed",
        },
      ],
    );

    assert.deepEqual(
      rows.map((row) => row.lesson.id),
      [72, 71, 73],
    );
  });

  test("counts evaluated lessons with missing scores without corrupting the average", () => {
    const rows = academyTrainingRows(
      [{ id: 31 }, { id: 32 }],
      [
        {
          id: 41,
          lesson_assignment_id: 31,
          weighted_overall_score: null,
          decision: "needs_improvement",
        },
      ],
    );
    assert.deepEqual(academyTrainingSummary(rows), {
      assigned: 2,
      evaluated: 1,
      passed: 0,
      failed: 1,
      averageScore: null,
      completionPercentage: 50,
      isComplete: false,
      canPromote: false,
    });
  });

  test("promotes only after every assigned lesson passes above a 7.0 average", () => {
    const rows = academyTrainingRows(
      [{ id: 51 }, { id: 52 }],
      [
        {
          id: 61,
          lesson_assignment_id: 51,
          weighted_overall_score: 7.1,
          decision: "passed",
        },
        {
          id: 62,
          lesson_assignment_id: 52,
          weighted_overall_score: 7.3,
          decision: "passed",
        },
      ],
    );
    assert.deepEqual(academyTrainingSummary(rows), {
      assigned: 2,
      evaluated: 2,
      passed: 2,
      failed: 0,
      averageScore: 7.2,
      completionPercentage: 100,
      isComplete: true,
      canPromote: true,
    });
  });
});

test("removed Internal Operations workspace exposes no Recruitment routes", () => {
  const routes = projectSource("shared/lib/routes.ts");
  assert.equal(
    existsSync(new URL("../../internal_operations", import.meta.url)),
    false,
  );
  assert.doesNotMatch(routes, /adminRecruitment/);
});

test("tasks use compact status tabs", () => {
  const tasks = source("TasksView.tsx");
  assert.match(tasks, /const taskTabs = \["open", "completed", "cancelled"\]/);
  assert.match(tasks, /role="tablist"/);
});
