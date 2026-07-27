"""Architecture guards for independent person modules and reusable domains."""

from __future__ import annotations

import ast
from pathlib import Path

from backend.application.modules import DOMAIN_MODULES
from backend.application.person_modules import PERSON_MODULES
from backend.core.access import (
    Domain,
    ObjectScope,
    PersonType,
    Role,
    SchoolScopeMode,
    actor_context_from_session,
    capabilities_for_role,
)

PEOPLE_ROOT = Path("backend/modules/people")
DOMAINS_ROOT = Path("backend/modules/domains")

EXPECTED_DOMAINS = {
    PersonType.CEO: {
        Domain.IDENTITY,
        Domain.ORGANIZATION,
        Domain.REPORTING,
        Domain.FINANCE,
        Domain.RECRUITMENT,
        Domain.ACADEMICS,
        Domain.TEACHER_RECORDS,
        Domain.COMMUNICATIONS,
        Domain.SUPPORT_CASES,
    },
    PersonType.ACADEMIC_DIRECTOR: {
        Domain.IDENTITY,
        Domain.ORGANIZATION,
        Domain.ACADEMICS,
        Domain.STUDENT_RECORDS,
        Domain.TEACHER_RECORDS,
        Domain.TEACHER_ACADEMY,
        Domain.RECRUITMENT,
        Domain.REPORTING,
        Domain.COMMUNICATIONS,
    },
    PersonType.HEAD_OF_DEPARTMENT: {
        Domain.IDENTITY,
        Domain.ORGANIZATION,
        Domain.ACADEMICS,
        Domain.TEACHER_RECORDS,
        Domain.TEACHER_ACADEMY,
        Domain.RECRUITMENT,
        Domain.REPORTING,
    },
    PersonType.HR_MANAGER: {
        Domain.IDENTITY,
        Domain.RECRUITMENT,
        Domain.REPORTING,
    },
    PersonType.CUSTOMER_SUPPORT: {
        Domain.IDENTITY,
        Domain.ORGANIZATION,
        Domain.STUDENT_RECORDS,
        Domain.PARENT_RELATIONSHIPS,
        Domain.TEACHER_RECORDS,
        Domain.FINANCE,
        Domain.SUPPORT_CASES,
        Domain.COMMUNICATIONS,
        Domain.REPORTING,
    },
    PersonType.TEACHER: {
        Domain.IDENTITY,
        Domain.ORGANIZATION,
        Domain.TEACHER_RECORDS,
        Domain.ACADEMICS,
        Domain.TEACHER_ACADEMY,
        Domain.COMMUNICATIONS,
        Domain.REPORTING,
    },
    PersonType.STUDENT: {
        Domain.IDENTITY,
        Domain.ORGANIZATION,
        Domain.STUDENT_RECORDS,
        Domain.ACADEMICS,
        Domain.COMMUNICATIONS,
        Domain.REPORTING,
    },
    PersonType.PARENT: {
        Domain.IDENTITY,
        Domain.PARENT_RELATIONSHIPS,
        Domain.STUDENT_RECORDS,
        Domain.ACADEMICS,
        Domain.FINANCE,
        Domain.COMMUNICATIONS,
        Domain.SUPPORT_CASES,
        Domain.REPORTING,
    },
}


