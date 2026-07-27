"""Customer Support read-only teacher orchestration and API tests."""

from __future__ import annotations

import json
import os
from base64 import b64encode

from itsdangerous import TimestampSigner

from backend.core.access.capabilities import capabilities_for_role
from backend.core.access.context import ActorContext, SchoolScope
from backend.core.access.domain_types import Role
from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.identity.contracts import StaffSchoolScopeAssignment
from backend.modules.domains.organization.contracts import SchoolReference
from backend.modules.domains.teacher_records.support_contracts import (
    TeacherSupportProfile,
    TeacherSupportProfilePage,
)
from backend.modules.people.customer_support import scope as scope_module
from backend.modules.people.customer_support.domain_types import DirectoryStatus
from backend.modules.people.customer_support.scope import (
    CustomerSupportScopeResolver,
)
from backend.modules.people.customer_support.teachers.queries import (
    CustomerSupportTeacherQueries,
    TeacherDetailResult,
    TeacherDirectoryItem,
    TeacherDirectoryPage,
    TeacherDirectoryQuery,
)
from backend.modules.people.customer_support.workspace.teachers_api import (
    get_teacher_queries,
)
from backend.modules.people.customer_support.workspace.teachers_api import (
    router as teacher_router,
)

XHR = {"X-Requested-With": "XMLHttpRequest"}


def _session(role: str) -> str:
    secret = (
        os.environ.get("APP_SECRET_KEY", "").strip() or "dev-only-insecure-key-do-not-use-in-prod"
    )
    payload = {
        "auth_role": role,
        "auth_login": f"{role}@test",
        "account_id": 41,
        "staff_id": 17,
    }
    return TimestampSigner(secret).sign(b64encode(json.dumps(payload).encode())).decode()


def _actor() -> ActorContext:
    return ActorContext(
        account_id=41,
        staff_id=17,
        role=Role.CUSTOMER_SUPPORT,
        capabilities=capabilities_for_role(Role.CUSTOMER_SUPPORT),
        school_scope=SchoolScope(),
    )


def _profile() -> TeacherSupportProfile:
    return TeacherSupportProfile(
        teacher_id=12,
        full_name="Ada Teacher",
        login="TCH0012",
        phone="+998900000000",
        telegram_username="ada_teacher",
        account_status="active",
        school_ids=(7,),
        school_names=("North School",),
        subject_names=("Mathematics",),
        assigned_group_ids=(31, 32),
        assigned_group_names=("Math A", "Math B"),
    )


class _ScopeResolver:
    def resolve(self, actor: ActorContext) -> ActorContext:
        return ActorContext(
            **{
                **actor.__dict__,
                "school_scope": SchoolScope(allowed_school_ids=frozenset({7})),
            }
        )


class _Reader:
    received_scope: SchoolScope | None = None

    def search_teachers(self, *, school_scope: SchoolScope, **kwargs):
        self.received_scope = school_scope
        return TeacherSupportProfilePage(items=(_profile(),), next_cursor="next")

    def get_teacher(self, *, school_scope: SchoolScope, teacher_id: int):
        self.received_scope = school_scope
        assert teacher_id == 12
        return _profile()


def test_person_query_maps_domain_profile_without_teacher_mutations():
    reader = _Reader()
    queries = CustomerSupportTeacherQueries(
        reader=reader,
        scope_resolver=_ScopeResolver(),  # type: ignore[arg-type]
    )

    page = queries.list_teachers(
        _actor(),
        TeacherDirectoryQuery(status=DirectoryStatus.ACTIVE),
    )
    detail = queries.get_teacher(_actor(), 12)

    assert reader.received_scope == SchoolScope(allowed_school_ids=frozenset({7}))
    assert page.items[0].assigned_group_count == 2
    assert detail.assigned_group_names == ("Math A", "Math B")


class _ScopeConnection:
    def __init__(self) -> None:
        self.rollbacks = 0
        self.closes = 0

    def execute(self, sql: str, params: object = None):
        assert sql == "SET TRANSACTION READ ONLY"
        return None

    def commit(self) -> None:
        raise AssertionError("Scope resolution must never commit.")

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


def test_scope_resolver_uses_typed_identity_and_school_contracts(monkeypatch):
    connection = _ScopeConnection()
    monkeypatch.setattr(
        scope_module,
        "get_staff_school_scope_assignment",
        lambda conn, **kwargs: StaffSchoolScopeAssignment(
            staff_id=17,
            raw_scope="north, 3",
        ),
    )
    monkeypatch.setattr(
        scope_module,
        "list_school_references",
        lambda conn: (
            SchoolReference(school_id=1, code="north", name="North School"),
            SchoolReference(school_id=2, code="south", name="South School"),
            SchoolReference(school_id=3, code="central", name="Central School"),
        ),
    )

    scoped_actor = CustomerSupportScopeResolver(UnitOfWorkFactory(lambda: connection)).resolve(
        _actor()
    )

    assert not scoped_actor.school_scope.all_schools
    assert scoped_actor.school_scope.allowed_school_ids == frozenset({1, 3})
    assert connection.rollbacks == 1
    assert connection.closes == 1


class _ApiQueries:
    def list_teachers(self, actor: ActorContext, query: TeacherDirectoryQuery):
        assert actor.role is Role.CUSTOMER_SUPPORT
        assert query.search_text == "Ada"
        return TeacherDirectoryPage(
            items=(
                TeacherDirectoryItem(
                    teacher_id=12,
                    full_name="Ada Teacher",
                    login="TCH0012",
                    phone="+998900000000",
                    telegram_username="ada_teacher",
                    account_status="active",
                    school_ids=(7,),
                    school_names=("North School",),
                    subject_names=("Mathematics",),
                    assigned_group_count=2,
                ),
            ),
            next_cursor=None,
        )

    def get_teacher(self, actor: ActorContext, teacher_id: int):
        page = self.list_teachers(actor, TeacherDirectoryQuery(search_text="Ada"))
        return TeacherDetailResult(
            teacher=page.items[0],
            assigned_group_names=("Math A", "Math B"),
        )


def test_teacher_api_is_camel_case_read_only_and_role_isolated(app, client):
    app.dependency_overrides[get_teacher_queries] = lambda: _ApiQueries()
    try:
        client.cookies.set("session", _session("customer_support"))
        listing = client.get(
            "/api/v1/customer-support/teachers?q=Ada",
            headers=XHR,
        )
        assert listing.status_code == 200
        assert listing.json()["data"]["items"][0] == {
            "teacherId": 12,
            "fullName": "Ada Teacher",
            "login": "TCH0012",
            "phone": "+998900000000",
            "telegramUsername": "ada_teacher",
            "accountStatus": "active",
            "schoolIds": [7],
            "schoolNames": ["North School"],
            "subjectNames": ["Mathematics"],
            "assignedGroupCount": 2,
        }

        detail = client.get(
            "/api/v1/customer-support/teachers/12",
            headers=XHR,
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["assignedGroupNames"] == ["Math A", "Math B"]

        client.cookies.set("session", _session("teacher"))
        denied = client.get("/api/v1/customer-support/teachers", headers=XHR)
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.pop(get_teacher_queries, None)


def test_teacher_transport_exposes_only_get_routes():
    methods = {
        method
        for route in teacher_router.routes
        for method in (getattr(route, "methods", None) or set())
    }
    assert methods == {"GET"}
