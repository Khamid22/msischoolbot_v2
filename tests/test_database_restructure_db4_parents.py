"""DB-4 parent domain migration coverage."""

from pathlib import Path


def test_parent_domain_modules_import_successfully():
    import backend.domains.parents.queries as parent_queries
    import backend.domains.parents.service as parent_service

    assert callable(parent_queries.link_parent_from_invite)
    assert callable(parent_queries.get_parent_by_telegram_id)
    assert callable(parent_queries.get_parent_child_link)
    assert callable(parent_queries.get_parent_child_link_by_dashboard_id)
    assert callable(parent_queries.list_parent_client_child_rows)
    assert callable(parent_queries.list_invite_parent_rows)
    assert callable(parent_queries.list_parent_subject_indicator_rows)
    assert callable(parent_queries.list_parent_recent_lesson_rows)
    assert callable(parent_queries.insert_parent_invite_row)
    assert callable(parent_service.link_parent_via_invite)
    assert callable(parent_service.create_parent_invite_code)
    assert callable(parent_service.load_parent_invite_payload)
    assert callable(parent_service.list_parent_client_children)
    assert callable(parent_service.parent_can_access_dashboard)
    assert callable(parent_service.resolve_parent_child_dashboard)
    assert parent_service.parent_queries is parent_queries


def test_parent_legacy_query_wrappers_still_export_domain_functions():
    import backend.domains.parents.queries as parent_queries
    import database.queries.parent_account_queries as legacy_account_queries
    import database.queries.parent_queries as legacy_parent_queries

    assert legacy_account_queries.link_parent_from_invite is parent_queries.link_parent_from_invite
    assert legacy_account_queries.get_parent_by_telegram_id is parent_queries.get_parent_by_telegram_id
    assert legacy_account_queries.list_parent_client_child_rows is parent_queries.list_parent_client_child_rows
    assert legacy_parent_queries.list_parent_subject_indicator_rows is parent_queries.list_parent_subject_indicator_rows
    assert legacy_parent_queries.list_parent_recent_lesson_rows is parent_queries.list_parent_recent_lesson_rows
    assert legacy_parent_queries.get_parent_child_row is parent_queries.get_parent_child_row


def test_parent_identity_and_admin_wrappers_still_export_domain_services():
    import backend.domains.parents.service as parent_service
    import backend.identity.parent_accounts as legacy_parent_accounts
    import backend.identity.parent_invites as legacy_parent_invites
    import backend.roles.admin.services.parent_service as legacy_admin_parent_service
    import backend.roles.parent.services as legacy_parent_role_service

    assert legacy_parent_accounts.link_parent_via_invite is parent_service.link_parent_via_invite
    assert legacy_parent_accounts.parent_children is parent_service.parent_children
    assert legacy_parent_invites.create_parent_invite_code is parent_service.create_parent_invite_code
    assert legacy_parent_invites.load_parent_invite_code_payload is parent_service.load_parent_invite_code_payload
    assert legacy_admin_parent_service.list_parent_accounts is parent_service.list_parent_accounts
    assert legacy_admin_parent_service.assign_parent_child is parent_service.assign_parent_child
    assert legacy_parent_role_service.list_parent_client_children is parent_service.list_parent_client_children
    assert legacy_parent_role_service.parent_can_access_student is parent_service.parent_can_access_student


def test_parent_domain_imports_are_used_where_safe():
    identity_routes_source = Path("backend/domains/identity/routes.py").read_text()
    parent_routes_source = Path("backend/pages/parent.py").read_text()
    admin_parent_routes_source = Path("backend/api/v1/admin/parents.py").read_text()
    admin_student_routes_source = Path("backend/api/v1/admin/students.py").read_text()
    admin_page_source = Path("backend/roles/admin/routes/admin_page.py").read_text()
    admin_page_service_source = Path("backend/roles/admin/services/page_service.py").read_text()
    student_payload_source = Path("backend/roles/student/services/payload_service.py").read_text()
    telegram_links_source = Path("backend/identity/telegram_links.py").read_text()

    assert "from backend.domains.parents.service import (" in identity_routes_source
    assert "from backend.domains.parents.service import (" in parent_routes_source
    assert "from backend.domains.parents.service import (" in admin_parent_routes_source
    assert "from backend.domains.parents.service import create_parent_invite_code" in admin_student_routes_source
    assert "from backend.domains.parents.service import list_linked_parents_for_student" in admin_page_source
    assert "from backend.domains.parents.service import list_parent_accounts, list_parent_children" in admin_page_service_source
    assert "from backend.domains.parents.service import parent_can_access_dashboard" in student_payload_source
    assert "from backend.domains.parents import queries as parent_queries" in telegram_links_source


def test_parent_legacy_files_are_only_compatibility_wrappers():
    wrapper_paths = [
        "database/queries/parent_account_queries.py",
        "database/queries/parent_queries.py",
        "backend/identity/parent_accounts.py",
        "backend/identity/parent_invites.py",
        "backend/roles/admin/services/parent_service.py",
        "backend/roles/parent/services.py",
    ]
    for path in wrapper_paths:
        source = Path(path).read_text()
        assert "backend.domains.parents" in source
        assert "FROM msi_v2" not in source
        assert "JOIN msi_v2" not in source
        assert "UPDATE msi_v2" not in source
        assert "INSERT INTO msi_v2" not in source
        assert "DELETE FROM msi_v2" not in source


def test_parent_invite_and_dashboard_logic_live_in_parent_domain():
    parent_service_source = Path("backend/domains/parents/service.py").read_text()
    parent_query_source = Path("backend/domains/parents/queries.py").read_text()

    assert "def create_parent_invite_code" in parent_service_source
    assert "def load_parent_invite_code_payload" in parent_service_source
    assert "def link_parent_via_invite" in parent_service_source
    assert "def parent_can_access_dashboard" in parent_service_source
    assert "resolve_public_dashboard_for_student_row(student_row_id)" in parent_service_source
    assert "def insert_parent_invite_row" in parent_query_source
    assert "def get_pending_parent_invite_token" in parent_query_source
