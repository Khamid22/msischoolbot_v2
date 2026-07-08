"""Source-level guards for teacher mobile UI/UX behavior."""

from pathlib import Path


ROOT = Path("frontend/src")


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_dismissible_layer_hook_closes_on_outside_pointer_and_escape():
    source = _read("shared/lib/useDismissibleLayer.ts")

    assert 'document.addEventListener("pointerdown"' in source
    assert 'document.addEventListener("keydown"' in source
    assert 'document.removeEventListener("pointerdown"' in source
    assert 'document.removeEventListener("keydown"' in source
    assert 'event.key !== "Escape"' in source
    assert "containsTarget" in source


def test_action_menu_and_academy_modal_use_shared_dismissible_modal():
    action_menu = _read("shared/ui/ActionMenu.tsx")
    academy_panel = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")
    modal_source = _read("shared/ui/Modal.tsx")

    assert "useDismissibleLayer" in action_menu
    assert "dismissibleRefs" in action_menu
    assert 'import { Modal, ModalBody, ModalFooter } from "@/shared/ui/Modal";' in academy_panel
    assert "<Modal" in academy_panel
    assert "<ModalBody" in academy_panel
    assert "<ModalFooter" in academy_panel
    assert "useDismissibleLayer" not in academy_panel
    assert 'role="dialog"' in modal_source
    assert 'aria-modal="true"' in modal_source
    assert "createPortal" in modal_source
    assert "closeOnOutsideClick" in modal_source


def test_teacher_academy_admin_list_has_mobile_cards_and_desktop_table():
    source = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")
    mobile_list = _read("shared/ui/MobileCardList.tsx")
    responsive_table = _read("shared/ui/ResponsiveTable.tsx")

    assert "function AcademyTeacherCard" in source
    assert "MobileCardList" in source
    assert 'className="p-3"' in source
    assert "ResponsiveTable" in source
    assert "max-h-[calc(100dvh-20rem)]" in source
    assert "lg:hidden" in mobile_list
    assert "hidden lg:block" in responsive_table
    assert "No academy lessons assigned." in source
    assert "TeacherAcademyPanel" in source
    assert 'const canCreateAcademyTeacher = Boolean(academyApi.create) && adminMode !== "head_of_department" && authRole !== "head_of_department";' in source
    assert "canScheduleAcademyLesson" in source
    assert "canAssessAcademyLesson" in source
    assert "2xl:max-h-[48rem]" in source


def test_teacher_academy_actions_use_schedule_not_assign():
    source = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")
    shared_source = _read("roles/admin/panels/teachers/shared.ts")
    teacher_home_source = _read("roles/teacher/pages/TeacherHome.tsx")

    assert "Schedule Academy Lesson" in source
    assert "Schedule Training Lesson" not in source
    assert "assign lessons" not in teacher_home_source
    assert '{ key: "training", label: "Lesson Practice"' in shared_source
    assert '{ key: "training", label: "Training"' not in shared_source
    assert "Save Schedule" in source
    assert "Schedule" in source
    assert "\n                                  Assign\n" not in source
    assert "Assign Real Group" not in source
    # Assess is the primary list action; Schedule lives in the action menu.
    assert 'label: "Assess"' in source
    assert 'label: scheduled ? "Reschedule" : "Schedule"' in source
    assert '{scheduled ? "Assess" : "Schedule"}' not in source
    assert "setScheduleTarget({ teacher, assignment: nextAssignment })" in source
    assert "setAssessmentTarget({ teacher, assignment: nextAssignment })" in source
    assert "primaryAction" in source
    assert "secondaryActions" in source
    assert "rowActions" in source
    assert "ActionMenu" in source
    assert "ConfirmDialog" in source
    assert "Delete teacher" in source
    assert "routes.academicDirectorTeacherAcademyDelete" in source
    assert "canDeleteAcademyTeacher" in source
    assert "routes.adminTeacherAcademy" not in source


