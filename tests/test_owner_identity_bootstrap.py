from backend.services.identity import bootstrap as storage


class _Cursor:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def execute(self, sql, params=None):
        if "SELECT id, password_hash FROM msi_v2.msi_staff" in sql:
            return _Cursor({"id": 7, "password_hash": "legacy-owner-hash"})
        return _Cursor()


def test_owner_bootstrap_preserves_existing_canonical_password(monkeypatch):
    captured = {}
    monkeypatch.setattr(storage, "OWNER_LOGIN", "admin")
    monkeypatch.setattr(storage, "OWNER_PASSWORD", "bootstrap-secret")
    monkeypatch.setattr(
        storage.identity_repository,
        "find_staff_account_row",
        lambda conn, **kwargs: {
            "id": 42,
            "password_hash": "private-canonical-hash",
            "must_change_password": False,
        },
    )
    monkeypatch.setattr(
        storage,
        "generate_password_hash",
        lambda _password: (_ for _ in ()).throw(
            AssertionError("bootstrap must not replace an existing canonical password")
        ),
    )
    monkeypatch.setattr(
        storage,
        "synchronize_staff_account",
        lambda conn, **values: captured.update(values) or 42,
    )

    storage.ensure_owner_admin(_Connection())

    assert captured["password_hash"] == "private-canonical-hash"
    assert captured["must_change_password"] is False

