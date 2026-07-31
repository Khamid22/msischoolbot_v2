"""Architecture guards for the modular LMS portal."""

import ast
from pathlib import Path

WORKSPACE_NAMES = {
    "ceo",
    "academic_director",
    "head_of_department",
    "customer_support",
    "student",
    "parent",
    "teacher",
    "hr_manager",
}
API_WORKSPACE_NAMES = {
    "ceo",
    "academic_director",
    "head_of_department",
    "customer_support",
    "student",
    "parent",
    "teacher",
}
FRONTEND_WORKSPACE_NAMES = WORKSPACE_NAMES - {"hr_manager"}

LEGACY_BACKEND_LAYERS = {"api", "pages", "services", "repositories", "schemas"}


def _python_sources(root: str):
    return [path for path in Path(root).rglob("*.py") if "__pycache__" not in path.parts]


def _workspace_sources():
    people_root = Path("backend/modules/people")
    return [
        path
        for workspace_root in people_root.glob("*/workspace")
        for path in workspace_root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def _syntax_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())


def _called_attribute_names(path: Path) -> set[str]:
    return {
        node.func.attr
        for node in ast.walk(_syntax_tree(path))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def _imported_module_names(path: Path) -> set[str]:
    imported_modules: set[str] = set()
    for node in ast.walk(_syntax_tree(path)):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
    return imported_modules


def test_application_composes_every_api_workspace_router():
    source = Path("backend/application/api.py").read_text()

    assert 'APIRouter(prefix="/api/v1")' in source
    for workspace in API_WORKSPACE_NAMES:
        import_path = f"backend.modules.people.{workspace}.workspace.api"
        assert import_path in source


def test_application_registry_composes_workspace_pages():
    source = Path("backend/application/registry.py").read_text()

    for workspace in WORKSPACE_NAMES:
        assert f"backend.modules.people.{workspace}.workspace.page" in source


def test_legacy_technical_layers_are_removed():
    for name in LEGACY_BACKEND_LAYERS:
        assert not Path("backend", name).exists()
    assert Path("backend/application").is_dir()
    assert Path("backend/modules").is_dir()
    assert not Path("backend/workspaces").exists()
    assert not Path("backend/internal_operations").exists()


def test_workspace_inventory_uses_exact_product_names():
    actual = {
        path.parent.name
        for path in Path("backend/modules/people").glob("*/workspace")
        if path.is_dir()
    }
    assert actual == WORKSPACE_NAMES


def test_workspace_and_application_adapters_do_not_own_sql_or_repositories():
    adapter_paths = _workspace_sources()
    adapter_paths.extend(Path("backend/modules").rglob("*api.py"))
    for path in adapter_paths:
        called_attributes = _called_attribute_names(path)
        assert "execute" not in called_attributes, f"SQL must stay in a module repository: {path}"
        assert "commit" not in called_attributes, (
            f"Transaction ownership must stay in commands: {path}"
        )


def test_modules_do_not_import_another_modules_repository():
    for path in _python_sources("backend/modules"):
        owning_module = path.relative_to("backend/modules").parts[0]
        for imported_module in _imported_module_names(path):
            imported_parts = imported_module.split(".")
            if (
                imported_parts[:2] != ["backend", "modules"]
                or "repository" not in imported_parts
                or len(imported_parts) < 3
            ):
                continue
            assert imported_parts[2] == owning_module, (
                f"Cross-module repository import: {path}: {imported_module}"
            )


def test_http_api_adapters_do_not_render_pages():
    api_paths = [
        path
        for path in _python_sources("backend/modules")
        if path.name.endswith("api.py")
    ]
    assert api_paths
    for path in api_paths:
        source = path.read_text()
        assert "render_react_page" not in source
        assert "HTMLResponse" not in source


def test_teacher_workspace_is_a_read_only_role_adapter():
    assert Path("backend/modules/people/teacher/workspace/page.py").exists()
    assert Path("frontend/src/workspaces/teacher/pages/Home.tsx").exists()
    assert not Path("frontend/src/roles").exists()
    source = Path("backend/modules/people/teacher/workspace/page.py").read_text()
    assert "get_academy_teacher_for_teacher_account" in source
    assert "@router.post" not in source


def test_teacher_academy_actions_remain_owned_by_authorized_workspaces():
    director_api = Path("backend/modules/people/academic_director/workspace/staff_records_api.py").read_text()
    department_api = Path("backend/modules/people/head_of_department/workspace/staff_records_api.py").read_text()
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


def test_frontend_uses_workspace_feature_and_shared_boundaries():
    source_root = Path("frontend/src")
    assert not (source_root / "roles").exists()
    for folder in ("app", "workspaces", "features", "shared"):
        assert (source_root / folder).is_dir()
    assert not (source_root / "internal_operations").exists()
    actual_workspaces = {
        path.name for path in (source_root / "workspaces").iterdir() if path.is_dir()
    }
    assert actual_workspaces == FRONTEND_WORKSPACE_NAMES | {
        "academic_shared",
        "public_admission",
        "shared",
    }


def test_frontend_teacher_academy_uses_api_v1_contracts():
    source = Path("frontend/src/shared/api/routes.ts").read_text()
    assert "/api/v1/academic-director/teacher-academy" in source
    assert "/api/v1/head-of-department/teacher-academy" in source
    assert "/admin/teacher-academy" not in source
