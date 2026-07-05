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
    assert '${isTraining ? "hidden sm:flex" : "flex"}' in source


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


def test_teacher_academy_and_active_tabs_stay_available():
    source = _read("roles/teacher/pages/TeacherHome.tsx")
    academy_tabs = source.split("const academyTabs", 1)[1].split("];", 1)[0]
    active_tabs = source.split("const activeTeacherTabs", 1)[1].split("];", 1)[0]

    assert 'label: "Overview"' in academy_tabs
    assert 'label: "Lessons"' in academy_tabs
    assert 'label: "Timetable"' in academy_tabs
    assert 'label: "Updates"' in academy_tabs
    assert 'label: "Career Growth"' in active_tabs
