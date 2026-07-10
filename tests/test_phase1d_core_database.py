from backend.core import database as core_database
from backend.modules.identity import database as identity_common
from pathlib import Path


def test_core_database_imports():
    assert core_database is not None


def test_core_database_connect_is_callable():
    assert callable(core_database.connect)


def test_legacy_identity_common_connect_still_works():
    assert callable(identity_common.connect)


def test_core_and_legacy_connect_share_callable():
    assert core_database.connect is identity_common.connect


def test_core_database_owns_connection_implementation():
    core_source = Path("backend/core/database.py").read_text()
    removed_database_module = Path("database") / "database.py"
    legacy_database_import = "from database." + "database import"

    assert "def connect_auth_db" in core_source
    assert "class _PostgresConnectionWrapper" in core_source
    assert legacy_database_import not in core_source
    assert "from backend.modules.identity.database import connect" not in core_source
    assert not removed_database_module.exists()
