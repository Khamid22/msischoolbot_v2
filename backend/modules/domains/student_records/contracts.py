"""Public Student Records use cases."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from backend.core.unit_of_work import Connection
from backend.modules.domains.identity.contracts import (
    ProvisionStudentAccountCommand,
    provision_student_account,
)
from backend.modules.domains.student_records import repository
from backend.modules.domains.student_records.service import (
    get_dashboard_student_profile,
    get_student_db_id_by_enrollment_id,
    get_student_subject_enrollments,
    list_enrolled_subject_options,
    record_student_activity,
    resolve_public_dashboard_for_student_row,
)


@dataclass(frozen=True)
class CreateAdmissionStudentCommand:
    full_name: str
    school_id: int


@dataclass(frozen=True)
class CreateAdmissionStudentResult:
    student_id: int
    legacy_student_row_id: int
    student_code: str


def create_admission_student(
    conn: Connection,
    command: CreateAdmissionStudentCommand,
) -> CreateAdmissionStudentResult:
    repository.acquire_student_identifier_lock(conn)
    student_code = repository.next_student_code(conn)
    legacy_student_row_id = repository.next_legacy_student_row_id(conn)
    student_id = repository.insert_admission_student(
        conn,
        student_code=student_code,
        full_name=" ".join(command.full_name.strip().split()),
        school_id=command.school_id,
        legacy_student_row_id=legacy_student_row_id,
    )
    if student_id <= 0:
        raise RuntimeError("The student record could not be created.")
    account = provision_student_account(
        conn,
        ProvisionStudentAccountCommand(
            student_id=student_id,
            login=student_code,
            initial_password=secrets.token_urlsafe(18),
            full_name=command.full_name,
            school_id=command.school_id,
        ),
    )
    if account.account_id <= 0:
        raise RuntimeError("The student identity could not be provisioned.")
    return CreateAdmissionStudentResult(
        student_id=student_id,
        legacy_student_row_id=legacy_student_row_id,
        student_code=student_code,
    )


def parent_can_access_dashboard(parent_id, dashboard_student_id):
    from backend.modules.domains.parent_relationships.contracts import (
        parent_can_access_dashboard as can_access_dashboard,
    )

    return can_access_dashboard(parent_id, dashboard_student_id)


__all__ = [
    "CreateAdmissionStudentCommand",
    "CreateAdmissionStudentResult",
    "create_admission_student",
    "get_dashboard_student_profile",
    "get_student_db_id_by_enrollment_id",
    "get_student_subject_enrollments",
    "list_enrolled_subject_options",
    "parent_can_access_dashboard",
    "record_student_activity",
    "resolve_public_dashboard_for_student_row",
]
