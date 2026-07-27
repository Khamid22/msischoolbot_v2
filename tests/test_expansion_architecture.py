"""Regression coverage for the expansion-ready backend foundation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import BaseModel

from backend.application.module_spec import ModuleSpec
from backend.application.modules import build_job_handler_registry
from backend.core.access import (
    ActorContext,
    Capability,
    Role,
    SchoolScope,
    actor_context_from_session,
    capabilities_for_role,
)
from backend.core.api import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ApiModel,
    normalize_page_size,
)
from backend.core.jobs import JobExecutionContext, JobHandlerSpec
from backend.core.unit_of_work import UnitOfWork, UnitOfWorkFactory
from backend.modules.jobs.schemas import EnqueueJobCommand


class _Result:
    rowcount = 1

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class _Connection:
    def __init__(self):
        self.statements: list[tuple[str, object]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def execute(self, sql: str, params: object = None):
        self.statements.append((sql, params))
        return _Result()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


class _WireExample(ApiModel):
    candidate_id: int
    full_name: str


class _ExamplePayload(BaseModel):
    candidate_id: int


def test_api_models_use_readable_python_and_compatible_camel_case_json():
    model = _WireExample.model_validate({"candidateId": 17, "fullName": "Example Candidate"})

    assert model.candidate_id == 17
    assert model.full_name == "Example Candidate"
    assert model.model_dump() == {
        "candidateId": 17,
        "fullName": "Example Candidate",
    }


def test_pagination_policy_is_bounded_and_predictable():
    assert DEFAULT_PAGE_SIZE == 25
    assert MAX_PAGE_SIZE == 100
    assert normalize_page_size(None) == 25
    assert normalize_page_size(0) == 1
    assert normalize_page_size(500) == 100


def test_actor_context_uses_canonical_roles_capabilities_and_school_scope():
    scope = SchoolScope(allowed_school_ids=frozenset({2, 7}))
    actor = ActorContext(
        account_id=11,
        staff_id=13,
        role=Role.HR_MANAGER,
        capabilities=capabilities_for_role(Role.HR_MANAGER),
        school_scope=scope,
        request_id="request-1",
        correlation_id="correlation-1",
    )

    assert actor.has(Capability.MANAGE_RECRUITMENT)
    assert scope.allows(7)
    assert not scope.allows(8)


def test_actor_context_reads_single_school_scope_without_truthy_string_leaks():
    actor = actor_context_from_session(
        {
            "auth_role": "customer_support",
            "school_id": "7",
            "all_schools": "false",
        }
    )

    assert actor.school_scope.allowed_school_ids == frozenset({7})
    assert actor.school_scope.all_schools is False


def test_unit_of_work_rolls_back_uncommitted_writes_and_closes_connection():
    connection = _Connection()

    with UnitOfWork(lambda: connection):
        pass

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_of_work_commits_once_and_does_not_rollback_after_success():
    connection = _Connection()

    with UnitOfWork(lambda: connection) as uow:
        uow.commit()
        with pytest.raises(RuntimeError, match="already complete"):
            uow.commit()

    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1


def test_unit_of_work_explicit_rollback_is_not_repeated_on_exit():
    connection = _Connection()

    with UnitOfWork(lambda: connection) as uow:
        uow.rollback()

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_of_work_instances_cannot_be_reused_for_another_transaction():
    connection = _Connection()
    uow = UnitOfWork(lambda: connection)

    with uow:
        pass

    with pytest.raises(RuntimeError, match="cannot be re-entered"):
        uow.__enter__()


def test_read_only_unit_of_work_marks_transaction_and_rejects_commit():
    connection = _Connection()

    with UnitOfWork(lambda: connection, read_only=True) as uow:
        assert connection.statements == [("SET TRANSACTION READ ONLY", None)]
        with pytest.raises(RuntimeError, match="read-only"):
            uow.commit()

    assert connection.rollbacks == 1


def test_outbox_enqueue_uses_the_current_transaction_connection():
    connection = _Connection()
    captured_connections: list[_Connection] = []

    def enqueue(conn, command):
        captured_connections.append(conn)
        assert command.topic == "example.created"
        return 91

    factory = UnitOfWorkFactory(lambda: connection, job_enqueuer=enqueue)
    with factory.transaction() as uow:
        job_id = uow.enqueue(
            EnqueueJobCommand(
                topic="example.created",
                payload={"candidate_id": 17},
                idempotency_key="example:17",
            )
        )
        uow.commit()

    assert job_id == 91
    assert captured_connections == [connection]


def test_module_job_registry_validates_payload_before_calling_handler():
    handled: list[tuple[int, int]] = []

    def handle(payload: _ExamplePayload, context: JobExecutionContext) -> None:
        handled.append((payload.candidate_id, context.job_id))

    module = ModuleSpec(
        name="example",
        job_handlers=(
            JobHandlerSpec(
                topic="example.created",
                payload_model=_ExamplePayload,
                handler=handle,
            ),
        ),
    )
    registry = build_job_handler_registry((module,))
    handler_spec = registry.handler_for("example.created")
    assert handler_spec is not None

    handler_spec.handle(
        {"candidate_id": 17},
        JobExecutionContext(job_id=91, attempt=1, worker_id="test-worker"),
    )

    assert handled == [(17, 91)]


def test_fresh_app_factory_isolates_application_owned_dependencies():
    from backend.server import create_app

    first = create_app()
    second = create_app()

    assert first is not second
    assert first.state.container is not second.state.container
    assert first.state.limiter is not second.state.limiter


def test_timezone_construction_is_owned_by_core_time_module():
    offenders: list[str] = []
    for path in Path("backend").rglob("*.py"):
        if path == Path("backend/core/time.py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            function_name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            first_argument = node.args[0]
            if (
                function_name == "ZoneInfo"
                and isinstance(first_argument, ast.Constant)
                and first_argument.value == "Asia/Tashkent"
            ):
                offenders.append(f"{path.as_posix()}:{node.lineno}")

    assert offenders == []


def test_new_student_identifier_allocation_uses_database_sequence_and_lock():
    repository_source = Path(
        "backend/modules/domains/support_cases/customer_records_repository.py"
    ).read_text(encoding="utf-8")
    migration_source = Path(
        "database/alembic/versions/0044_student_identifier_sequence.py"
    ).read_text(encoding="utf-8")

    assert "pg_advisory_xact_lock" in repository_source
    assert "nextval('msi_v2.legacy_student_row_id_seq')" in repository_source
    assert "MAX(legacy_student_row_id)" not in repository_source
    assert "CREATE SEQUENCE IF NOT EXISTS" in migration_source