def test_phase3_shared_responsive_components_exist_and_are_used():
    action_menu = _read("shared/ui/ActionMenu.tsx")
    icon_button = _read("shared/ui/IconButton.tsx")
    metric_card = _read("shared/ui/MetricCard.tsx")
    empty_state = _read("shared/ui/EmptyState.tsx")
    status_badge = _read("shared/ui/StatusBadge.tsx")
    mobile_list = _read("shared/ui/MobileCardList.tsx")
    responsive_table = _read("shared/ui/ResponsiveTable.tsx")
    progress_bar = _read("shared/ui/ProgressBar.tsx")
    academy_source = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")
    announcements_source = _read("roles/admin/panels/AnnouncementsPanel.tsx")

    assert "export function IconButton" in icon_button
    assert "export function MetricCard" in metric_card
    assert "export function EmptyState" in empty_state
    assert "export function StatusBadge" in status_badge
    assert "export function MobileCardList" in mobile_list
    assert "export function ResponsiveTable" in responsive_table
    assert "export function ProgressBar" in progress_bar
    assert "createPortal" in action_menu
    assert "uiLayers.popover" in action_menu
    assert "window.addEventListener(\"scroll\", updateMenuPosition, true)" in action_menu
    assert "IconButton" in academy_source
    assert "MetricCard" in academy_source
    assert "ProgressBar" in academy_source
    assert "EmptyState" in academy_source
    assert "ActionMenu" in announcements_source
    assert "MetricCard" in announcements_source
    assert "EmptyState" in announcements_source


def test_head_of_departments_has_mobile_cards_desktop_table_and_compact_login():
    source = _read("roles/academic_director/pages/HeadOfDepartments.tsx")

    assert "function DepartmentCard" in source
    assert "MobileCardList" in source
    assert 'hideAt="md"' in source
    assert "ResponsiveTable" in source
    assert 'showAt="md"' in source
    assert "MetricCard" in source
    assert "StatusBadge" in source
    assert "EmptyState" in source
    assert "Account Login" in source
    assert "font-mono" in source


def test_teacher_academy_modals_select_assignment_ids():
    source = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")

    # The schedule modal keeps its lesson assignment selector and only picks
    # the lesson plus a date and time; other assignment fields pass through.
    assert 'name="assignment_id"' in source
    assert "onSubmit(asNumber(selectedAssignment.id), {" in source
    assert "Select lesson assignment" in source
    assert 'type="date"' in source
    assert 'type="time"' in source
    assert "session_datetime: sessionDate && sessionTime" in source
    assert 'name="evaluator_id"' not in source
    assert 'name="assignment_type"' not in source
    assert 'name="deadline_date"' not in source
    assert 'name="notes_to_trainee"' not in source
    # The assessment modal assesses the lesson row it was opened from and ends
    # with an explicit Pass/Fail decision behind a confirmation dialog.
    assert "fields.lesson_assignment_id = String(asNumber(assignment.id));" in source
    assert "fields.decision = decision;" in source
    assert 'name="strengths"' in source
    assert 'name="areas_for_improvement"' in source
    assert 'name="final_recommendation"' not in source
    assert 'name="class_label"' not in source
    assert "Save assessment" not in source
    assert "Confirm pass?" in source
    assert "Confirm fail?" in source
    # The detail modal switches between curriculum selection and assigned lessons.
    assert "Subject Curriculum" in source
    assert "CurriculumSelectionTab" in source
    assert "academy_curriculum_item_ids: selectedIds.join" in source


