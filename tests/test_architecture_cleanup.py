"""Cleanup guards for architecture folders, wrappers, and startup imports."""

from __future__ import annotations

import importlib
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
        Path("database/queries/__init__.py"),
        Path("database/cross_queries/__init__.py"),
        Path("database/queries/teacher_queries.py"),
        Path("database/cross_queries/student_queries.py"),
        Path("database/queries/parent_account_queries.py"),
        Path("database/queries/parent_queries.py"),
        Path("database/queries/announcement_queries.py"),
    ]:
        source = path.read_text()
        assert "Temporary compatibility wrapper. Delete after" in source


def test_main_startup_imports_storage_not_account_service():
    main_source = Path("main.py").read_text()

    assert "from backend.identity.storage import init_storage" in main_source
    assert "backend.identity.account_service" not in main_source
    assert callable(importlib.import_module("backend.identity.storage").init_storage)
    importlib.import_module("main")
