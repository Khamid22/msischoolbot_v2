"""Architecture guards for the modular LMS portal."""

from pathlib import Path


WORKSPACE_NAMES = {
    "ceo",
    "academic_director",
    "head_of_departments",
    "customer_support",
    "hr_manager",
    "student",
    "parent",
    "teacher",
}
API_WORKSPACE_NAMES = WORKSPACE_NAMES - {"teacher"}

LEGACY_BACKEND_LAYERS = {"api", "pages", "services", "repositories", "schemas"}


def _python_sources(root: str):
    return [path for path in Path(root).rglob("*.py") if "__pycache__" not in path.parts]


def test_application_composes_exactly_seven_workspace_routers():
    source = Path("backend/application/api.py").read_text()

    assert 'APIRouter(prefix="/api/v1")' in source
    assert "teacher_router" not in source
    for workspace in API_WORKSPACE_NAMES:
        import_path = f"backend.workspaces.{workspace}.api"
        assert import_path in source


def test_application_registry_composes_workspace_pages():
    source = Path("backend/application/registry.py").read_text()

    for workspace in WORKSPACE_NAMES:
        assert f"backend.workspaces.{workspace}.page" in source


def test_legacy_technical_layers_are_removed():
    for name in LEGACY_BACKEND_LAYERS:
        assert not Path("backend", name).exists()
    assert Path("backend/application").is_dir()
    assert Path("backend/workspaces").is_dir()
    assert Path("backend/modules").is_dir()
    assert Path("backend/internal_operations").is_dir()


def test_workspace_inventory_uses_exact_product_names():
    actual = {
        path.name
        for path in Path("backend/workspaces").iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }
    assert actual == WORKSPACE_NAMES


def test_workspaces_and_internal_operations_do_not_own_sql_or_repositories():
    for root in ("backend/workspaces", "backend/internal_operations", "backend/application"):
        for path in _python_sources(root):
            source = path.read_text()
            assert ".execute(" not in source, f"SQL must stay in a module repository: {path}"
            assert "FROM msi_v2" not in source, f"SQL must stay in a module repository: {path}"
            assert "import repository" not in source, f"Adapters must call module services: {path}"


def test_modules_do_not_import_another_modules_repository():
    for path in _python_sources("backend/modules"):
        source = path.read_text()
        owning_module = path.relative_to("backend/modules").parts[0]
        for line in source.splitlines():
            if not line.startswith("from backend.modules.") or "repository" not in line:
                continue
            imported_module = line.removeprefix("from backend.modules.").split(".", 1)[0].split()[0]
            assert imported_module == owning_module, f"Cross-module repository import: {path}: {line}"


def test_http_api_adapters_do_not_render_pages():
    api_paths = [
        path
        for root in ("backend/workspaces", "backend/modules", "backend/internal_operations")
        for path in _python_sources(root)
        if path.name.endswith("api.py")
    ]
    assert api_paths
    for path in api_paths:
        source = path.read_text()
        assert "render_react_page" not in source
        assert "HTMLResponse" not in source


def test_teacher_workspace_is_a_read_only_role_adapter():
    assert Path("backend/workspaces/teacher/page.py").exists()
    assert Path("frontend/src/workspaces/teacher/pages/Home.tsx").exists()
    assert not Path("frontend/src/roles").exists()
    source = Path("backend/workspaces/teacher/page.py").read_text()
    assert "get_academy_teacher_for_teacher_account" in source
    assert "@router.post" not in source


def test_teacher_academy_actions_remain_owned_by_authorized_workspaces():
    director_api = Path("backend/workspaces/academic_director/staff_records_api.py").read_text()
    department_api = Path("backend/workspaces/head_of_departments/staff_records_api.py").read_text()
    for source in (director_api, department_api):
        assert "register_teacher_academy_routes" in source
        assert "CurrentUser" in source
    assert "can_user_manage_academy_teacher" in department_api


def test_server_registers_api_before_page_adapters():
    source = Path("backend/server.py").read_text()
    assert "from backend.application.api import router as api_v1_router" in source
    assert "from backend.application.registry import register_application_pages" in source
    assert source.index("app_instance.include_router(api_v1_router)") < source.index(
        "register_application_pages(app_instance)"
    )


def test_frontend_uses_workspace_feature_shared_and_internal_boundaries():
    source_root = Path("frontend/src")
    assert not (source_root / "roles").exists()
    for folder in ("app", "workspaces", "features", "shared", "internal_operations"):
        assert (source_root / folder).is_dir()
    actual_workspaces = {
        path.name
        for path in (source_root / "workspaces").iterdir()
        if path.is_dir()
    }
    assert actual_workspaces == WORKSPACE_NAMES | {"academic_shared", "shared"}


def test_frontend_teacher_academy_uses_api_v1_contracts():
    source = Path("frontend/src/shared/api/routes.ts").read_text()
    assert "/api/v1/academic-director/teacher-academy" in source
    assert "/api/v1/head-of-department/teacher-academy" in source
    assert "/admin/teacher-academy" not in source
