"""Customer Support records workspace contracts and domain safeguards."""

from __future__ import annotations

import json
import os
from base64 import b64encode
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner

from backend.core.access.management_permissions import role_has_permission
from backend.core.access.workspace_permissions import has_workspace_permission
from backend.modules.customer_support import repository, service
from backend.workspaces.customer_support.api import router


XHR = {"X-Requested-With": "XMLHttpRequest"}


def _session(role: str, *, csrf: str = "support-csrf") -> str:
    secret = os.environ.get("APP_SECRET_KEY", "").strip() or "dev-only-insecure-key-do-not-use-in-prod"
    payload = {
        "auth_role": role,
        "auth_login": f"{role}@test",
        "account_id": 41,
        "staff_id": 17,
        "csrf_token": csrf,
    }
    return TimestampSigner(secret).sign(b64encode(json.dumps(payload).encode())).decode()


def test_customer_support_permissions_are_explicit_and_academics_stay_read_only():
    for permission in ("manage_students", "manage_parents", "manage_payments"):
        assert role_has_permission("customer_support", permission)
    for permission in (
        "manage_student_records",
        "manage_parent_records",
        "manage_student_access",
        "manage_payments",
    ):
        assert has_workspace_permission("customer_support", permission)
    assert not role_has_permission("customer_support", "manage_academics")


def test_customer_support_api_is_role_isolated(client, monkeypatch):
    monkeypatch.setattr(
        service,
        "context",
        lambda actor: {"schools": [], "allSchools": True, "actor": actor.login},
    )
    client.cookies.set("session", _session("customer_support"))
    allowed = client.get("/api/v1/customer-support/context", headers=XHR)
    assert allowed.status_code == 200
    assert allowed.json()["data"]["actor"] == "customer_support@test"

    for role in ("hr_manager", "academic_director", "parent", "student"):
        client.cookies.set("session", _session(role))
        assert client.get("/api/v1/customer-support/context", headers=XHR).status_code == 403


def test_api_exposes_void_but_never_hard_delete_for_payments():
    routes = {
        (method, route.path)
        for route in router.routes
        for method in (route.methods or set())
    }
    assert ("POST", "/customer-support/payments/{payment_id}/void") in routes
    assert ("POST", "/customer-support/payments/{payment_id}/settlement") in routes
    assert ("DELETE", "/customer-support/payments/{payment_id}") not in routes


def test_school_scope_uses_only_staff_allowed_schools(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_staff_scope_row",
        lambda conn, **kwargs: {"id": 17, "school_scope": "north, 3"},
    )
    monkeypatch.setattr(
        repository,
        "list_school_rows",
        lambda conn: [
            {"id": 1, "school_key": "north", "school_name": "North School", "status": "active"},
            {"id": 2, "school_key": "south", "school_name": "South School", "status": "active"},
            {"id": 3, "school_key": "central", "school_name": "Central School", "status": "active"},
        ],
    )
    scope = service.load_scope(object(), service.SupportActor(17, 41, "support"))
    assert not scope.all_schools
    assert scope.school_ids == (1, 3)
    assert [school["school_name"] for school in scope.schools] == ["North School", "Central School"]


def test_empty_scope_means_all_but_missing_staff_identity_is_denied(monkeypatch):
    schools = [{"id": 1, "school_key": "north", "school_name": "North", "status": "active"}]
    monkeypatch.setattr(repository, "list_school_rows", lambda conn: schools)
    monkeypatch.setattr(
        repository,
        "get_staff_scope_row",
        lambda conn, **kwargs: {"id": 17, "school_scope": ""},
    )
    assert service.load_scope(object(), service.SupportActor(17, 41, "support")).all_schools

    monkeypatch.setattr(repository, "get_staff_scope_row", lambda conn, **kwargs: None)
    with pytest.raises(service.ScopeError, match="scope could not be resolved"):
        service.load_scope(object(), service.SupportActor(None, None, "support"))


