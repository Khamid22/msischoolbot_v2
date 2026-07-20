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

  test("uses a single-stage compact view and five screen-fitted desktop columns", () => {
    assert.match(pipeline, /xl:hidden/);
    assert.match(pipeline, /grid w-full min-w-0 grid-cols-5/);
    assert.doesNotMatch(pipeline, /min-w-\[1200px\]|minmax\(240px,1fr\)/);
    assert.match(pipeline, /no-scrollbar/);
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

  test("supports empty-space board panning without taking over candidate cards", () => {
    assert.match(pipeline, /boardPanRef/);
    assert.match(pipeline, /data-candidate-card/);
    assert.match(pipeline, /Math\.abs\(deltaX\) < 6/);
    assert.match(pipeline, /onPointerMove=\{moveBoardPan\}/);
    assert.match(pipeline, /onWheel=\{shiftWheelBoard\}/);
    assert.match(pipeline, /\["ArrowLeft", "ArrowRight"\]/);
    assert.match(pipeline, /\[data-candidate-card\], a, button, input, select, textarea/);
  });

  test("places the HR-only add action in New Candidate headers", () => {
    assert.match(pipeline, /canAddCandidate && onAddCandidate/);
    assert.match(pipeline, /stage === "new_candidate"/);
    assert.match(pipeline, /mobileStage === "new_candidate"/);
    assert.match(pipeline, /aria-label="Add candidate"/);
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

  test("renders the six-segment filtered percentage summary without a chart dependency", () => {
    assert.match(pipeline, /const chartStages = \[/);
    for (const stage of ["new_candidate", "responded", "job_interview", "test_and_demo", "teacher_academy", "active_teacher"]) {
      assert.match(pipeline, new RegExp(`stage: "${stage}"`));
    }
    assert.match(pipeline, /Pipeline distribution\. Total/);
    assert.match(pipeline, /h-2\.5/);
    assert.match(pipeline, /100 - floorTotal/);
    assert.match(pipeline, /\{item\.percentage\}%/);
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
});

describe("recruitment scheduling and assigned-demo notifications", () => {
  const appointmentForm = source("AppointmentForm.tsx");
  const pipeline = source("PipelineView.tsx");
  const profile = source("CandidateProfile.tsx");
  const notifications = source("RecruitmentNotifications.tsx");
  const telegram = source("TelegramConnectionCard.tsx");

  test("uses compact date/time controls, auto-assigns HR interviews, and omits scheduling notes", () => {
    assert.match(appointmentForm, /type="date"/);
    assert.match(appointmentForm, /type="time"/);
    assert.match(appointmentForm, /step=\{900\}/);
    assert.match(appointmentForm, /step=\{15\}/);
    assert.doesNotMatch(appointmentForm, /Appointment time|Asia\/Tashkent \(UTC\+5\)/);
    assert.doesNotMatch(appointmentForm, /Responsible interviewer/);
    assert.match(appointmentForm, /demo && !historical \? <label[\s\S]*Demo evaluator/);
    assert.match(appointmentForm, /Conference link \(optional\)/);
    assert.match(appointmentForm, /Location \(optional\)/);
    assert.doesNotMatch(appointmentForm, /name="note"|>Notes</);
    assert.match(appointmentForm, /Historical result/);
    assert.match(appointmentForm, /name="historical_result"/);
    assert.match(appointmentForm, /isPastTashkentAppointment/);
  });

  test("keeps pipeline-only cards compact and warns about missing subject knowledge", () => {
    assert.match(pipeline, /compact=\{compact\}/);
    assert.match(pipeline, /space-y-1\.5/);
    assert.match(pipeline, /px-2\.5 pb-1\.5 pt-2/);
    assert.match(pipeline, /Subject test missing\/not passed/);
    assert.match(profile, /Subject test missing\/not passed/);
  });

  test("shows recipient-scoped demo notifications and unread recruitment badges", () => {
    assert.match(notifications, /notifications\/unread-count/);
    assert.match(notifications, /Assigned demo lessons/);
    assert.match(notifications, /notifications\/\$\{id\}\/read/);
    assert.match(notifications, /unread_only=true/);
    assert.match(notifications, /onMutate/);
    assert.match(notifications, /setQueryData<NotificationPage>/);
    assert.match(notifications, /event\.preventDefault\(\)/);
    assert.match(notifications, /window\.location\.assign/);
    assert.match(notifications, /refetchInterval: 30_000/);
  });

  test("links Telegram only with Mini App initData and supports unlinking", () => {
    assert.match(telegram, /Telegram\?\.WebApp\?\.initData/);
    assert.match(telegram, /init_data: telegramInitData\(\)/);
    assert.match(telegram, /method: "DELETE"/);
    assert.match(telegram, /Open Telegram Mini App/);
    assert.doesNotMatch(telegram, /telegram_user_id|raw Telegram/i);
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
    assert.match(profile, /education_background/);
    assert.match(profile, /Education background/);
    assert.match(profile, /expected_version: candidate\.version/);
    assert.match(profile, /Void mistaken result/);
    assert.match(profile, /Read-only audit trail/);
    assert.match(profile, /value="trash_bin"/);
    assert.match(profile, /appointments are scheduled separately after the move/);
    assert.doesNotMatch(profile, /\/scheduled-stage-moves/);
    assert.match(profile, /candidate\.next_appointment/);
    assert.doesNotMatch(profile, /title="Upcoming appointments"/);
    assert.match(profile, /<InterviewSessionModal/);
    assert.match(profile, /title="Job Interviews"/);
    assert.match(profile, /can_add_subject_test/);
    assert.match(profile, /Record subject test/);
  });

  test("records scheduled demo lessons in a compact Pass or Reject modal", () => {
    const demoFields = profile.split('case "record_demo":')[1]?.split('case "schedule_appointment":')[0] || "";
    assert.match(profile, /open=\{action\?\.kind === "record_demo"\}/);
    assert.match(profile, /title="Record demo lesson"/);
    assert.match(profile, /size="sm"/);
    assert.match(demoFields, /Date/);
    assert.match(demoFields, /Time/);
    assert.match(demoFields, /Full name/);
    assert.match(demoFields, /Evaluator's notes/);
    assert.doesNotMatch(demoFields, /Score \(0–10\)|Criterion result|Academic recommendation|name="score"/);
    assert.match(profile, /name="result" value="passed"[\s\S]*Pass/);
    assert.match(profile, /name="result" value="failed"[\s\S]*Reject/);
    assert.match(profile, /scheduledAppointments\.find\(\(item\) => item\.appointment_type === "demo_lesson"/);
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
    assert.match(workspace, /name="position_option_id"/);
    assert.match(profile, /position_option_id/);
    assert.match(pipeline, /option_categories\.position/);
  });

  test("adds an essential HR and CEO recruitment analytics dashboard", () => {
    const analytics = source("AnalyticsView.tsx");
    assert.match(workspace, /key: "analytics", label: "Analytics"/);
    assert.match(workspace, /<AnalyticsView/);
    assert.match(analytics, /\/api\/v1\/hr\/analytics/);
    assert.match(analytics, /Applications/);
    assert.match(analytics, /Shortlisted/);
    assert.match(analytics, /Academy accepted/);
    assert.match(analytics, /academy_total/);
    assert.match(analytics, /Total \{numberValue/);
    assert.match(analytics, /Current active pipeline/);
    assert.match(analytics, /SLA overdue now/);
    assert.match(analytics, /Selected application cohort/);
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
    for (const label of ["Pipeline", "Teachers", "Analytics", "Schedule", "Rejected", "Trash Bin", "Settings"]) assert.match(hrNav, new RegExp(`label: "${label}"`));
    assert.doesNotMatch(hrNav, /label: "Candidates"|label: "Tasks"/);
    assert.match(rejected, /type OutcomeTab = "rejected" \| "candidate_withdrew"/);
    assert.match(rejected, /origin_stage/);
    assert.match(rejected, /reason_detail/);
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
    assert.match(roster, /ActionMenu/);
    assert.match(roster, /All subjects/);
    assert.match(roster, /teacher_subject/);
    assert.match(roster, /teacher_sort/);
    assert.match(roster, /teacher_page/);
    assert.match(roster, /DESKTOP_MIN_PAGE_SIZE = 10/);
    assert.match(roster, /MOBILE_PAGE_SIZE = 5/);
    assert.match(roster, /className="group h-14/);
    assert.doesNotMatch(roster, /<th[^>]*>Actions<\/th>/);
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
    assert.match(schedule, /scheduled,in_progress,completed/);
    assert.match(schedule, /Current & completed/);
    assert.match(schedule, /Evaluated by/);
    assert.match(schedule, /evaluated_by_name/);
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
