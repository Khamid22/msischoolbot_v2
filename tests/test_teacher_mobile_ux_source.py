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


def test_action_menu_and_academy_modal_use_dismissible_layer():
    action_menu = _read("shared/ui/ActionMenu.tsx")
    academy_panel = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")

    assert "useDismissibleLayer" in action_menu
    assert "dismissibleRefs" in action_menu
    assert "useDismissibleLayer" in academy_panel
    assert 'role="dialog"' in academy_panel
    assert 'aria-modal="true"' in academy_panel
    assert "aria-label={title}" in academy_panel


def test_teacher_academy_admin_list_has_mobile_cards_and_desktop_table():
    source = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")

    assert "function AcademyTeacherCard" in source
    assert "lg:hidden" in source
    assert "hidden max-h-[calc(100dvh-20rem)] overflow-auto lg:block" in source
    assert "No academy lessons assigned." in source
    assert "TeacherAcademyPanel" in source
    assert 'const canCreateAcademyTeacher = adminMode !== "head_of_department" && authRole !== "head_of_department";' in source
    assert "Academy status distribution" in source
    assert "Average score by subject" in source
    assert "Completion rate by subject" in source
    assert "Recent assessment trend" in source


def test_teacher_academy_actions_use_schedule_not_assign():
    source = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")

    assert "Schedule Training Lesson" in source
    assert "Save Schedule" in source
    assert "Schedule" in source
    assert "\n                                  Assign\n" not in source
    assert "setScheduleTarget({ teacher, assignment: nextAssignment })" in source


def test_teacher_academy_modals_select_assignment_ids():
    source = _read("roles/admin/panels/teachers/TeacherAcademyPanel.tsx")

    assert 'name="assignment_id"' in source
    assert "onSubmit(asNumber(selectedAssignment?.id), fields)" in source
    assert 'name="lesson_assignment_id"' in source
    assert "fields.lesson_assignment_id = String(asNumber(selectedAssignment?.id));" in source
    assert "Select lesson assignment" in source
    assert 'name="class_label"' in source
    assert 'name="decision"' in source
    assert 'name="strengths"' in source
    assert 'name="areas_for_improvement"' in source
    assert 'name="final_recommendation"' in source
    assert "Save assessment" in source


def test_teacher_mobile_bottom_nav_contract():
    source = _read("roles/teacher/pages/TeacherHome.tsx")
    mobile_tabs = source.split("const teacherMobileTabs", 1)[1].split("];", 1)[0]

    assert 'label: "Home"' in mobile_tabs
    assert 'label: "Lessons"' in mobile_tabs
    assert 'label: "Updates"' in mobile_tabs
    assert 'label: "Profile"' in mobile_tabs
    assert "fixed inset-x-0 bottom-0" in source
    assert "Teacher mobile navigation" in source
    assert "var(--app-bottom-inset)" in source
    assert 'aria-current={isActive ? "page" : undefined}' in source
    assert "const mobileTabs = isTraining ? teacherMobileTabs : activeTeacherMobileTabs;" in source
    assert 'bottomNavActiveKey(activeTab, cabinetMode)' in source
    assert "function CabinetSidebar" in source
    assert "Teacher cabinet desktop navigation" in source


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
    assert 'Assessment chart will appear after the first report.' in source
    assert 'hidden sm:inline-flex' in profile_block
    assert 'activeTab === "career" || (!isTraining && activeTab === "profile")' in source


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
