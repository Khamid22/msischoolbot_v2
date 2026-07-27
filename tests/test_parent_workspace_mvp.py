"""Parent workspace policy, wire-contract, and transport tests."""

from __future__ import annotations

import json
import os
from base64 import b64encode

import pytest
from itsdangerous import TimestampSigner

from backend.core.access.capabilities import capabilities_for_role
from backend.core.access.context import ActorContext, SchoolScope
from backend.core.access.domain_types import Capability, Role
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.communications import announcements_repository
from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketCategory,
    TicketStatus,
)
from backend.modules.people.parent import commands as parent_commands_module
from backend.modules.people.parent.commands import ParentCommands
from backend.modules.people.parent.policies import (
    ParentAccessError,
    require_parent_capability,
)
from backend.modules.people.parent.schemas import (
    CreateParentTicketRequest,
    ParentChildrenResponse,
    ParentChildResponse,
    ParentOverviewResponse,
    ParentPaymentSummaryResponse,
    ParentPreferenceResponse,
    ParentTicketResponse,
    ParentTicketsResponse,
    ParentUpdatesResponse,
)
from backend.modules.people.parent.workspace.api import (
    get_parent_commands,
    get_parent_queries,
)

XHR = {"X-Requested-With": "XMLHttpRequest"}


def _session(role: str) -> str:
    secret = (
        os.environ.get("APP_SECRET_KEY", "").strip()
        or "dev-only-insecure-key-do-not-use-in-prod"
    )
    payload = {
        "auth_role": role,
        "auth_login": f"{role}@test",
        "account_id": 41,
        "parent_id": 9,
        "csrf_token": "parent-csrf",
    }
    encoded = b64encode(json.dumps(payload).encode())
    return TimestampSigner(secret).sign(encoded).decode()


def _actor(
    *,
    role: Role = Role.PARENT,
    capabilities: frozenset[Capability] | None = None,
    parent_id: int | None = 9,
) -> ActorContext:
    return ActorContext(
        account_id=41,
        role=role,
        capabilities=capabilities or capabilities_for_role(role),
        school_scope=SchoolScope(),
        parent_id=parent_id,
    )


def _child() -> ParentChildResponse:
    return ParentChildResponse(
        student_row_id=71,
        student_code="ST0071",
        full_name="Linked Child",
        school_name="North School",
        dashboard_url="/parent/dashboard/71",
    )


def _ticket() -> ParentTicketResponse:
    return ParentTicketResponse(
        ticket_id=31,
        parent_id=9,
        student_row_id=71,
        student_name="Linked Child",
        student_code="ST0071",
        school_id=3,
        school_name="North School",
        category=TicketCategory.ATTENDANCE,
        topic="Attendance question",
        status=TicketStatus.NEW,
        assigned_staff_id=None,
        assigned_staff_name="",
        created_at="2026-07-27T08:00:00Z",
        updated_at="2026-07-27T08:00:00Z",
        resolved_at="",
    )


class _ParentQueries:
    def overview(self, actor: ActorContext):
        assert actor.parent_id == 9
        return ParentOverviewResponse(
            children=[_child()],
            payment_summary=ParentPaymentSummaryResponse(due_total=250_000),
            open_ticket_count=1,
            preference=ParentPreferenceResponse(
                parent_id=9,
                display_name="Parent",
                preferred_language="uz",
            ),
        )

    def list_children(self, actor: ActorContext):
        return ParentChildrenResponse(items=[_child()])

    def get_child(self, actor: ActorContext, student_row_id: int):
        assert student_row_id == 71
        return _child()

    def list_updates(self, actor: ActorContext, *, limit: int):
        assert limit <= 100
        return ParentUpdatesResponse()

    def list_payments(self, actor: ActorContext, *, student_row_id=None):
        raise AssertionError("Payments are not used by this transport test.")

    def list_tickets(self, actor: ActorContext, *, limit: int):
        return ParentTicketsResponse(items=[_ticket()])

    def get_ticket(self, actor: ActorContext, ticket_id: int):
        assert ticket_id == 31
        return _ticket()

    def get_preference(self, actor: ActorContext):
        return ParentPreferenceResponse(
            parent_id=9,
            display_name="Parent",
            preferred_language="uz",
        )


class _ParentCommands:
    def create_ticket(self, actor, request):
        assert request.student_row_id == 71
        return _ticket()

    def reply_to_ticket(self, actor, ticket_id, request):
        assert ticket_id == 31
        assert request.body == "Thank you"
        return _ticket()

    def update_preference(self, actor, request):
        return ParentPreferenceResponse(
            parent_id=9,
            display_name="Parent",
            preferred_language=request.preferred_language,
        )


