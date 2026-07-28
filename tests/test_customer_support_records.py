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
from backend.modules.domains.support_cases import (
    customer_records_repository_contracts as repository,
)
from backend.modules.domains.support_cases import customer_records_service as service
from backend.modules.people.customer_support import contracts as public_contracts
from backend.modules.people.customer_support.workspace.api import router

XHR = {"X-Requested-With": "XMLHttpRequest"}


def _session(role: str, *, csrf: str = "support-csrf") -> str:
    secret = (
        os.environ.get("APP_SECRET_KEY", "").strip() or "dev-only-insecure-key-do-not-use-in-prod"
    )
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
        public_contracts,
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
        for method in (getattr(route, "methods", None) or set())
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


def test_duplicate_parent_child_link_is_rejected_without_version_or_audit_mutation(monkeypatch):
    class Connection:
        committed = False

        def commit(self):
            self.committed = True

    conn = Connection()

    @contextmanager
    def opened():
        yield conn

    scope = service.SchoolScope(True, (3,), ({"id": 3},), "")
    monkeypatch.setattr(service, "_connect", opened)
    monkeypatch.setattr(service, "load_scope", lambda connection, actor: scope)
    monkeypatch.setattr(
        repository,
        "get_parent_row",
        lambda connection, parent_id: {"id": parent_id, "version": 4},
    )
    monkeypatch.setattr(
        repository,
        "get_student_row",
        lambda connection, student_id: {
            "id": student_id,
            "school_id": 3,
            "full_name": "Student",
        },
    )
    monkeypatch.setattr(
        repository,
        "insert_parent_student_link",
        lambda connection, **kwargs: False,
    )
    monkeypatch.setattr(
        repository,
        "bump_parent_version",
        lambda *args, **kwargs: pytest.fail("a duplicate link must not bump the parent version"),
    )

    with pytest.raises(service.DuplicateLinkError, match="already linked"):
        service.link_parent_child(
            service.SupportActor(17, 41, "support"),
            7,
            8,
            expected_version=4,
        )
    assert not conn.committed


def test_customer_support_parent_invite_replaces_pending_link(monkeypatch):
    class Connection:
        committed = False

        def commit(self):
            self.committed = True

    conn = Connection()

    @contextmanager
    def opened():
        yield conn

    scope = service.SchoolScope(True, (3,), ({"id": 3},), "")
    invite_call = {}
    monkeypatch.setattr(service, "_connect", opened)
    monkeypatch.setattr(service, "load_scope", lambda connection, actor: scope)
    monkeypatch.setattr(
        repository,
        "get_student_row",
        lambda connection, student_id: {
            "id": student_id,
            "school_id": 3,
            "version": 4,
            "legacy_student_row_id": 77,
        },
    )
    monkeypatch.setattr(
        service,
        "create_parent_invite_contract",
        lambda connection, command: invite_call.update(
            {
                "student_row_id": command.legacy_student_row_id,
                "issued_by": command.issued_by_staff_id,
                "replace_pending": command.replace_pending,
            }
        )
        or type("Invite", (), {"invite_code": "new-code"})(),
    )
    monkeypatch.setattr(service, "_audit", lambda *args, **kwargs: None)

    result = service.create_parent_invite(
        service.SupportActor(17, 41, "support"),
        8,
        expected_version=4,
    )

    assert result == {"inviteCode": "new-code", "studentId": 8}
    assert invite_call == {
        "student_row_id": 77,
        "issued_by": 17,
        "replace_pending": True,
    }
    assert conn.committed


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
            {
                "id": 1,
                "amount": 100,
                "currency": "UZS",
                "status": "paid",
                "paid_at": date.today(),
                "due_date": yesterday,
                "voided_at": None,
            },
            {
                "id": 2,
                "amount": 250,
                "currency": "UZS",
                "status": "due",
                "paid_at": None,
                "due_date": yesterday,
                "voided_at": None,
            },
            {
                "id": 3,
                "amount": 400,
                "currency": "UZS",
                "status": "due",
                "paid_at": None,
                "due_date": tomorrow,
                "voided_at": None,
            },
            {
                "id": 4,
                "amount": 9999,
                "currency": "UZS",
                "status": "voided",
                "paid_at": None,
                "due_date": yesterday,
                "voided_at": date.today(),
                "void_reason": "Duplicate",
            },
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


def test_parent_link_storage_prevents_duplicate_pairs_and_preserves_inactive_history():
    baseline = Path("database/alembic/versions/0001_msi_v2_baseline.sql").read_text()
    customer_support_repository = Path(
        "backend/modules/domains/support_cases/customer_records_repository.py"
    ).read_text()
    parent_repository = Path(
        "backend/modules/domains/parent_relationships/repository.py"
    ).read_text()

    link_table = baseline.split(
        "CREATE TABLE IF NOT EXISTS msi_v2.parent_student_links",
        1,
    )[1].split(");", 1)[0]
    assert "PRIMARY KEY (parent_id, student_id)" in link_table
    assert "WHERE existing_family.status <> 'active'" in customer_support_repository
    assert "RETURNING parent_id" in customer_support_repository
    assert "UPDATE msi_v2.parent_student_links l" in parent_repository
    assert "SET status = 'inactive'" in parent_repository
    assert "DELETE FROM msi_v2.parent_student_links" not in parent_repository


