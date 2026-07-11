"""Cleanup guards for obsolete layers, wrappers, and spreadsheet integration."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest


LEGACY_IMPORT_ROOTS = [
    "backend.api",
    "backend.pages",
    "backend.services",
    "backend.repositories",
    "backend.schemas",
    "backend.identity",
    "backend.roles",
    "database.queries",
]


def _active_source_text() -> str:
    chunks = []
    for root in (Path("backend"), Path("frontend/src"), Path("tgbot")):
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".ts", ".tsx"} and "__pycache__" not in path.parts:
                chunks.append(path.read_text())
    return "\n".join(chunks)


def test_required_modular_architecture_paths_exist():
    for path in [
        Path("backend/application/api.py"),
        Path("backend/application/registry.py"),
        Path("backend/internal_operations/page.py"),
        Path("backend/modules/accounts/service.py"),
        Path("backend/modules/academics/service.py"),
        Path("backend/modules/staff_records/development_service.py"),
        Path("backend/modules/student_records/service.py"),
        Path("frontend/src/shared/api/routes.ts"),
    ]:
        assert path.exists(), f"Expected modular architecture path: {path}"


def test_legacy_backend_import_roots_are_deleted_and_unreferenced():
    active_source = _active_source_text()
    for module_name in LEGACY_IMPORT_ROOTS:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)
        assert f"{module_name}." not in active_source


def test_database_folder_contains_only_alembic_runtime():
    runtime_entries = {
        path.name
        for path in Path("database").iterdir()
        if path.name != "__pycache__"
    }
    assert runtime_entries == {"__init__.py", "alembic"}
    assert Path("database/alembic/versions/0008_remove_teacher_portal_access.py").exists()


def test_generated_database_caches_are_not_tracked():
    tracked = subprocess.check_output(["git", "ls-files", "database"], text=True).splitlines()
    assert not [path for path in tracked if "__pycache__" in path or path.endswith(".pyc")]


def test_module_repositories_are_canonical():
    expected = [
        Path("backend/modules/communications/announcements_repository.py"),
        Path("backend/modules/complaints/repository.py"),
        Path("backend/modules/academics/office_hours_repository.py"),
        Path("backend/modules/learning_resources/repository.py"),
        Path("backend/modules/parent_access/repository.py"),
        Path("backend/modules/payments/repository.py"),
        Path("backend/modules/reporting/repository.py"),
    ]
    assert all(path.exists() for path in expected)


def test_excel_is_not_an_lms_integration_or_upload_format():
    source = _active_source_text().casefold()
    assert not Path("backend/integrations/excel").exists()
    assert not Path("scripts/reconcile_academic_workbooks.py").exists()
    assert "openpyxl" not in Path("requirements.txt").read_text().casefold()
    assert '".xls"' not in source
    assert '".xlsx"' not in source
    assert "google sheets" not in source


def test_main_starts_from_modular_accounts_and_core_config():
    main_source = Path("main.py").read_text()
    assert "from backend.modules.accounts.bootstrap import init_storage" in main_source
    assert "from backend.core.config import get_web_settings" in main_source
    assert callable(importlib.import_module("backend.modules.accounts.bootstrap").init_storage)


def test_demo_authentication_bypass_is_removed():
    assert not Path("backend/core/demo_auth.py").exists()
    server_source = Path("backend/server.py").read_text()
    assert "DEMO_AUTH_ENABLED" not in server_source
    assert "maybe_apply_demo_auth" not in server_source
