"""Customer Support dashboard transport and wire-contract tests."""

from __future__ import annotations

import json
import os
from base64 import b64encode
from datetime import UTC, datetime, timedelta

from itsdangerous import TimestampSigner

from backend.modules.domains.reporting.customer_support.schemas import (
    CustomerSupportDashboardMetrics,
    CustomerSupportDashboardResponse,
    CustomerSupportSchool,
)
from backend.modules.people.customer_support.workspace.dashboard_api import (
    get_dashboard_use_case,
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
    return TimestampSigner(secret).sign(b64encode(json.dumps(payload).encode())).decode()


class _DashboardUseCase:
    received_actor = None
    received_filters = None

    def __call__(self, actor, filters):
        self.received_actor = actor
        self.received_filters = filters
        now = datetime(2026, 7, 27, 9, tzinfo=UTC)
        return CustomerSupportDashboardResponse(
            generated_at=now,
            period_days=filters.period_days,
            period_started_at=now - timedelta(days=filters.period_days),
            period_ended_at=now,
            effective_school_ids=sorted(filters.school_ids),
            school_ids=sorted(filters.school_ids),
            available_schools=[
                CustomerSupportSchool(school_id=3, school_name="North School")
            ],
            metrics=CustomerSupportDashboardMetrics(
                open_tickets=8,
                assigned_to_me=3,
                sla_breached_tickets=2,
                overdue_payment_accounts=4,
            ),
        )


def test_dashboard_api_validates_filters_and_serializes_camel_case(app, client):
    use_case = _DashboardUseCase()
    app.dependency_overrides[get_dashboard_use_case] = lambda: use_case
    try:
        client.cookies.set("session", _session("customer_support"))
        response = client.get(
            "/api/v1/customer-support/dashboard?period=7&schoolId=3",
            headers=XHR,
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["periodDays"] == 7
        assert payload["effectiveSchoolIds"] == [3]
        assert payload["metrics"]["slaBreachedTickets"] == 2
        assert payload["availableSchools"][0]["schoolName"] == "North School"
        assert use_case.received_actor.staff_id == 17
        assert use_case.received_filters.school_ids == frozenset({3})

        invalid = client.get(
            "/api/v1/customer-support/dashboard?period=14",
            headers=XHR,
        )
        assert invalid.status_code == 422

        client.cookies.set("session", _session("parent"))
        denied = client.get("/api/v1/customer-support/dashboard", headers=XHR)
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.pop(get_dashboard_use_case, None)
