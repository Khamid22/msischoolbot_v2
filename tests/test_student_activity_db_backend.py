import unittest

from app.routes.students.services import auth_service


class StudentActivityDbBackendTests(unittest.TestCase):
    def test_sqlite_busy_timeout_is_not_applied_to_postgres_connections(self):
        class FakePostgresConnection:
            db_backend = "postgres"

        self.assertFalse(auth_service._is_sqlite_connection(FakePostgresConnection()))

    def test_sqlite_busy_timeout_is_applied_to_sqlite_connections(self):
        class FakeSqliteConnection:
            db_backend = "sqlite"

        self.assertTrue(auth_service._is_sqlite_connection(FakeSqliteConnection()))


if __name__ == "__main__":
    unittest.main()
