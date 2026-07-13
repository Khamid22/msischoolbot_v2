"""Regression coverage for the granular academic read path and safe mutations."""

from __future__ import annotations

from pathlib import Path

import pytest


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_group_page_is_bounded_and_uses_an_opaque_cursor(monkeypatch):
    from backend.modules.academics import read_service

    captured = {}

    def rows(_conn, **kwargs):
        captured.update(kwargs)
        return [
            {"id": 1, "name": "AFT1", "filtered_total": 3},
            {"id": 2, "name": "AFT2", "filtered_total": 3},
        ]

    monkeypatch.setattr(read_service, "connect_auth_db", lambda: _Connection())
    monkeypatch.setattr(read_service.repository, "list_group_rows_page", rows)

    page = read_service.list_group_page(cursor="o0", limit=2)

    assert page == {
        "items": [{"id": 1, "name": "AFT1"}, {"id": 2, "name": "AFT2"}],
        "next_cursor": "o2",
        "total": 3,
    }
    assert captured["limit"] == 2
    assert captured["offset"] == 0


def test_group_page_caps_requested_size(monkeypatch):
    from backend.modules.academics import read_service

    captured = {}

    def rows(_conn, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(read_service, "connect_auth_db", lambda: _Connection())
    monkeypatch.setattr(read_service.repository, "list_group_rows_page", rows)

    read_service.list_group_page(limit=10_000)

    assert captured["limit"] == 100


def test_timetable_range_rejects_unbounded_reads_before_database_access(monkeypatch):
    from backend.modules.academics import read_service

    monkeypatch.setattr(
        read_service,
        "connect_auth_db",
        lambda: pytest.fail("database should not be opened for an invalid range"),
    )

    with pytest.raises(ValueError, match="cannot exceed 63 days"):
        read_service.list_timetable_range(
            start_date="2026-01-01", end_date="2026-04-01"
        )


def test_light_academic_context_omits_group_collection(monkeypatch):
    from backend.modules.academics import service

    monkeypatch.setattr(service, "_connect", lambda: _Connection())
    monkeypatch.setattr(service.academic_repository, "list_school_rows", lambda _conn: [])
    monkeypatch.setattr(service.academic_repository, "list_class_rows", lambda _conn: [])
    monkeypatch.setattr(service.academic_repository, "list_subject_rows", lambda _conn: [])
    monkeypatch.setattr(
        service.academic_repository,
        "list_group_rows",
        lambda _conn: pytest.fail("groups must use the paginated endpoint"),
    )
    monkeypatch.setattr(
        service.academic_repository,
        "get_enrollment_summary_row",
        lambda _conn: {},
    )

    context = service.list_academic_admin_rows(
        include_heavy=False, include_groups=False
    )

    assert context["groups"] == []
    assert context["lessons"] == []
    assert context["sessions"] == []


def test_group_archive_preserves_dependencies_and_writes_audit(monkeypatch):
    from backend.modules.academics import operations

    connection = _Connection()
    connection.committed = False
    connection.commit = lambda: setattr(connection, "committed", True)
    monkeypatch.setattr(operations, "connect_auth_db", lambda: connection)
    monkeypatch.setattr(
        operations.academic_repository,
        "get_group_archive_candidate",
        lambda _conn, _id: {
            "id": 17,
            "public_id": 701,
            "group_name": "AFT1",
            "group_code": "",
            "status": "active",
            "school_key": "school5",
            "subject_name": "IGCSE Mathematics A",
        },
    )
    preserved = {
        "enrollments": 6,
        "schedules": 2,
        "lessons": 172,
        "attendance": 500,
        "homework": 400,
        "exams": 48,
    }
    monkeypatch.setattr(
        operations.academic_repository,
        "count_group_dependencies",
        lambda _conn, _id: preserved,
    )
    monkeypatch.setattr(
        operations.academic_repository,
        "archive_group",
        lambda _conn, _id: {"id": 17},
    )
    audit = {}
    monkeypatch.setattr(
        operations.academic_repository,
        "insert_audit_event",
        lambda _conn, **kwargs: audit.update(kwargs),
    )

    archived = operations.archive_group(
        701, actor_staff_id=8, actor_account_id=9
    )

    assert archived["status"] == "archived"
    assert archived["preserved"] == preserved
    assert audit["event_type"] == "academic.group_archived"
    assert audit["actor_account_id"] == 9
    assert connection.committed is True


def test_permanent_group_purge_requires_archival_and_exact_confirmation(monkeypatch):
    from backend.modules.academics import operations

    connection = _Connection()
    connection.commit = lambda: None
    monkeypatch.setattr(operations, "connect_auth_db", lambda: connection)
    candidate = {
        "id": 17,
        "public_id": 701,
        "group_name": "AFT1",
        "status": "archived",
    }
    monkeypatch.setattr(
        operations.academic_repository,
        "get_group_archive_candidate",
        lambda _conn, _id: candidate,
    )
    monkeypatch.setattr(
        operations.academic_repository,
        "count_group_dependencies",
        lambda _conn, _id: {"lessons": 172},
    )
    purged = []
    monkeypatch.setattr(
        operations.academic_repository,
        "purge_group",
        lambda _conn, group_id: purged.append(group_id) or {"id": group_id},
    )
    monkeypatch.setattr(
        operations.academic_repository, "insert_audit_event", lambda *_args, **_kwargs: None
    )

    with pytest.raises(ValueError, match="PURGE AFT1"):
        operations.permanently_purge_group(701, "AFT1")
    assert purged == []

    result = operations.permanently_purge_group(701, "PURGE AFT1")
    assert result["deleted"] == {"lessons": 172}
    assert purged == [17]


def test_workspace_adapters_do_not_own_academic_sql_or_internal_schemas():
    paths = [
        Path("backend/internal_operations/academics_api.py"),
        Path("backend/workspaces/academic_director/academics_api.py"),
        Path("backend/modules/academics/read_service.py"),
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "conn.execute" not in source
        assert "msi_v2." not in source
        assert "backend.internal_operations.schemas" not in source


def test_granular_routes_exist_for_both_management_roles(app):
    del app  # Route prefixes are registered separately; assert the shared adapters here.
    from backend.internal_operations.academics_api import router as admin_router
    from backend.workspaces.academic_director.academics_api import router as director_router

    for router in (admin_router, director_router):
        paths = {}
        for route in router.routes:
            if getattr(route, "path", None):
                paths.setdefault(route.path, set()).update(route.methods or [])
        assert "GET" in paths["/academic/groups"]
        assert "GET" in paths["/academic/groups/{group_id}/summary"]
        assert "GET" in paths["/academic/groups/{group_id}/timetable"]
        assert "GET" in paths["/academic/timetable"]
        assert "GET" in paths["/academic/programs"]