def test_teacher_mobile_bottom_nav_contract():
    source = _read("roles/teacher/pages/TeacherHome.tsx")
    mobile_tabs = source.split("const teacherMobileTabs", 1)[1].split("];", 1)[0]
    active_mobile_tabs = source.split("const activeTeacherMobileTabs", 1)[1].split("];", 1)[0]

    assert 'label: "Home"' in mobile_tabs
    assert 'label: "Lessons"' in mobile_tabs
    assert 'label: "Updates"' in mobile_tabs
    assert 'label: "Profile"' in mobile_tabs
    assert 'label: "Home"' in active_mobile_tabs
    assert 'label: "Reports"' in active_mobile_tabs
    assert 'label: "Timetable"' in active_mobile_tabs
    assert 'label: "Profile"' in active_mobile_tabs
    assert "fixed inset-x-0 bottom-0" in source
    assert "Teacher mobile navigation" in source
    assert source.count('aria-label="Teacher mobile navigation"') == 1
    assert "var(--app-bottom-inset)" in source
    assert 'aria-current={isActive ? "page" : undefined}' in source
    assert "const mobileTabs = isTraining ? teacherMobileTabs : activeTeacherMobileTabs;" in source
    assert 'bottomNavActiveKey(activeTab, cabinetMode)' in source
    assert "function CabinetSidebar" in source
    assert "Teacher cabinet desktop navigation" in source


def test_teacher_cabinet_has_no_admin_preview_mode_source():
    source = _read("roles/teacher/pages/TeacherHome.tsx")

    assert "previewRole" not in source
    assert "devPreviewEnabled" not in source
    assert "ADMIN_PREVIEW_ROLES" not in source
    assert "devPreviewRole" not in source
    assert "msi_admin_mode" not in source
    assert "Student mode" not in source


def test_teacher_mobile_tables_and_cards_are_compact():
    source = _read("roles/teacher/pages/TeacherHome.tsx")

    assert "grid grid-cols-2 gap-2" in source
    assert "miniapp-table-scroll" in source
    assert "pb-[calc(var(--app-bottom-inset)+6.5rem)]" in source
    assert "text-xl font-black" in source


def test_teacher_academy_mobile_home_is_compact_and_profile_is_separate():
    source = _read("roles/teacher/pages/TeacherHome.tsx")
    home_block = source.split('{activeTab === "home"', 1)[1].split('{activeTab === "reports"', 1)[0]
    profile_block = source.split('{activeTab === "profile"', 1)[1].split('{activeTab === "career"', 1)[0]

    assert "NextLessonPreview" in home_block
    assert "LatestUpdatePreview" in home_block
    assert "AcademyProfileSummary" not in home_block
    assert "Roadmap assignments" not in home_block
    assert "AcademyProfileSummary" in profile_block
    assert "AcademyScoreSnapshot" in profile_block
    assert "if (!rows.length) return null;" in source
    assert 'Assessment chart will appear after the first report.' not in source
    assert 'hidden sm:inline-flex' in profile_block
    assert 'activeTab === "career" || (!isTraining && activeTab === "profile")' not in source
    assert '{activeTab === "career" ? (' in source


def test_teacher_cabinet_design_is_applied_to_academy_shell():
    source = _read("roles/teacher/pages/TeacherHome.tsx")

    assert "bg-[#F0F2F6]" in source
    assert "bg-[#12203D]" in source
    assert "text-[#2F5DE0]" in source
    assert "Teacher Cabinet" in source
    assert "AcademyLessonsScreen" in source
    assert "No academy lessons assigned." in source
    assert "No assessment reports yet." in source


def test_active_teacher_charts_include_requested_views():
    source = _read("roles/teacher/components/ActiveTeacherCharts.tsx")

    assert 'title="Attendance trend"' in source
    assert 'title="AAP trend"' in source
    assert 'title="Homework submission"' in source
    assert 'title="Group comparison"' in source


def test_teacher_academy_and_active_tabs_stay_available():
    source = _read("roles/teacher/pages/TeacherHome.tsx")
    academy_tabs = source.split("const academyTabs", 1)[1].split("];", 1)[0]
    active_tabs = source.split("const activeTeacherTabs", 1)[1].split("];", 1)[0]

    assert 'label: "Overview"' in academy_tabs
    assert 'label: "Lessons"' in academy_tabs
    assert 'label: "Timetable"' in academy_tabs
    assert 'label: "Updates"' in academy_tabs
    assert 'label: "Career Growth"' in active_tabs
