"""DB-1 database access architecture coverage."""

from pathlib import Path


def test_core_database_clean_import_path_exports_connection_helpers():
    import backend.core.database as core_database

    assert callable(core_database.connect_db)
    assert callable(core_database.connect)
    assert callable(core_database.connect_auth_db)
    assert callable(core_database.get_db_backend)
    assert callable(core_database.get_db_backend_for_connection)
    assert callable(core_database.close_idle_pool_connections)


def test_legacy_database_module_is_removed_after_core_migration():
    core_source = Path("backend/core/database.py").read_text()
    database_package_source = Path("database/__init__.py").read_text()
    alembic_source = Path("database/alembic/env.py").read_text()
    removed_database_module = Path("database") / "database.py"
    legacy_database_import = "from database." + "database import"

    assert not removed_database_module.exists()
    assert legacy_database_import not in core_source
    assert "from backend.core.database import connect_auth_db, get_db_backend" in database_package_source
    assert "from backend.core.database import _database_url" in alembic_source


def test_teacher_academy_domain_modules_import_successfully():
    import backend.repositories.teacher_academy as academy_repository
    import backend.services.teacher_academy.core as academy_service

    assert callable(academy_repository.list_academy_teacher_rows)
    assert callable(academy_repository.insert_academy_lesson_assignment)
    assert callable(academy_repository.insert_assessment)
    assert callable(academy_service.list_academy_teachers)
    assert academy_service.repository is academy_repository


def test_old_admin_teacher_academy_service_path_is_removed():
    page_service_source = Path("backend/services/admin/workspace.py").read_text()

    assert not Path("backend/roles/admin/services/teacher_academy_service.py").exists()
    assert "from backend.services.teacher_academy.core import list_academy_teachers" in page_service_source
    assert "teacher_academy_service" not in page_service_source


def test_teacher_academy_service_uses_module_repository_not_inline_sql():
    service_source = Path("backend/services/teacher_academy/core.py").read_text()

    assert "from backend.repositories import teacher_academy as repository" in service_source
    assert "from database import queries" not in service_source
    assert "conn.execute" not in service_source
    assert "FROM msi_v2" not in service_source
    assert "INSERT INTO msi_v2" not in service_source
    assert "UPDATE msi_v2" not in service_source


def test_page_and_role_edges_import_teacher_academy_domain_service_where_safe():
    role_sources = [
        Path("backend/pages/academics/director.py").read_text(),
        Path("backend/pages/academics/hod.py").read_text(),
        Path("backend/services/academics/hod_cards.py").read_text(),
        Path("backend/services/teachers/workspace.py").read_text(),
        Path("backend/services/admin/workspace.py").read_text(),
    ]

    for source in role_sources:
        assert "backend.services.teacher_academy.core" in source
        assert "backend.roles.admin.services.teacher_academy_service" not in source