def test_archive_is_blocked_by_active_groups_without_mutating(monkeypatch):
    class Connection:
        committed = False

        def commit(self):
            self.committed = True

    conn = Connection()

    @contextmanager
    def opened():
        yield conn

    scope = service.SchoolScope(True, (1,), ({"id": 1},), "")
    monkeypatch.setattr(service, "_connect", opened)
    monkeypatch.setattr(service, "load_scope", lambda connection, actor: scope)
    monkeypatch.setattr(
        repository,
        "get_student_row",
        lambda connection, student_id: {"id": student_id, "school_id": 1, "version": 4},
    )
    monkeypatch.setattr(
        repository,
        "list_active_enrollment_blockers",
        lambda connection, student_id: [{"group_id": 9, "group_name": "Math A"}],
    )
    monkeypatch.setattr(
        repository,
        "set_student_lifecycle",
        lambda *args, **kwargs: pytest.fail("blocked archive must not update the student"),
    )

    with pytest.raises(service.DependencyConflictError) as error:
        service.set_student_lifecycle(
            service.SupportActor(17, 41, "support"),
            5,
            expected_version=4,
            active=False,
            reason="Requested transfer",
        )
    assert error.value.details == {"groups": [{"group_id": 9, "group_name": "Math A"}]}
    assert not conn.committed


def test_versions_conflict_and_cursor_round_trip():
    item = {"display_name": "Zoë Example", "kind": "student", "id": 75}
    assert service._decode_cursor(service._encode_cursor(item)) == (
        "zoë example",
        "student",
        75,
    )
    with pytest.raises(service.CustomerSupportError, match="cursor is invalid"):
        service._decode_cursor("not-a-valid-cursor")
    with pytest.raises(service.VersionConflictError) as error:
        service._ensure_version(8, 7)
    assert error.value.status_code == 409
    assert error.value.details == {"currentVersion": 8}


def test_voided_payments_remain_visible_but_never_change_totals():
    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)
    payload = service._payments_payload(
        [
            {"id": 1, "amount": 100, "currency": "UZS", "status": "paid", "paid_at": date.today(), "due_date": yesterday, "voided_at": None},
            {"id": 2, "amount": 250, "currency": "UZS", "status": "due", "paid_at": None, "due_date": yesterday, "voided_at": None},
            {"id": 3, "amount": 400, "currency": "UZS", "status": "due", "paid_at": None, "due_date": tomorrow, "voided_at": None},
            {"id": 4, "amount": 9999, "currency": "UZS", "status": "voided", "paid_at": None, "due_date": yesterday, "voided_at": date.today(), "void_reason": "Duplicate"},
        ]
    )
    assert [item["state"] for item in payload["items"]] == ["paid", "debt", "upcoming", "voided"]
    assert payload["totals"] == {"paid": 100.0, "due": 0.0, "debt": 250.0, "upcoming": 400.0}


def test_migration_adds_versions_and_auditable_void_metadata_without_deleting_data():
    source = Path("database/alembic/versions/0034_customer_support_records.py").read_text()
    upgrade = source.split("def downgrade", 1)[0]
    assert 'down_revision = "0033_broaden_sla_anchor_backfill"' in source
    for field in ("version BIGINT", "voided_at", "voided_by_account_id", "void_reason"):
        assert field in upgrade
    assert "DELETE FROM" not in upgrade


def test_frontend_contract_is_search_first_responsive_and_never_asks_for_internal_student_ids():
    source = Path("frontend/src/workspaces/customer_support/pages/Home.tsx").read_text()
    api = Path("frontend/src/features/customer-support/api.ts").read_text()
    assert "Customer Records" in source
    assert "debouncedQuery" in source and "URLSearchParams" in source
    assert "lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]" in source
    assert "motion-reduce:transition-none" in source
    assert "Search records" in source and "Name, code, phone, Telegram" in source
    assert "Student record ID" not in source
    assert "LinkChildModal" in source
    assert "RoleWorkspaceShell" in source
    assert 'desktopSidebarMode="collapsible"' in source
    assert 'mobileNavigationMode="drawer"' in source
    assert "/payments/${dialog.targetId}/void" in source
    assert 'method: "DELETE"' in api  # unlinking a family link only
    assert "password_hash" not in source
