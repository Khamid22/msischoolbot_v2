from backend.core import database as core_database
from backend.identity import common as identity_common


def test_core_database_imports():
    assert core_database is not None


def test_core_database_connect_is_callable():
    assert callable(core_database.connect)


def test_legacy_identity_common_connect_still_works():
    assert callable(identity_common.connect)


def test_core_and_legacy_connect_share_callable():
    assert core_database.connect is identity_common.connect
