"""Read-only implementation of the Teacher Support contract."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from backend.core.access.context import SchoolScope
from backend.core.api.pagination import normalize_page_size
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.teacher_records import support_repository
from backend.modules.domains.teacher_records.support_contracts import (
    TeacherSupportCursorError,
    TeacherSupportNotFoundError,
    TeacherSupportProfile,
    TeacherSupportProfilePage,
    TeacherSupportScopeError,
)


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _decode_cursor(cursor: str | None) -> tuple[str, int]:
    token = str(cursor or "").strip()
    if not token:
        return "", 0
    try:
        padded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        name = _normalize_text(payload.get("name")).casefold()
        teacher_id = int(payload.get("teacher_id") or 0)
        if not name or teacher_id <= 0:
            raise ValueError("invalid cursor fields")
        return name, teacher_id
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise TeacherSupportCursorError("The teacher cursor is invalid.") from exc


def _encode_cursor(profile: TeacherSupportProfile) -> str:
    payload = json.dumps(
        {
            "name": profile.full_name.casefold(),
            "teacher_id": profile.teacher_id,
        },
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def _tuple_of_ints(value: object) -> tuple[int, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(int(item) for item in value)


def _tuple_of_text(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _profile_from_row(row) -> TeacherSupportProfile:
    return TeacherSupportProfile(
        teacher_id=int(row["teacher_id"]),
        full_name=str(row["full_name"] or "").strip(),
        login=str(row["login"] or "").strip(),
        phone=str(row["phone"] or "").strip(),
        telegram_username=str(row["telegram_username"] or "").strip(),
        account_status=str(row["account_status"] or "disabled").strip().casefold(),
        school_ids=_tuple_of_ints(row["school_ids"]),
        school_names=_tuple_of_text(row["school_names"]),
        subject_names=_tuple_of_text(row["subject_names"]),
        assigned_group_ids=_tuple_of_ints(row["assigned_group_ids"]),
        assigned_group_names=_tuple_of_text(row["assigned_group_names"]),
    )


def _selected_school_id(
    school_scope: SchoolScope,
    requested_school_id: int | None,
) -> int | None:
    if requested_school_id is None:
        return None
    selected_school_id = int(requested_school_id)
    if selected_school_id <= 0 or not school_scope.allows(selected_school_id):
        raise TeacherSupportScopeError(
            "The selected school is outside your Customer Support scope."
        )
    return selected_school_id


@dataclass(frozen=True)
class PostgresTeacherSupportReader:
    unit_of_work_factory: UnitOfWorkFactory

    def search_teachers(
        self,
        *,
        school_scope: SchoolScope,
        search_text: str,
        school_id: int | None,
        status: str,
        cursor: str | None,
        page_size: int,
    ) -> TeacherSupportProfilePage:
        selected_school_id = _selected_school_id(school_scope, school_id)
        normalized_status = str(status or "all").strip().casefold()
        if normalized_status not in {"all", "active", "pending", "disabled", "archived"}:
            raise ValueError("Unsupported teacher status filter.")
        normalized_page_size = normalize_page_size(page_size)
        cursor_name, cursor_id = _decode_cursor(cursor)
        with self.unit_of_work_factory.read() as unit_of_work:
            rows = support_repository.search_teacher_support_rows(
                unit_of_work.conn,
                search_text=_normalize_text(search_text),
                status=normalized_status,
                selected_school_id=selected_school_id,
                allowed_school_ids=tuple(sorted(school_scope.allowed_school_ids)),
                all_schools=school_scope.all_schools,
                cursor_name=cursor_name,
                cursor_id=cursor_id,
                limit=normalized_page_size + 1,
            )

        profiles = tuple(_profile_from_row(row) for row in rows[:normalized_page_size])
        has_more = len(rows) > normalized_page_size
        return TeacherSupportProfilePage(
            items=profiles,
            next_cursor=_encode_cursor(profiles[-1]) if has_more and profiles else None,
        )

    def get_teacher(
        self,
        *,
        school_scope: SchoolScope,
        teacher_id: int,
    ) -> TeacherSupportProfile:
        parsed_teacher_id = int(teacher_id)
        if parsed_teacher_id <= 0:
            raise TeacherSupportNotFoundError("Teacher was not found.")
        with self.unit_of_work_factory.read() as unit_of_work:
            row = support_repository.get_teacher_support_row(
                unit_of_work.conn,
                teacher_id=parsed_teacher_id,
                allowed_school_ids=tuple(sorted(school_scope.allowed_school_ids)),
                all_schools=school_scope.all_schools,
            )
        if not row:
            raise TeacherSupportNotFoundError("Teacher was not found in your assigned schools.")
        return _profile_from_row(row)


__all__ = ["PostgresTeacherSupportReader"]
