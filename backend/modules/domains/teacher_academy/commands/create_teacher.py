"""Create a Teacher Academy teacher and lifecycle profile atomically."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from backend.core.unit_of_work import Connection
from backend.modules.domains.recruitment import contracts as recruitment_contracts
from backend.modules.domains.teacher_academy import mutations_repository, repository

DEFAULT_ACADEMY_POSITION = "Trainee Teacher"
DEFAULT_ACADEMY_EMPLOYMENT_TYPE = "academy"


class ConnectionContext(Connection, Protocol):
    def __enter__(self) -> ConnectionContext: ...

    def __exit__(self, exc_type, exc_value, traceback) -> bool: ...


@dataclass(frozen=True)
class CreateAcademyTeacherCommand:
    full_name: str
    subject_program_id: int | str
    selected_curriculum_item_ids: Sequence[int | str] | str | None = None
    position: str = DEFAULT_ACADEMY_POSITION
    employment_type: str = DEFAULT_ACADEMY_EMPLOYMENT_TYPE
    telegram_username: str = ""
    phone: str = ""
    email: str = ""
    academy_start_date: str = ""
    mentor_id: int | str | None = None
    department_head_id: int | str | None = None
    notes: str = ""
    created_by: str = ""


@dataclass(frozen=True)
class AcademyTeacherCredentials:
    login: str
    display_name: str
    subject_name: str

    def to_legacy_payload(self) -> dict[str, str]:
        return {
            "role": "teacher",
            "login": self.login,
            "teacher_code": self.login,
            "temporary_password": self.login,
            "display_name": self.display_name,
            "subject_name": self.subject_name,
        }


@dataclass(frozen=True)
class CreateAcademyTeacherResult:
    is_created: bool
    message: str = ""
    credentials: AcademyTeacherCredentials | None = None


@dataclass(frozen=True)
class _TeacherIdentity:
    teacher_id: int
    staff_id: int
    account_id: int
    login: str


@dataclass(frozen=True)
class _CreationPlan:
    program: Any
    lessons: Sequence[Any]


@dataclass(frozen=True)
class _CreatedTeacher:
    academy_teacher_id: int
    identity: _TeacherIdentity
    program: Any


@dataclass(frozen=True)
class CreateAcademyTeacherDependencies:
    connect: Callable[[], ConnectionContext]
    generate_password_hash: Callable[[str], str]
    provision_account: Callable[..., int]
    notify: Callable[..., dict[str, Any]]
    now: Callable[[], str]
    as_int: Callable[[Any], int]
    get_program: Callable[[Connection, Any], Any]
    get_lessons: Callable[[Connection, Any, Any], tuple[list[Any], str]]


def _failure(message: str) -> CreateAcademyTeacherResult:
    return CreateAcademyTeacherResult(is_created=False, message=message)


def _normalized_position(command: CreateAcademyTeacherCommand) -> str:
    return command.position.strip() or DEFAULT_ACADEMY_POSITION


def _create_teacher_identity(
    conn: Connection,
    *,
    command: CreateAcademyTeacherCommand,
    program: Any,
    full_name: str,
    occurred_at: str,
    dependencies: CreateAcademyTeacherDependencies,
) -> tuple[_TeacherIdentity | None, str]:
    teacher_id = repository.insert_teacher_profile_row(
        conn,
        full_name,
        notes=command.notes.strip(),
        status="academy",
        subject_id=int(program["subject_id"]),
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    if not teacher_id:
        return None, "Unable to create the teacher profile."
    mutations_repository.acquire_teacher_login_advisory_lock(conn)
    login = repository.get_next_teacher_code(conn)
    password_hash = dependencies.generate_password_hash(login)
    staff_id = repository.insert_teacher_auth(
        conn,
        teacher_id,
        login,
        login,
        password_hash,
        occurred_at,
    )
    if not staff_id:
        return None, "Unable to provision the Academy teacher login."
    account_id = dependencies.provision_account(
        conn,
        teacher_id=teacher_id,
        staff_id=staff_id,
        login=login,
        password_hash=password_hash,
        full_name=full_name,
    )
    return (
        _TeacherIdentity(
            teacher_id=int(teacher_id),
            staff_id=int(staff_id),
            account_id=int(account_id or 0),
            login=login,
        ),
        "",
    )


def _create_academy_record(
    conn: Connection,
    *,
    command: CreateAcademyTeacherCommand,
    program: Any,
    full_name: str,
    staff_id: int,
    occurred_at: str,
    dependencies: CreateAcademyTeacherDependencies,
) -> int:
    return int(
        mutations_repository.insert_academy_teacher(
            conn,
            staff_id=staff_id,
            full_name=full_name,
            subject_id=int(program["subject_id"]),
            subject_program_id=int(program["id"]),
            position=_normalized_position(command),
            employment_type=command.employment_type.strip() or DEFAULT_ACADEMY_EMPLOYMENT_TYPE,
            telegram_username=command.telegram_username.strip(),
            phone=command.phone.strip(),
            email=command.email.strip(),
            academy_start_date=command.academy_start_date.strip(),
            mentor_id=dependencies.as_int(command.mentor_id),
            department_head_id=dependencies.as_int(command.department_head_id),
            notes=command.notes.strip(),
            created_by=command.created_by.strip(),
            created_at=occurred_at,
        )
        or 0
    )


def _create_lifecycle_profile(
    conn: Connection,
    *,
    command: CreateAcademyTeacherCommand,
    academy_teacher_id: int,
    account_id: int,
    full_name: str,
    program: Any,
    occurred_at: str,
) -> recruitment_contracts.AcademyLifecycleProfileResult:
    return recruitment_contracts.create_academy_lifecycle_profile(
        conn,
        recruitment_contracts.CreateAcademyLifecycleProfileCommand(
            academy_teacher_id=academy_teacher_id,
            full_name=full_name,
            subject_id=int(program["subject_id"]),
            applied_position=_normalized_position(command),
            phone=command.phone.strip(),
            email=command.email.strip(),
            telegram_username=command.telegram_username.strip(),
            linked_account_id=account_id or None,
            created_by=command.created_by.strip(),
            occurred_at=occurred_at,
        ),
    )


def _insert_lesson_assignments(
    conn: Connection,
    *,
    command: CreateAcademyTeacherCommand,
    academy_teacher_id: int,
    program: Any,
    lessons: Sequence[Any],
    occurred_at: str,
) -> None:
    for sequence_number, lesson in enumerate(lessons, start=1):
        mutations_repository.insert_academy_lesson_assignment(
            conn,
            academy_teacher_id=academy_teacher_id,
            subject_id=int(program["subject_id"]),
            subject_program_id=int(program["id"]),
            curriculum_item_id=int(lesson["id"]),
            sequence_no=sequence_number,
            lesson_number=str(lesson["lesson_number"] or ""),
            lesson_topic=str(lesson["title"] or ""),
            focus_areas_json=json.dumps([]),
            created_by=command.created_by.strip(),
            created_at=occurred_at,
        )


def _link_profile_and_identity(
    conn: Connection,
    *,
    command: CreateAcademyTeacherCommand,
    identity: _TeacherIdentity,
    academy_teacher_id: int,
    full_name: str,
    program: Any,
    occurred_at: str,
) -> str:
    lifecycle = _create_lifecycle_profile(
        conn,
        command=command,
        academy_teacher_id=academy_teacher_id,
        account_id=identity.account_id,
        full_name=full_name,
        program=program,
        occurred_at=occurred_at,
    )
    if not lifecycle.is_linked:
        return "Unable to link the Teacher Academy lifecycle profile."
    is_identity_linked = mutations_repository.link_teacher_identity_to_candidate(
        conn,
        teacher_id=identity.teacher_id,
        candidate_id=lifecycle.candidate_id,
        updated_at=occurred_at,
    )
    return "" if is_identity_linked else "Unable to link the Teacher Academy account profile."


def _notify_created_teacher(
    *,
    command: CreateAcademyTeacherCommand,
    dependencies: CreateAcademyTeacherDependencies,
    academy_teacher_id: int,
    full_name: str,
    program: Any,
) -> str:
    subject_name = str(program["subject_name"] or "")
    dependencies.notify(
        academy_teacher={
            "id": academy_teacher_id,
            "full_name": full_name,
            "subject_id": int(program["subject_id"] or 0),
            "subject": subject_name,
            "telegram_username": command.telegram_username.strip(),
            "telegram_user_id": 0,
        },
        event_type="teacher_created",
        title="Welcome to MSI School",
        body="Welcome to the MSI School family.",
        source="Academic Department",
    )
    return subject_name


def _load_creation_plan(
    conn: Connection,
    *,
    command: CreateAcademyTeacherCommand,
    dependencies: CreateAcademyTeacherDependencies,
) -> tuple[_CreationPlan | None, str]:
    program = dependencies.get_program(conn, command.subject_program_id)
    if not program:
        return None, "Select a subject curriculum program."
    lessons, lesson_error = dependencies.get_lessons(
        conn,
        program["id"],
        command.selected_curriculum_item_ids,
    )
    if lesson_error:
        return None, lesson_error
    return _CreationPlan(program=program, lessons=lessons), ""


def _persist_teacher(
    conn: Connection,
    *,
    command: CreateAcademyTeacherCommand,
    dependencies: CreateAcademyTeacherDependencies,
    plan: _CreationPlan,
    full_name: str,
    occurred_at: str,
) -> tuple[_CreatedTeacher | None, str]:
    identity, identity_error = _create_teacher_identity(
        conn,
        command=command,
        program=plan.program,
        full_name=full_name,
        occurred_at=occurred_at,
        dependencies=dependencies,
    )
    if not identity:
        return None, identity_error
    academy_teacher_id = _create_academy_record(
        conn,
        command=command,
        program=plan.program,
        full_name=full_name,
        staff_id=identity.staff_id,
        occurred_at=occurred_at,
        dependencies=dependencies,
    )
    if not academy_teacher_id:
        return None, "Unable to create the Teacher Academy record."
    link_error = _link_profile_and_identity(
        conn,
        command=command,
        identity=identity,
        academy_teacher_id=academy_teacher_id,
        full_name=full_name,
        program=plan.program,
        occurred_at=occurred_at,
    )
    if link_error:
        return None, link_error
    _insert_lesson_assignments(
        conn,
        command=command,
        academy_teacher_id=academy_teacher_id,
        program=plan.program,
        lessons=plan.lessons,
        occurred_at=occurred_at,
    )
    return _CreatedTeacher(academy_teacher_id, identity, plan.program), ""


def create_academy_teacher(
    command: CreateAcademyTeacherCommand,
    dependencies: CreateAcademyTeacherDependencies,
) -> CreateAcademyTeacherResult:
    full_name = command.full_name.strip()
    if not full_name:
        return _failure("Trainee name is required.")

    occurred_at = dependencies.now()
    with dependencies.connect() as conn:
        plan, plan_error = _load_creation_plan(
            conn,
            command=command,
            dependencies=dependencies,
        )
        if not plan:
            return _failure(plan_error)
        created, creation_error = _persist_teacher(
            conn,
            command=command,
            dependencies=dependencies,
            plan=plan,
            full_name=full_name,
            occurred_at=occurred_at,
        )
        if not created:
            conn.rollback()
            return _failure(creation_error)
        conn.commit()

    assert created is not None
    subject_name = _notify_created_teacher(
        command=command,
        dependencies=dependencies,
        academy_teacher_id=created.academy_teacher_id,
        full_name=full_name,
        program=created.program,
    )
    return CreateAcademyTeacherResult(
        is_created=True,
        credentials=AcademyTeacherCredentials(
            login=created.identity.login,
            display_name=full_name,
            subject_name=subject_name,
        ),
    )


__all__ = [
    "AcademyTeacherCredentials",
    "CreateAcademyTeacherCommand",
    "CreateAcademyTeacherDependencies",
    "CreateAcademyTeacherResult",
    "create_academy_teacher",
]
