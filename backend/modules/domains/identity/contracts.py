"""Typed transaction-aware identity commands for other modules."""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.unit_of_work import Connection
from backend.modules.domains.identity import repository, staff_accounts
from backend.modules.domains.identity.passwords import generate_password_hash
from backend.modules.domains.identity.session import (
    build_dashboard_url,
    current_auth_login,
    current_auth_role,
    current_parent_id,
    current_staff_id,
    current_student_db_id,
    current_student_enrollment_id,
    current_student_full_name,
    current_student_school_code,
    current_teacher_id,
    current_teacher_staff_id,
    set_account_session,
    url_for,
)


@dataclass(frozen=True)
class ProvisionStudentAccountCommand:
    student_id: int
    login: str
    initial_password: str
    full_name: str
    school_id: int | None
    status: str = "active"


@dataclass(frozen=True)
class ProvisionStudentAccountResult:
    account_id: int


@dataclass(frozen=True)
class ProvisionParentAccountCommand:
    parent_id: int
    full_name: str
    phone: str
    telegram_username: str = ""


@dataclass(frozen=True)
class ProvisionParentAccountResult:
    account_id: int


@dataclass(frozen=True)
class StaffSchoolScopeAssignment:
    staff_id: int
    raw_scope: str


def get_staff_school_scope_assignment(
    conn: Connection,
    *,
    staff_id: int | None,
    account_id: int | None,
) -> StaffSchoolScopeAssignment | None:
    row = repository.get_staff_school_scope_row(
        conn,
        staff_id=staff_id,
        account_id=account_id,
    )
    if not row:
        return None
    return StaffSchoolScopeAssignment(
        staff_id=int(row["staff_id"]),
        raw_scope=str(row["school_scope"] or "").strip(),
    )


def provision_student_account(
    conn: Connection,
    command: ProvisionStudentAccountCommand,
) -> ProvisionStudentAccountResult:
    login = command.login.strip().upper()
    if not login or not command.initial_password:
        return ProvisionStudentAccountResult(account_id=0)
    current = repository.find_student_account_row(
        conn,
        student_id=command.student_id,
        login=login,
    )
    account_id = repository.save_student_account(
        conn,
        account_id=int(current["id"] or 0) if current else 0,
        student_id=command.student_id,
        login=login,
        password_hash=generate_password_hash(command.initial_password),
        full_name=" ".join(command.full_name.strip().split()),
        school_id=command.school_id,
        status=command.status.strip().casefold() or "active",
    )
    return ProvisionStudentAccountResult(account_id=account_id)


def provision_parent_account(
    conn: Connection,
    command: ProvisionParentAccountCommand,
) -> ProvisionParentAccountResult:
    from backend.modules.domains.identity.service import (
        provision_parent_account as provision,
    )

    account_id = provision(
        conn,
        parent_id=command.parent_id,
        full_name=command.full_name,
        phone=command.phone,
        telegram_username=command.telegram_username,
    )
    return ProvisionParentAccountResult(account_id=account_id)


def create_hr_manager_account(
    *,
    display_name: str = "HR Manager",
) -> tuple[bool, str, dict[str, object]]:
    return staff_accounts.create_hr_manager_account(display_name=display_name)


def create_customer_support_account(
    *,
    display_name: str = "Customer Support",
) -> tuple[bool, str, dict[str, object]]:
    return staff_accounts.create_customer_support_account(display_name=display_name)


def create_academic_director_account(
    *,
    login: str = "AD0001",
    display_name: str = "Academic Director",
    temporary_password: str = "",
    commit: bool = True,
) -> tuple[bool, str, dict[str, object]]:
    return staff_accounts.create_academic_director_account(
        login=login,
        display_name=display_name,
        temporary_password=temporary_password,
        commit=commit,
    )


def create_head_of_department_account(
    *,
    display_name: str,
    subject_id: object,
    created_by: str = "",
) -> tuple[bool, str, dict[str, object]]:
    return staff_accounts.create_head_of_department_account(
        display_name=display_name,
        subject_id=subject_id,
        created_by=created_by,
    )


def reset_head_of_department_password(
    account_id: object,
    *,
    actor_account_id: object = None,
    actor_login: str = "",
) -> tuple[bool, str, dict[str, object]]:
    return staff_accounts.reset_head_of_department_password(
        account_id,
        actor_account_id=actor_account_id,
        actor_login=actor_login,
    )


def list_active_subjects() -> list[dict[str, object]]:
    return staff_accounts.list_active_subjects()


def list_head_of_department_accounts() -> dict[str, object]:
    return staff_accounts.list_head_of_department_accounts()


def reset_student_password(
    student_db_id: object,
    *,
    conn: Connection | None = None,
) -> dict[str, object]:
    from backend.modules.domains.identity.service import reset_student_password as reset_password

    return reset_password(student_db_id, conn=conn)


__all__ = [
    "ProvisionParentAccountCommand",
    "ProvisionParentAccountResult",
    "ProvisionStudentAccountCommand",
    "ProvisionStudentAccountResult",
    "StaffSchoolScopeAssignment",
    "create_academic_director_account",
    "create_customer_support_account",
    "create_head_of_department_account",
    "create_hr_manager_account",
    "build_dashboard_url",
    "current_auth_login",
    "current_auth_role",
    "current_parent_id",
    "current_staff_id",
    "current_student_db_id",
    "current_student_enrollment_id",
    "current_student_full_name",
    "current_student_school_code",
    "current_teacher_id",
    "current_teacher_staff_id",
    "get_staff_school_scope_assignment",
    "list_active_subjects",
    "list_head_of_department_accounts",
    "provision_student_account",
    "provision_parent_account",
    "reset_head_of_department_password",
    "reset_student_password",
    "set_account_session",
    "url_for",
]
