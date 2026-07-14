"""Payment repository regression tests for canonical student foreign keys."""

from backend.modules.finance import repository


class _Result:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []
        self.rowcount = 1

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _FakeConnection:
    def __init__(self):
        self.insert_params = None

    def execute(self, sql, params=None):
        params = tuple(params or ())
        if "SELECT id" in sql and "legacy_student_row_id" in sql and "group_students" not in sql:
            assert params == (9_000_123_456,)
            return _Result({"id": 42})
        if "SELECT gs.group_id" in sql:
            assert params == (9_000_123_456, "IGCSE Mathematics A")
            return _Result({"group_id": 7})
        if "INSERT INTO msi_v2.payments" in sql:
            self.insert_params = params
            return _Result({"id": 11})
        if "FROM msi_v2.payments p" in sql and "WHERE p.id" in sql:
            return _Result(
                {
                    "id": 11,
                    "student_row_id": 9_000_123_456,
                    "subject": "IGCSE Mathematics A",
                }
            )
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_payment_insert_converts_public_student_row_id_to_internal_foreign_key():
    conn = _FakeConnection()

    row = repository.insert_student_payment_row(
        conn,
        student_row_id=9_000_123_456,
        subject="IGCSE Mathematics A",
        month_label="2026-07",
        amount=100,
        currency="UZS",
        status="due",
        due_date="2026-07-15",
        paid_at="",
        notes="",
        created_by_admin_id=3,
        created_at="2026-07-10T00:00:00Z",
        updated_at="2026-07-10T00:00:00Z",
    )

    assert row["student_row_id"] == 9_000_123_456
    assert conn.insert_params is not None
    assert conn.insert_params[0] == 42
    assert conn.insert_params[1] == 7
    assert 9_000_123_456 not in conn.insert_params


def test_payment_select_resolves_legacy_id_through_students_join():
    source = repository._payment_select()

    assert "st.legacy_student_row_id AS student_row_id" in source
    assert "student_id AS student_row_id" not in source

