"""Architecture tests for the focused Customer Support preparation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.core.access.context import ActorContext, SchoolScope
from backend.core.access.domain_types import (
    Capability,
    Domain,
    ObjectScope,
    Role,
    SchoolScopeMode,
)
from backend.modules.domains.reporting.customer_support.contracts import (
    CustomerSupportDashboardFilters,
    CustomerSupportDashboardResponse,
)
from backend.modules.people.customer_support.dashboard.queries import (
    GetCustomerSupportDashboard,
)
from backend.modules.people.customer_support.domain_types import CustomerSupportSection
from backend.modules.people.customer_support.module import (
    CUSTOMER_SUPPORT_CAPABILITIES,
    PERSON_MODULE,
)
from backend.modules.people.customer_support.policies import (
    CustomerSupportAccessError,
)

CUSTOMER_SUPPORT_ROOT = Path("backend/modules/people/customer_support")


def _actor(role: Role) -> ActorContext:
    return ActorContext(
        account_id=11,
        role=role,
        capabilities=frozenset({Capability.VIEW_DASHBOARD}),
        school_scope=SchoolScope(allowed_school_ids=frozenset({7, 9})),
    )


@dataclass
class _DashboardReader:
    received_scope: SchoolScope | None = None

    def get_dashboard(
        self,
        *,
        school_scope: SchoolScope,
        filters: CustomerSupportDashboardFilters | None = None,
    ) -> CustomerSupportDashboardResponse:
        self.received_scope = school_scope
        raise RuntimeError("boundary reached")


def test_each_customer_support_section_has_an_explicit_scope():
    assert {spec.section for spec in CUSTOMER_SUPPORT_CAPABILITIES} == set(CustomerSupportSection)
    for spec in CUSTOMER_SUPPORT_CAPABILITIES:
        assert spec.read_capabilities <= PERSON_MODULE.default_capabilities
        assert spec.write_capabilities <= PERSON_MODULE.default_capabilities
        assert spec.allowed_domains <= PERSON_MODULE.allowed_domains
        assert spec.school_scope_mode is SchoolScopeMode.ASSIGNED_SCHOOLS
        assert spec.object_scope is ObjectScope.SUPPORTED_PEOPLE


def test_customer_support_defaults_cover_new_read_boundaries_without_teacher_mutation():
    assert Domain.REPORTING in PERSON_MODULE.allowed_domains
    assert Domain.TEACHER_RECORDS in PERSON_MODULE.allowed_domains
    assert Capability.VIEW_TEACHER_SUPPORT_INFO in PERSON_MODULE.default_capabilities
    assert Capability.MANAGE_TEACHER_ACCESS not in PERSON_MODULE.default_capabilities


def test_dashboard_orchestration_passes_the_actor_school_scope():
    reader = _DashboardReader()
    query = GetCustomerSupportDashboard(reader)

    with pytest.raises(RuntimeError, match="boundary reached"):
        query(_actor(Role.CUSTOMER_SUPPORT))

    assert reader.received_scope == SchoolScope(allowed_school_ids=frozenset({7, 9}))


def test_dashboard_orchestration_rejects_another_person_before_the_domain_call():
    reader = _DashboardReader()
    query = GetCustomerSupportDashboard(reader)

    with pytest.raises(CustomerSupportAccessError):
        query(_actor(Role.TEACHER))

    assert reader.received_scope is None


def test_focused_person_packages_contain_no_repository_or_sql_dependencies():
    offenders: list[str] = []
    for section in CustomerSupportSection:
        root = CUSTOMER_SUPPORT_ROOT / section.value
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "repository" in node.module:
                        offenders.append(f"{path}:{node.lineno}:{node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "repository" in alias.name:
                            offenders.append(f"{path}:{node.lineno}:{alias.name}")
                elif (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"execute", "executemany", "commit", "rollback"}
                ):
                    offenders.append(f"{path}:{node.lineno}:{node.func.attr}")

    assert offenders == []


def test_each_section_imports_only_its_declared_domains_and_own_package():
    specs = {spec.section: spec for spec in CUSTOMER_SUPPORT_CAPABILITIES}
    offenders: list[str] = []

    for section in CustomerSupportSection:
        root = CUSTOMER_SUPPORT_ROOT / section.value
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules = (node.module,)
                elif isinstance(node, ast.Import):
                    imported_modules = tuple(alias.name for alias in node.names)
                else:
                    continue

                for module_name in imported_modules:
                    domain_prefix = "backend.modules.domains."
                    if module_name.startswith(domain_prefix):
                        imported_domain = Domain(
                            module_name.removeprefix(domain_prefix).split(".", 1)[0]
                        )
                        if imported_domain not in specs[section].allowed_domains:
                            offenders.append(f"{path}:{node.lineno}:{module_name}")

                    person_prefix = "backend.modules.people.customer_support."
                    if module_name.startswith(person_prefix):
                        imported_section = module_name.removeprefix(person_prefix).split(".", 1)[0]
                        top_level_dependencies = {"domain_types", "policies", "scope"}
                        if (
                            imported_section != section.value
                            and imported_section not in top_level_dependencies
                        ):
                            offenders.append(f"{path}:{node.lineno}:{module_name}")

    assert offenders == []
