"""Guard the role-based architecture against restoring System Admin."""

from pathlib import Path

from backend.core.access.roles import (
    ALL_ROLES,
    dashboard_path_for_role,
    normalize_role,
)


REMOVED_ROLES = {"admin", "system_admin", "owner"}
REMOVED_ROUTE_PREFIXES = ("/admin", "/api/v1/admin", "/internal/operations")


def test_removed_roles_are_not_valid_or_routable():
    assert REMOVED_ROLES.isdisjoint(ALL_ROLES)
    for role in REMOVED_ROLES:
        assert normalize_role(role) == ""
        assert dashboard_path_for_role(role) == "/"


def test_internal_operations_source_trees_are_deleted():
    assert not Path("backend/internal_operations").exists()
    assert not Path("frontend/src/internal_operations").exists()
    assert not Path("frontend/src/shared/ui/AdminEmbedLayout.tsx").exists()


def test_removed_admin_routes_are_not_registered(app):
    paths = {
        str(getattr(route, "path", "") or "")
        for route in app.routes
    }
    assert not any(
        path == prefix or path.startswith(f"{prefix}/")
        for path in paths
        for prefix in REMOVED_ROUTE_PREFIXES
    )


def test_removal_migration_retires_legacy_accounts_and_closes_role_constraint():
    source = Path(
        "database/alembic/versions/0028_remove_system_admin.py"
    ).read_text(encoding="utf-8")

    assert "role = 'retired'" in source
    assert "password_hash = NULL" in source
    assert "account_telegram_links" in source
    upgrade_source = source.split("def downgrade", 1)[0]
    role_constraint = upgrade_source.rsplit(
        "ADD CONSTRAINT accounts_role_check",
        1,
    )[-1]
    assert "'system_admin'" not in role_constraint
