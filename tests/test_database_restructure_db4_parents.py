"""DB-4 parent domain migration coverage."""

from pathlib import Path

import pytest


def test_parent_domain_modules_import_successfully():
    import backend.modules.people.parents.repository as parent_repository
    import backend.modules.people.parents.service as parent_service

    assert callable(parent_repository.link_parent_from_invite)
    assert callable(parent_repository.get_parent_by_telegram_id)
    assert callable(parent_repository.get_parent_child_link)
    assert callable(parent_repository.get_parent_child_link_by_dashboard_id)
    assert callable(parent_repository.list_parent_client_child_rows)
    assert callable(parent_repository.list_invite_parent_rows)
    assert callable(parent_repository.list_parent_subject_indicator_rows)
    assert callable(parent_repository.list_parent_recent_lesson_rows)
    assert callable(parent_repository.insert_parent_invite_row)
    assert callable(parent_repository.consume_parent_invite)
    assert callable(parent_service.link_parent_via_invite)
    assert callable(parent_service.claim_parent_invite_code)
    assert callable(parent_service.create_parent_invite_code)
    assert callable(parent_service.load_parent_invite_code_payload)
    assert callable(parent_service.list_parent_client_children)
    assert callable(parent_service.parent_can_access_dashboard)
    assert callable(parent_service.resolve_parent_child_dashboard)
    assert parent_service.parent_repository is parent_repository


def test_parent_legacy_query_wrappers_are_gone():
    for module_name in (
        "database.queries.parent_account_queries",
        "database.queries.parent_repository",
    ):
        with pytest.raises(ModuleNotFoundError):
            __import__(module_name)


def test_parent_module_is_canonical_and_legacy_facades_are_gone():
    assert not Path("backend/identity/parent_invites.py").exists()
    assert not Path("backend/identity/parent_accounts.py").exists()
    assert not Path("backend/roles/parent/services.py").exists()
    assert not Path("backend/roles/admin/services/parent_service.py").exists()


def test_parent_domain_imports_are_used_where_safe():
    identity_routes_source = Path("backend/modules/identity/page.py").read_text()
    parent_routes_source = Path("backend/workspaces/parent/page.py").read_text()
    admin_parent_routes_source = Path("backend/internal_operations/parent_access_api.py").read_text()
    admin_student_routes_source = Path("backend/internal_operations/student_records_api.py").read_text()
    admin_page_source = Path("backend/internal_operations/page.py").read_text()
    admin_page_service_source = Path("backend/internal_operations/workspace.py").read_text()
    student_payload_source = Path("backend/modules/people/students/payload.py").read_text()

    assert "from backend.modules.people.parents.service import (" in identity_routes_source
    assert "from backend.modules.people.parents.service import (" in parent_routes_source
    assert "from backend.modules.people.parents.service import (" in admin_parent_routes_source
    assert "from backend.modules.people.parents.service import create_parent_invite_code" in admin_student_routes_source
    assert "from backend.modules.people.parents.service import list_linked_parents_for_student" in admin_page_source
    assert "from backend.modules.people.parents.service import list_parent_accounts, list_parent_children" in admin_page_service_source
    assert "from backend.modules.people.parents.service import parent_can_access_dashboard" in student_payload_source
    assert not Path("backend/identity/telegram_links.py").exists()


def test_parent_query_sql_is_owned_by_the_domain():
    source = Path("backend/modules/people/parents/repository.py").read_text()

    assert "def get_parent_child_row" in source
    assert "FROM msi_v2" in source


def test_parent_invite_and_dashboard_logic_live_in_parent_domain():
    parent_service_source = Path("backend/modules/people/parents/service.py").read_text()
    parent_query_source = Path("backend/modules/people/parents/repository.py").read_text()

    assert "def create_parent_invite_code" in parent_service_source
    assert "def claim_parent_invite_code" in parent_service_source
    assert "def load_parent_invite_code_payload" in parent_service_source
    assert "def link_parent_via_invite" in parent_service_source
    assert "def parent_can_access_dashboard" in parent_service_source
    assert "resolve_public_dashboard_for_student_row(student_row_id)" in parent_service_source
    assert "def insert_parent_invite_row" in parent_query_source
    assert "def get_pending_parent_invite_payload" in parent_query_source
    assert "def consume_parent_invite" in parent_query_source
