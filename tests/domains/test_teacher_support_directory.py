"""School-scope and pagination tests for the Teacher Support reader."""

from __future__ import annotations

import pytest

from backend.core.access.context import SchoolScope
from backend.core.unit_of_work import Connection, UnitOfWorkFactory
from backend.modules.domains.teacher_records import support_repository
from backend.modules.domains.teacher_records.support_contracts import (
    TeacherSupportCursorError,
    TeacherSupportNotFoundError,
    TeacherSupportScopeError,
)
from backend.modules.domains.teacher_records.support_queries import (
    PostgresTeacherSupportReader,
)


class _Result:
    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _Connection:
    def __init__(self) -> None:
        self.statements: list[str] = []
        self.rollbacks = 0
        self.closes = 0

    def execute(self, sql: str, params: object = None) -> _Result:
        self.statements.append(sql)
        return _Result()

    def commit(self) -> None:
        raise AssertionError("Teacher Support reads must never commit.")

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


def _reader(connection: _Connection) -> PostgresTeacherSupportReader:
    return PostgresTeacherSupportReader(UnitOfWorkFactory(lambda: connection))


def _row(teacher_id: int, full_name: str) -> dict[str, object]:
    return {
        "teacher_id": teacher_id,
        "full_name": full_name,
        "login": f"TCH{teacher_id:04d}",
        "phone": "+998900000000",
        "telegram_username": "teacher",
        "account_status": "active",
        "school_ids": [7],
        "school_names": ["North School"],
        "subject_names": ["Mathematics"],
        "assigned_group_ids": [31, 32],
        "assigned_group_names": ["Math A", "Math B"],
    }


def test_teacher_reader_forwards_scope_and_returns_a_stable_cursor(monkeypatch):
    connection = _Connection()
    captured: dict[str, object] = {}

    def search_rows(conn: Connection, **kwargs):
        captured.update(kwargs)
        return [_row(4, "Alpha Teacher"), _row(9, "Beta Teacher")]

    monkeypatch.setattr(support_repository, "search_teacher_support_rows", search_rows)
    scope = SchoolScope(allowed_school_ids=frozenset({9, 7}))

    first = _reader(connection).search_teachers(
        school_scope=scope,
        search_text=" math ",
        school_id=7,
        status="active",
        cursor=None,
        page_size=1,
    )

    assert [profile.teacher_id for profile in first.items] == [4]
    assert first.next_cursor
    assert captured["allowed_school_ids"] == (7, 9)
    assert captured["selected_school_id"] == 7
    assert captured["limit"] == 2

    decoded: dict[str, object] = {}

    def next_rows(conn: Connection, **kwargs):
        decoded.update(kwargs)
        return []

    monkeypatch.setattr(support_repository, "search_teacher_support_rows", next_rows)
    _reader(connection).search_teachers(
        school_scope=scope,
        search_text="",
        school_id=None,
        status="all",
        cursor=first.next_cursor,
        page_size=25,
    )
    assert decoded["cursor_name"] == "alpha teacher"
    assert decoded["cursor_id"] == 4
    assert connection.statements == ["SET TRANSACTION READ ONLY"] * 2
    assert connection.rollbacks == 2
    assert connection.closes == 2


def test_teacher_reader_rejects_bad_scope_and_cursor_before_query(monkeypatch):
    connection = _Connection()
    monkeypatch.setattr(
        support_repository,
        "search_teacher_support_rows",
        lambda *args, **kwargs: pytest.fail("invalid inputs must not query"),
    )
    reader = _reader(connection)
    scope = SchoolScope(allowed_school_ids=frozenset({7}))

    with pytest.raises(TeacherSupportScopeError):
        reader.search_teachers(
            school_scope=scope,
            search_text="",
            school_id=8,
            status="all",
            cursor=None,
            page_size=25,
        )
    with pytest.raises(TeacherSupportCursorError):
        reader.search_teachers(
            school_scope=scope,
            search_text="",
            school_id=None,
            status="all",
            cursor="not-a-cursor",
            page_size=25,
        )
    assert connection.statements == []


def test_teacher_detail_is_scoped_and_not_found_is_explicit(monkeypatch):
    connection = _Connection()
    captured: dict[str, object] = {}

    def get_row(conn: Connection, **kwargs):
        captured.update(kwargs)
        return _row(12, "Visible Teacher") if kwargs["teacher_id"] == 12 else None

    monkeypatch.setattr(support_repository, "get_teacher_support_row", get_row)
    reader = _reader(connection)
    scope = SchoolScope(allowed_school_ids=frozenset({7}))

    profile = reader.get_teacher(school_scope=scope, teacher_id=12)
    assert profile.assigned_group_names == ("Math A", "Math B")
    assert captured["allowed_school_ids"] == (7,)

    with pytest.raises(TeacherSupportNotFoundError):
        reader.get_teacher(school_scope=scope, teacher_id=99)


def test_teacher_support_repository_reads_only_active_teachers():
    connection = _Connection()

    support_repository.search_teacher_support_rows(
        connection,
        search_text="",
        status="all",
        selected_school_id=None,
        allowed_school_ids=(),
        all_schools=True,
        cursor_name="",
        cursor_id=0,
        limit=26,
    )
    support_repository.get_teacher_support_row(
        connection,
        teacher_id=14,
        allowed_school_ids=(),
        all_schools=True,
    )

    assert len(connection.statements) == 2
    for statement in connection.statements:
        assert "lower(btrim(teacher.status)) = 'active'" in statement
        assert "msi_v2.academy_teachers" not in statement
