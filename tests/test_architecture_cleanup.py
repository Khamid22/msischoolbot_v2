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
    "backend.identity.account_auth",
    "backend.identity.account_telegram_auth",
    "backend.identity.parent_accounts",
    "backend.identity.telegram_links",
    "backend.identity.profiles",
    "backend.roles.parent.services",
    "backend.modules.identity.service",
    "backend.roles.common.teacher_academy_api",
    "backend.roles.admin.services.teacher_academy_service",
    "database.cross_queries",
    "database.cross_queries.bot_user_queries",
    "database.cross_queries.student_queries",
    "database.queries",
    "database.queries.admin_queries",
    "database.queries.meta_queries",
    "database.queries.parent_account_queries",
    "database.queries.parent_queries",
    "database.queries.payment_queries",
    "database.queries.teacher_queries",
    "database.tables",
    "tgbot.helpers",
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
        Path("backend/modules/router.py"),
        Path("backend/modules/admin/api.py"),
        Path("backend/modules/teacher_academy/director_api.py"),
        Path("backend/modules/teacher_academy/hod_api.py"),
        Path("backend/modules/teacher_academy/service.py"),
        Path("backend/modules/teacher_academy/repository.py"),
        Path("backend/core/database.py"),
        Path("backend/core/config.py"),
        Path("backend/core/access/dependencies.py"),
        Path("frontend/src/shared/api/routes.ts"),
    ]:
        assert path.exists(), f"Expected clean architecture path to exist: {path}"


def test_empty_unused_placeholder_folders_are_removed():
    for path in [
        Path("backend/api"),
        Path("backend/pages"),
        Path("backend/roles"),
        Path("backend/domains"),
        Path("backend/modules/people"),
    ]:
        assert not path.exists(), f"Unused empty placeholder should be removed: {path}"


def test_deleted_wrappers_are_not_importable_and_not_referenced_by_active_code():
    active_source = _active_source_text()
    for module_name in DELETED_WRAPPER_IMPORTS:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
        assert module_name not in active_source


def test_only_still_used_temporary_wrappers_are_documented():
    source = Path("config.py").read_text()
    assert "Temporary compatibility wrapper. Delete after" in source
    assert not Path("backend/roles/admin/services/parent_service.py").exists()


def test_database_folder_inventory_exists_and_lists_remaining_files():
    inventory = Path("docs/DATABASE_FOLDER_MIGRATION_STATUS.md")
    source = inventory.read_text()

    assert inventory.exists()
    assert "database/alembic/" in source

    runtime_entries = {
        path.name
        for path in Path("database").iterdir()
        if path.name != "__pycache__"
    }
    assert runtime_entries == {"__init__.py", "alembic"}


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

    assert Path("backend/modules/announcements/repository.py").exists()
    assert not Path("database/queries").exists()
    assert "database.queries.announcement_queries" not in active_source


def test_complaint_office_hours_and_resource_query_wrappers_moved_to_domains():
    active_source = _active_source_text()

    for path in [
        Path("backend/modules/complaints/repository.py"),
        Path("backend/modules/office_hours/repository.py"),
        Path("backend/modules/resources/repository.py"),
    ]:
        assert path.exists(), f"Expected domain query module to exist: {path}"

    assert not (Path("database") / "queries").exists()

    legacy_module_imports = [
        "from .complaint_queries import *",
        "from .office_hours import *",
        "from .resource_queries import *",
        "database.queries." + "complaint_queries",
        "database.queries." + "office_hours",
        "database.queries." + "resource_queries",
    ]
    for legacy_import in legacy_module_imports:
        assert legacy_import not in active_source


def test_academic_helpers_moved_out_of_database_folder():
    active_source = _active_source_text()
    bot_source = "\n".join(path.read_text() for path in Path("tgbot").rglob("*.py"))
    old_academic_import = "database." + "academics"

    for path in [
        Path("backend/modules/academics/canonical.py"),
        Path("backend/modules/academics/dates.py"),
        Path("backend/modules/academics/performance_summary.py"),
        Path("backend/modules/academics/schools.py"),
        Path("backend/modules/academics/subjects.py"),
        Path("backend/modules/academics/summary_repository.py"),
        Path("backend/modules/academics/text.py"),
    ]:
        assert path.exists(), f"Expected moved academic helper to exist: {path}"

    assert not Path("backend/modules/academics/curriculum.py").exists()
    assert not Path("backend/integrations/excel").exists()

    assert not (Path("database") / "academics").exists()
    assert not (Path("database") / "queries" / ("subject_" + "summary_queries.py")).exists()
    assert old_academic_import not in active_source
    assert old_academic_import not in bot_source


def test_excel_is_not_an_lms_integration_or_upload_format():
    assert not Path("backend/integrations/excel").exists()
    assert not Path("backend/modules/academics/curriculum.py").exists()
    assert not Path("scripts/reconcile_academic_workbooks.py").exists()
    assert "openpyxl" not in Path("requirements.txt").read_text().casefold()

    upload_source = Path(
        "backend/integrations/storage/r2.py"
    ).read_text().casefold()
    assert '".xls"' not in upload_source
    assert '".xlsx"' not in upload_source


def test_complaint_office_hours_and_resource_services_use_module_repositories():
    expected_sources = {
        Path("backend/modules/complaints/service.py"): "from backend.modules.complaints import repository",
        Path("backend/modules/office_hours/service.py"): "from backend.modules.office_hours import repository",
        Path("backend/modules/resources/service.py"): "from backend.modules.resources import repository",
        Path("backend/modules/resources/comments_service.py"): "from backend.modules.resources import repository",
    }

    for path, expected_import in expected_sources.items():
        source = path.read_text()
        assert expected_import in source
        assert "from database import queries" not in source


def test_main_startup_imports_storage_not_account_service():
    main_source = Path("main.py").read_text()

    assert "from backend.modules.identity.bootstrap import init_storage" in main_source
    assert "from backend.core.config import get_web_settings" in main_source
    assert "backend.identity.account_service" not in main_source
    assert callable(importlib.import_module("backend.modules.identity.bootstrap").init_storage)
    importlib.import_module("main")
