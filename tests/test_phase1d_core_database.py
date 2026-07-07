from backend.core import database as core_database
from backend.identity import common as identity_common
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
    legacy_source = Path("database/database.py").read_text()

    assert "def connect_auth_db" in core_source
    assert "class _PostgresConnectionWrapper" in core_source
    assert "from database.database import" not in core_source
    assert "from backend.identity.common import connect" not in core_source
    assert "from backend.core.database import" in legacy_source
    assert "Temporary compatibility wrapper. Delete after" in legacy_source
