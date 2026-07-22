"""Responsive contracts for staff-record management in authorized workspaces."""

from pathlib import Path


ROOT = Path("frontend/src")


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_academy_uses_shared_accessible_modal_and_action_menu():
    source = "\n".join([
        _read("features/teacher-academy/TeacherAcademyPanel.tsx"),
        _read("features/teacher-academy/TeacherAcademyWorkflowModals.tsx"),
    ])
    assert 'from "@/shared/ui/ActionMenu"' in source
    assert 'from "@/shared/ui/Modal"' in source
    assert "ActionMenu" in source
    assert "Modal" in source


def test_teacher_academy_uses_compact_cards_at_every_roster_breakpoint():
    panel = _read("features/teacher-academy/TeacherAcademyPanel.tsx")
    cards = _read("features/teacher-academy/TeacherAcademyCards.tsx")
    assert "TeacherCardGrid" in cards
    assert "grid-cols-1" in cards
    assert "md:grid-cols-2" in cards
    assert "xl:grid-cols-3" in cards
    assert "min-h-[15rem]" in cards
    assert "TeacherAcademyRoster" in panel
    assert "ScopedTeacherAcademyRoster" in panel
    assert "AppointedLessonsView" not in panel
    assert not (ROOT / "features/teacher-academy/AppointedLessonsView.tsx").exists()


def test_head_of_departments_workspace_uses_exact_folder_and_shared_shell():
    source = _read("workspaces/head_of_departments/pages/TeacherAcademy.tsx")
    assert "HeadOfDepartmentPageShell" in source
    assert "allowTeacherPreview" not in source
    assert not (ROOT / "workspaces/head_of_department").exists()


def test_academic_director_workspace_has_no_teacher_portal_preview():
    source = _read("workspaces/academic_director/pages/TeacherAcademy.tsx")
    assert "AcademicDirectorPageShell" in source
    assert "allowTeacherPreview" not in source


def test_obsolete_admin_role_previews_are_deleted():
    academy = _read("features/teacher-academy/TeacherAcademyPanel.tsx")
    workspace = _read("shared/lib/workspace.ts")
    assert "Preview as Teacher" not in academy
    assert not (ROOT / "internal_operations").exists()
    assert "devPreviewEnabled" not in workspace
    assert not (ROOT / "features/reporting/overview/RoleOverviewPanel.tsx").exists()
    assert not (ROOT / "shared/lib/staleUiState.ts").exists()


def test_shared_responsive_components_remain_available():
    for path in [
        "shared/ui/MobileCardList.tsx",
        "shared/ui/ResponsiveTable.tsx",
        "shared/ui/RoleMobileNav.tsx",
        "shared/ui/RoleSidebar.tsx",
    ]:
        assert (ROOT / path).exists()


def test_teacher_portal_navigation_and_page_are_domain_owned():
    source = _read("app/App.tsx")
    assert "teacher-home" in source
    assert not (ROOT / "roles").exists()
    assert (ROOT / "workspaces/teacher/pages/Home.tsx").exists()
