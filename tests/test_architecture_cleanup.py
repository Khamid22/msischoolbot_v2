"""Cleanup guards for architecture folders, wrappers, and startup imports."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest


ACTIVE_SOURCE_ROOTS = [
    Path("backend"),
    Path("frontend/src"),
]

DELETED_WRAPPER_IMPORTS = [
    "backend.identity.account_service",
    "backend.identity.account_auth_v2",
    "backend.identity.account_telegram_auth_v2",
    "backend.identity.profiles",
    "backend.roles.common.teacher_academy_api",
    "backend.roles.admin.services.teacher_academy_service",
]


def _active_source_text() -> str:
    chunks: list[str] = []
    for root in ACTIVE_SOURCE_ROOTS:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".ts", ".tsx"} and "__pycache__" not in path.parts:
                chunks.append(path.read_text())
    return "\n".join(chunks)


def test_new_real_architecture_folders_remain():
    for path in [
        Path("backend/api/v1"),
        Path("backend/api/v1/admin/router.py"),
        Path("backend/api/v1/academic_director/teacher_academy.py"),
        Path("backend/api/v1/head_of_department/teacher_academy.py"),
        Path("backend/domains/teacher_academy/service.py"),
        Path("backend/domains/teacher_academy/queries.py"),
        Path("backend/core/database.py"),
        Path("backend/core/config.py"),
        Path("backend/security/dependencies.py"),
        Path("frontend/src/shared/api/routes.ts"),
    ]:
        assert path.exists(), f"Expected clean architecture path to exist: {path}"


def test_empty_unused_placeholder_folders_are_removed():
    for path in [
        Path("backend/api/v1/workspaces"),
        Path("backend/domains/people"),
    ]:
        assert not path.exists(), f"Unused empty placeholder should be removed: {path}"


def test_deleted_wrappers_are_not_importable_and_not_referenced_by_active_code():
    active_source = _active_source_text()
    for module_name in DELETED_WRAPPER_IMPORTS:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
        assert module_name not in active_source


def test_kept_temporary_wrappers_are_documented():
    for path in [
        Path("backend/identity/parent_accounts.py"),
        Path("backend/identity/parent_invites.py"),
        Path("backend/roles/admin/services/parent_service.py"),
        Path("backend/roles/parent/services.py"),
        Path("config.py"),
        Path("database/queries/__init__.py"),
        Path("database/cross_queries/__init__.py"),
        Path("database/queries/teacher_queries.py"),
        Path("database/cross_queries/student_queries.py"),
        Path("database/queries/parent_account_queries.py"),
        Path("database/queries/parent_queries.py"),
        Path("database/queries/payment_queries.py"),
    ]:
        source = path.read_text()
        assert "Temporary compatibility wrapper. Delete after" in source


def test_database_folder_inventory_exists_and_lists_remaining_files():
    inventory = Path("docs/DATABASE_FOLDER_MIGRATION_STATUS.md")
    source = inventory.read_text()

    assert inventory.exists()
    assert "database/alembic/" in source
    assert "database/queries/announcement_queries.py" in source
    assert "Deleted `database/queries/announcement_queries.py`" in source
    for path in Path("database").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            assert str(path) in source, f"{path} missing from database migration inventory"


def test_database_generated_caches_are_deleted_and_alembic_remains():
    assert Path("database/alembic/env.py").exists()
    assert list(Path("database/alembic/versions").glob("*.py"))
    tracked_database_files = subprocess.check_output(
        ["git", "ls-files", "database"],
        text=True,
    ).splitlines()
    assert not [path for path in tracked_database_files if "__pycache__" in path or path.endswith(".pyc")]


def test_announcement_database_query_wrapper_is_removed_after_domain_migration():
    active_source = _active_source_text()

    assert Path("backend/domains/announcements/queries.py").exists()
    assert not Path("database/queries/announcement_queries.py").exists()
    assert "from .announcement_queries import *" not in Path("database/queries/__init__.py").read_text()
    assert "database.queries.announcement_queries" not in active_source


def test_complaint_office_hours_and_resource_query_wrappers_moved_to_domains():
    active_source = _active_source_text()
    query_barrel = Path("database/queries/__init__.py").read_text()

    for path in [
        Path("backend/domains/complaints/queries.py"),
        Path("backend/domains/office_hours/queries.py"),
        Path("backend/domains/resources/queries.py"),
    ]:
        assert path.exists(), f"Expected domain query module to exist: {path}"

    legacy_query_dir = Path("database") / "queries"
    for path in [
        legacy_query_dir / "complaint_queries.py",
        legacy_query_dir / "office_hours.py",
        legacy_query_dir / "resource_queries.py",
    ]:
        assert not path.exists(), f"Old query wrapper should be removed: {path}"

    legacy_module_imports = [
        "from .complaint_queries import *",
        "from .office_hours import *",
        "from .resource_queries import *",
        "database.queries." + "complaint_queries",
        "database.queries." + "office_hours",
        "database.queries." + "resource_queries",
    ]
    for legacy_import in legacy_module_imports:
        assert legacy_import not in query_barrel
        assert legacy_import not in active_source


def test_academic_helpers_moved_out_of_database_folder():
    active_source = _active_source_text()
    bot_source = "\n".join(path.read_text() for path in Path("tgbot").rglob("*.py"))
    old_academic_import = "database." + "academics"

    for path in [
        Path("backend/domains/academics/canonical.py"),
        Path("backend/domains/academics/curriculum.py"),
        Path("backend/domains/academics/dates.py"),
        Path("backend/domains/academics/performance_summary.py"),
        Path("backend/domains/academics/schools.py"),
        Path("backend/domains/academics/subjects.py"),
        Path("backend/domains/academics/summary_queries.py"),
        Path("backend/domains/academics/text.py"),
    ]:
        assert path.exists(), f"Expected moved academic helper to exist: {path}"

    assert not (Path("database") / "academics").exists()
    assert not (Path("database") / "queries" / ("subject_" + "summary_queries.py")).exists()
    assert old_academic_import not in active_source
    assert old_academic_import not in bot_source


def test_complaint_office_hours_and_resource_services_use_domain_queries():
    expected_sources = {
        Path("backend/domains/complaints/service.py"): "from backend.domains.complaints import queries",
        Path("backend/domains/office_hours/service.py"): "from backend.domains.office_hours import queries",
        Path("backend/domains/resources/service.py"): "from backend.domains.resources import queries",
        Path("backend/domains/resources/comments_service.py"): "from backend.domains.resources import queries",
    }

    for path, expected_import in expected_sources.items():
        source = path.read_text()
        assert expected_import in source
        assert "from database import queries" not in source


def test_main_startup_imports_storage_not_account_service():
    main_source = Path("main.py").read_text()

    assert "from backend.identity.storage import init_storage" in main_source
    assert "from backend.core.config import get_web_settings" in main_source
    assert "backend.identity.account_service" not in main_source
    assert callable(importlib.import_module("backend.identity.storage").init_storage)
    importlib.import_module("main")
