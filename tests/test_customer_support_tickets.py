"""Customer Support ticket transport and school-scope contract tests."""

from __future__ import annotations

import json
import os
from base64 import b64encode
from datetime import UTC, datetime

import pytest
from itsdangerous import TimestampSigner

from backend.modules.domains.support_cases.tickets.domain_types import (
    TicketCategory,
    TicketStatus,
)
from backend.modules.people.customer_support.tickets.commands import (
    TicketMutationResult,
)
from backend.modules.people.customer_support.tickets.queries import (
    TicketDetailResult,
    TicketMessageResult,
    TicketQueueItem,
    TicketQueuePage,
)
from backend.modules.people.customer_support.tickets.use_cases import _decode_cursor
from backend.modules.people.customer_support.workspace.tickets_api import (
    get_ticket_use_cases,
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
        "staff_id": 17,
    }
    return TimestampSigner(secret).sign(
        b64encode(json.dumps(payload).encode())
    ).decode()


def _queue_item() -> TicketQueueItem:
    timestamp = datetime(2026, 7, 27, 8, tzinfo=UTC)
    return TicketQueueItem(
        ticket_id=51,
        parent_id=9,
        student_id=71,
        school_id=3,
        school_name="North School",
        topic="Payment question",
        category=TicketCategory.PAYMENT,
        status=TicketStatus.NEW,
        requester_name="Parent Example",
        assigned_staff_id=None,
        assigned_staff_name="",
        reply_count=0,
        created_at=timestamp,
        updated_at=timestamp,
    )


class _TicketUseCases:
    def list_tickets(self, actor, query):
        assert actor.staff_id == 17
        assert query.school_id == 3
        return TicketQueuePage(items=(_queue_item(),), next_cursor=None, total=1)

    def get_ticket(self, actor, ticket_id):
        assert ticket_id == 51
        timestamp = datetime(2026, 7, 27, 8, tzinfo=UTC)
        return TicketDetailResult(
            ticket=_queue_item(),
            messages=(
                TicketMessageResult(
                    message_id=1,
                    author_type="parent",
                    author_name="Parent Example",
                    body="Could you explain this charge?",
                    created_at=timestamp,
                ),
            ),
        )

    def reply_to_ticket(self, actor, command):
        assert command.body == "We are checking it."
        return TicketMutationResult(
            ticket_id=command.ticket_id,
            status=TicketStatus.IN_PROGRESS,
            updated_at="2026-07-27T09:00:00Z",
        )

    def assign_ticket(self, actor, command):
        return TicketMutationResult(
            ticket_id=command.ticket_id,
            status=TicketStatus.NEW,
            updated_at="2026-07-27T09:00:00Z",
        )

    def change_ticket_status(self, actor, command):
        return TicketMutationResult(
            ticket_id=command.ticket_id,
            status=command.status,
            updated_at="2026-07-27T09:00:00Z",
        )


@pytest.mark.parametrize("cursor", ["not-base64", "W10", "WzAsIiIsMV0"])
def test_ticket_cursor_rejects_invalid_or_incomplete_values(cursor):
    with pytest.raises(ValueError, match="cursor is invalid"):
        _decode_cursor(cursor)


def test_customer_support_ticket_queue_is_scoped_and_camel_case(app, client):
    app.dependency_overrides[get_ticket_use_cases] = lambda: _TicketUseCases()
    try:
        client.cookies.set("session", _session("customer_support"))
        response = client.get(
            "/api/v1/customer-support/tickets?schoolId=3",
            headers=XHR,
        )
        assert response.status_code == 200
        assert response.json()["data"]["actorStaffId"] == 17
        assert response.json()["data"]["items"][0]["ticketId"] == 51
        assert response.json()["data"]["items"][0]["schoolName"] == "North School"

        client.cookies.set("session", _session("parent"))
        denied = client.get("/api/v1/customer-support/tickets", headers=XHR)
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.pop(get_ticket_use_cases, None)


def test_customer_support_reply_uses_same_origin_guard_and_typed_response(
    app,
    client,
):
    app.dependency_overrides[get_ticket_use_cases] = lambda: _TicketUseCases()
    client.cookies.set("session", _session("customer_support"))
    try:
        rejected = client.post(
            "/api/v1/customer-support/tickets/51/messages",
            json={"body": "We are checking it."},
        )
        assert rejected.status_code == 403

        response = client.post(
            "/api/v1/customer-support/tickets/51/messages",
            headers=XHR,
            json={"body": "We are checking it."},
        )
        assert response.status_code == 200
        assert response.json()["data"] == {
            "ticketId": 51,
            "status": "in_progress",
            "updatedAt": "2026-07-27T09:00:00Z",
        }
    finally:
        app.dependency_overrides.pop(get_ticket_use_cases, None)