def test_parent_policy_requires_role_capability_and_profile():
    assert require_parent_capability(_actor(), Capability.CONTACT_SUPPORT) == 9
    with pytest.raises(ParentAccessError):
        require_parent_capability(_actor(role=Role.STUDENT), Capability.CONTACT_SUPPORT)
    with pytest.raises(ParentAccessError):
        require_parent_capability(
            _actor(capabilities=frozenset({Capability.VIEW_DASHBOARD})),
            Capability.CONTACT_SUPPORT,
        )
    with pytest.raises(ParentAccessError):
        require_parent_capability(_actor(parent_id=None), Capability.CONTACT_SUPPORT)


class _RowsResult:
    def fetchall(self):
        return []


class _AnnouncementConnection:
    sql = ""
    params = ()

    def execute(self, sql: str, params=()):
        self.sql = sql
        self.params = params
        return _RowsResult()


def test_parent_announcements_are_published_and_parent_audience_only():
    connection = _AnnouncementConnection()
    announcements_repository.list_published_announcement_rows_for_audience(
        connection,
        "parents",
    )

    assert "status = 'published'" in connection.sql
    assert "audience IN ('all', %s)" in connection.sql
    assert "published_at <= now()" in connection.sql
    assert "pinned DESC" in connection.sql
    assert connection.params == ("parents",)


class _WriteConnection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def execute(self, sql: str, params=None):
        raise AssertionError("The failing domain command should run before repository SQL.")

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


def test_parent_ticket_command_rolls_back_the_shared_transaction(monkeypatch):
    connection = _WriteConnection()
    commands = ParentCommands(UnitOfWorkFactory(lambda: connection))
    monkeypatch.setattr(
        parent_commands_module,
        "create_parent_ticket",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("opening message failed")),
    )

    with pytest.raises(RuntimeError, match="opening message failed"):
        commands.create_ticket(
            _actor(),
            CreateParentTicketRequest(
                student_row_id=71,
                category=TicketCategory.ATTENDANCE,
                topic="Attendance question",
                message="Please check this attendance record.",
            ),
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_parent_api_preserves_camel_case_and_role_isolation(app, client):
    app.dependency_overrides[get_parent_queries] = lambda: _ParentQueries()
    try:
        client.cookies.set("session", _session("parent"))
        response = client.get("/api/v1/parent/overview", headers=XHR)
        assert response.status_code == 200
        assert response.json()["data"]["children"][0]["studentRowId"] == 71
        assert response.json()["data"]["paymentSummary"]["dueTotal"] == 250_000
        assert response.json()["data"]["preference"]["preferredLanguage"] == "uz"

        client.cookies.set("session", _session("student"))
        denied = client.get("/api/v1/parent/overview", headers=XHR)
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.pop(get_parent_queries, None)


def test_parent_workspace_and_legacy_dashboard_routes_stay_registered(app):
    paths = set()

    def collect(route_list):
        for route in route_list:
            path = getattr(route, "path", "")
            if path:
                paths.add(path)
            original_router = getattr(route, "original_router", None)
            if original_router is not None:
                collect(original_router.routes)
                continue
            nested = getattr(route, "routes", None)
            if nested:
                collect(nested)

    collect(app.routes)
    assert {
        "/parent",
        "/parent/updates",
        "/parent/children",
        "/parent/children/{student_row_id}",
        "/parent/payments",
        "/parent/support",
        "/parent/support/{ticket_id}",
        "/parent/dashboard/{student_row_id}",
    } <= paths


def test_parent_ticket_mutation_uses_same_origin_guard_and_typed_wire_format(
    app,
    client,
):
    app.dependency_overrides[get_parent_commands] = lambda: _ParentCommands()
    client.cookies.set("session", _session("parent"))
    payload = {
        "studentRowId": 71,
        "category": "attendance",
        "topic": "Attendance question",
        "message": "Please help with this attendance record.",
    }
    try:
        rejected = client.post("/api/v1/parent/tickets", json=payload)
        assert rejected.status_code == 403

        created = client.post(
            "/api/v1/parent/tickets",
            headers=XHR,
            json=payload,
        )
        assert created.status_code == 201
        assert created.json()["data"]["ticketId"] == 31
        assert "ticket_id" not in created.json()["data"]
    finally:
        app.dependency_overrides.pop(get_parent_commands, None)