def _python_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*.py") if "__pycache__" not in path.parts]


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module, tuple(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, ()


def test_every_person_has_one_complete_module_spec():
    assert {module.person_type for module in PERSON_MODULES.modules} == set(PersonType)
    for module in PERSON_MODULES.modules:
        assert module.default_capabilities == capabilities_for_role(module.role)
        assert module.allowed_domains == frozenset(EXPECTED_DOMAINS[module.person_type])
        assert module.workspace_name == module.person_type.value

    assert PERSON_MODULES.for_person(Role.CEO).school_scope_mode is SchoolScopeMode.ALL_SCHOOLS
    assert PERSON_MODULES.for_person(Role.CEO).object_scope is ObjectScope.ORGANIZATION_WIDE
    assert PERSON_MODULES.for_person(Role.STUDENT).object_scope is ObjectScope.OWN_RECORDS
    assert PERSON_MODULES.for_person(Role.PARENT).object_scope is ObjectScope.LINKED_CHILDREN


def test_person_modules_do_not_import_other_people():
    offenders: list[str] = []
    for person_type in PersonType:
        root = PEOPLE_ROOT / person_type.value
        for path in _python_files(root):
            for module_name, _names in _imports(path):
                prefix = "backend.modules.people."
                if not module_name.startswith(prefix):
                    continue
                imported_person = module_name.removeprefix(prefix).split(".", 1)[0]
                if imported_person != person_type.value:
                    offenders.append(f"{path}:{module_name}")
    assert offenders == []


def test_person_modules_use_only_allowed_public_domain_contracts():
    offenders: list[str] = []
    for person_spec in PERSON_MODULES.modules:
        root = PEOPLE_ROOT / person_spec.person_type.value
        for path in _python_files(root):
            for module_name, imported_names in _imports(path):
                prefix = "backend.modules.domains."
                if not module_name.startswith(prefix):
                    continue
                domain_and_tail = module_name.removeprefix(prefix).split(".")
                domain = Domain(domain_and_tail[0])
                is_public_contract = any(
                    part.endswith("contracts") for part in domain_and_tail[1:]
                ) or any(name.endswith("contracts") for name in imported_names)
                if domain not in person_spec.allowed_domains or not is_public_contract:
                    offenders.append(f"{path}:{module_name}")
    assert offenders == []


def test_domains_never_depend_on_people_or_workspaces():
    offenders: list[str] = []
    for path in _python_files(DOMAINS_ROOT):
        for module_name, _names in _imports(path):
            if module_name.startswith("backend.modules.people"):
                offenders.append(f"{path}:{module_name}")
    assert offenders == []


def test_cross_domain_repository_imports_are_rejected():
    offenders: list[str] = []
    for path in _python_files(DOMAINS_ROOT):
        owner_domain = path.relative_to(DOMAINS_ROOT).parts[0]
        for module_name, imported_names in _imports(path):
            prefix = "backend.modules.domains."
            if not module_name.startswith(prefix):
                continue
            domain_and_tail = module_name.removeprefix(prefix).split(".")
            imported_domain = domain_and_tail[0]
            if imported_domain == owner_domain:
                continue
            imports_repository = any("repository" in part for part in domain_and_tail[1:]) or any(
                "repository" in name for name in imported_names
            )
            if imports_repository:
                offenders.append(f"{path}:{module_name}")
    assert offenders == []


def test_all_domains_register_without_application_conditionals():
    assert {module.name for module in DOMAIN_MODULES} == {
        "identity",
        "organization",
        "student_records",
        "parent_relationships",
        "teacher_records",
        "academics",
        "recruitment",
        "teacher_academy",
        "finance",
        "support_cases",
        "communications",
        "reporting",
        "jobs",
    }


def test_role_workspaces_enter_through_their_person_module():
    workspace_people = {
        "ceo",
        "academic_director",
        "head_of_department",
        "customer_support",
        "teacher",
        "student",
        "parent",
        "hr_manager",
    }
    offenders: list[str] = []
    for person_name in workspace_people:
        root = PEOPLE_ROOT / person_name / "workspace"
        for path in _python_files(root):
            for module_name, _names in _imports(path):
                if module_name.startswith("backend.modules.domains."):
                    offenders.append(f"{path}:{module_name}")
                if module_name.startswith("backend.modules.people."):
                    imported_person = module_name.split(".")[3]
                    if imported_person != person_name:
                        offenders.append(f"{path}:{module_name}")
    assert offenders == []


def test_people_and_workspaces_contain_no_sql_or_transaction_commits():
    offenders: list[str] = []
    for path in _python_files(PEOPLE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr in {"execute", "executemany", "commit", "rollback"}:
                offenders.append(f"{path}:{node.lineno}:{node.func.attr}")
    assert offenders == []


def test_actor_scope_combines_person_defaults_with_session_assignments():
    ceo = actor_context_from_session({"auth_role": "ceo"})
    assert ceo.school_scope.all_schools
    assert ceo.can_use_domain(Domain.REPORTING)

    student = actor_context_from_session(
        {
            "auth_role": "student",
            "school_id": "7",
            "subject_ids": "3,5",
            "group_ids": [11, 13],
        }
    )
    assert student.school_scope.allowed_school_ids == frozenset({7})
    assert student.assigned_subject_ids == frozenset({3, 5})
    assert student.assigned_group_ids == frozenset({11, 13})
    assert student.object_scope is ObjectScope.OWN_RECORDS


def test_obsolete_role_and_domain_paths_are_removed():
    obsolete = (
        "identity",
        "organization",
        "academics",
        "hr",
        "teacher_academy",
        "finance",
        "support",
        "communications",
        "reporting",
        "customer_support",
        "people/students",
        "people/parents",
        "people/teachers",
        "people/staff",
    )
    for relative in obsolete:
        assert not (Path("backend/modules") / relative).exists()
    assert not Path("backend/workspaces").exists()