def test_frontend_contract_is_split_search_first_and_strongly_typed():
    entry = Path("frontend/src/workspaces/customer_support/pages/Home.tsx").read_text()
    workspace = Path(
        "frontend/src/features/customer-support/CustomerSupportWorkspace.tsx"
    ).read_text()
    layout = Path("frontend/src/features/customer-support/shared/SupportPageLayout.tsx").read_text()
    records_hook = Path(
        "frontend/src/features/customer-support/shared/useSupportRecords.ts"
    ).read_text()
    students = Path("frontend/src/features/customer-support/students/StudentsPage.tsx").read_text()
    parents = Path("frontend/src/features/customer-support/parents/ParentsPage.tsx").read_text()
    teachers = Path("frontend/src/features/customer-support/teachers/TeachersPage.tsx").read_text()
    teacher_detail = Path(
        "frontend/src/features/customer-support/teachers/TeacherDetail.tsx"
    ).read_text()
    teacher_hook = Path(
        "frontend/src/features/customer-support/teachers/useTeacherDirectory.ts"
    ).read_text()
    student_detail = Path(
        "frontend/src/features/customer-support/students/StudentDetail.tsx"
    ).read_text()
    parent_detail = Path(
        "frontend/src/features/customer-support/parents/ParentDetail.tsx"
    ).read_text()
    link_dialog = Path(
        "frontend/src/features/customer-support/parents/LinkStudentDialog.tsx"
    ).read_text()
    model = Path("frontend/src/features/customer-support/model.ts").read_text()
    api = Path("frontend/src/features/customer-support/api.ts").read_text()
    assert len(entry.splitlines()) < 10
    nav_positions = [
        workspace.index('key: "dashboard"'),
        workspace.index('key: "payments"'),
        workspace.index('key: "parents"'),
        workspace.index('key: "students"'),
        workspace.index('key: "teachers"'),
        workspace.index('key: "tickets"'),
    ]
    assert nav_positions == sorted(nav_positions)
    assert 'desktopSidebarMode="collapsible"' in workspace
    assert 'mobileNavigationMode="drawer"' in workspace
    assert "lg:grid-cols-[minmax(20rem,0.72fr)_minmax(0,1.55fr)]" in layout
    assert "debouncedQuery" in records_hook and "URLSearchParams" in records_hook
    assert "AbortController" in records_hook and "275" in records_hook
    assert 'useSupportRecords("student")' in students
    assert 'fixedSchoolKey: "school5"' not in students
    assert "loadAll: true" not in students
    assert "school.school_key.trim().toLocaleLowerCase() === normalizedKey" in records_hook
    assert "if (fixedSchoolKey && !schoolId) return;" in records_hook
    assert 'limit: loadAll ? "50" : "25"' in records_hook
    assert "do {" in records_hook and "} while (pageCursor)" in records_hook
    assert 'params.set("recordId"' in records_hook
    assert 'params.set("recordType"' not in records_hook
    assert "Student record ID" not in students
    assert "LinkStudentDialog" in parents and 'status: "active"' in link_dialog
    assert "useInfiniteQuery" in teacher_hook
    assert "listSupportTeachers" in teacher_hook
    assert "Read-only support view" in teacher_detail
    assert "mutation" not in teachers.casefold()
    assert "excludeParentId: String(parentId)" in link_dialog
    assert "} while (cursor);" in link_dialog
    assert "excludedIds" not in link_dialog
    assert "/payments/students/${detail.profile.id}/" in students
    assert "paid-invoices" in students
    assert "Mark unpaid" not in students
    assert "Replace the pending invitation?" in students
    assert "Parent invitations" in student_detail
    assert "/customer-support/parents?recordId=" in student_detail
    assert 'title="Family"' in parent_detail
    assert "/customer-support/students?recordId=" in parent_detail
    for type_name in (
        "SupportSchool",
        "SupportRecordSummary",
        "StudentProfile",
        "ParentProfile",
        "StudentEnrollment",
        "ParentStudentLink",
        "StudentParentLink",
        "ParentInviteSummary",
        "PaymentRecord",
        "PaymentTotals",
        "SupportAuditEvent",
        "StudentDetail",
        "ParentDetail",
        "SupportContext",
    ):
        assert f"type {type_name}" in model
    assert 'method: "DELETE"' in api  # unlinking a family link only
    assert "password_hash" not in "\n".join((students, parents, model))


@pytest.mark.parametrize(
    ("path", "view", "title"),
    [
        ("/customer-support/dashboard", "dashboard", "Customer Support Dashboard"),
        ("/customer-support/payments", "payments", "Payments Workspace"),
        ("/customer-support/parents", "parents", "Parents"),
        ("/customer-support/students", "students", "Students"),
        ("/customer-support/teachers", "teachers", "Teachers"),
        ("/customer-support/tickets", "tickets", "Support Tickets"),
    ],
)
def test_customer_support_page_routes_render_the_requested_view(client, path, view, title):
    client.cookies.set("session", _session("customer_support"))
    response = client.get(path)
    assert response.status_code == 200
    assert 'data-react-page="customer-support-home"' in response.text
    assert title in response.text
    assert f'"view":"{view}"' in response.text


@pytest.mark.parametrize("path", ["/customer-support", "/support"])
def test_customer_support_legacy_roots_redirect_to_dashboard(client, path):
    client.cookies.set("session", _session("customer_support"))
    response = client.get(path)
    assert response.status_code == 308
    assert response.headers["location"] == "/customer-support/dashboard"
