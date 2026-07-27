import pytest

from backend.modules.domains.identity import telegram_auth as account_telegram_auth


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(self):
        self.links = {
            9001: {
                "id": 1,
                "account_id": 1,
                "telegram_user_id": 9001,
                "telegram_username": "parent_user",
                "status": "active",
            },
            9002: {
                "id": 2,
                "account_id": 2,
                "telegram_user_id": 9002,
                "telegram_username": "student_user",
                "status": "active",
            },
            9003: {
                "id": 3,
                "account_id": 3,
                "telegram_user_id": 9003,
                "telegram_username": "teacher_user",
                "status": "active",
            },
            9004: {
                "id": 4,
                "account_id": 4,
                "telegram_user_id": 9004,
                "telegram_username": "admin_user",
                "status": "active",
            },
            9005: {
                "id": 5,
                "account_id": 1,
                "telegram_user_id": 9005,
                "telegram_username": "revoked_user",
                "status": "revoked",
            },
            9006: {
                "id": 6,
                "account_id": 6,
                "telegram_user_id": 9006,
                "telegram_username": "disabled_user",
                "status": "active",
            },
            9007: {
                "id": 7,
                "account_id": 7,
                "telegram_user_id": 9007,
                "telegram_username": "missing_profile_user",
                "status": "active",
            },
            9008: {
                "id": 8,
                "account_id": 8,
                "telegram_user_id": 9008,
                "telegram_username": "unknown_role_user",
                "status": "active",
            },
        }
        self.accounts = {
            1: {
                "id": 1,
                "login": None,
                "password_hash": None,
                "role": "parent",
                "status": "active",
                "full_name": "Parent User",
                "phone": None,
                "legacy_source_table": "parents",
                "legacy_source_id": 50,
            },
            2: {
                "id": 2,
                "login": "MSI00001",
                "password_hash": None,
                "role": "student",
                "status": "active",
                "full_name": "Student User",
                "phone": None,
                "legacy_source_table": "students",
                "legacy_source_id": 101,
            },
            3: {
                "id": 3,
                "login": "TCH0001",
                "password_hash": None,
                "role": "teacher",
                "status": "active",
                "full_name": "Teacher User",
                "phone": None,
                "legacy_source_table": "teachers",
                "legacy_source_id": 10,
            },
            4: {
                "id": 4,
                "login": "admin",
                "password_hash": None,
                "role": "system_admin",
                "status": "active",
                "full_name": "System Admin",
                "phone": None,
                "legacy_source_table": "msi_staff",
                "legacy_source_id": 1,
            },
            6: {
                "id": 6,
                "login": "MSI00002",
                "password_hash": None,
                "role": "student",
                "status": "disabled",
                "full_name": "Disabled Student",
                "phone": None,
                "legacy_source_table": "students",
                "legacy_source_id": 102,
            },
            7: {
                "id": 7,
                "login": "MSI00003",
                "password_hash": None,
                "role": "student",
                "status": "active",
                "full_name": "Missing Profile",
                "phone": None,
                "legacy_source_table": "students",
                "legacy_source_id": 103,
            },
            8: {
                "id": 8,
                "login": "ghost",
                "password_hash": None,
                "role": "ghost",
                "status": "active",
                "full_name": "Ghost",
                "phone": None,
                "legacy_source_table": "msi_staff",
                "legacy_source_id": 8,
            },
        }
        self.parent_profiles = {
            1: {
                "profile_id": 11,
                "account_id": 1,
                "parent_id": 50,
                "telegram_username": "parent_user",
                "profile_status": "active",
                "full_name": "Parent User",
                "telegram_user_id": 9001,
            }
        }
        self.student_profiles = {
            2: {
                "profile_id": 12,
                "account_id": 2,
                "student_id": 101,
                "school_id": 5,
                "student_code": "MSI00001",
                "class_id": None,
                "profile_status": "active",
                "legacy_student_row_id": 1001,
                "full_name": "Student User",
                "current_student_code": "MSI00001",
                "school_code": "sehriyo",
                "enrollment_id": 321,
            },
            6: {
                "profile_id": 16,
                "account_id": 6,
                "student_id": 102,
                "school_id": 5,
                "student_code": "MSI00002",
                "class_id": None,
                "profile_status": "active",
                "legacy_student_row_id": 1002,
                "full_name": "Disabled Student",
                "current_student_code": "MSI00002",
                "school_code": "sehriyo",
                "enrollment_id": 322,
            },
        }
        self.teacher_profiles = {
            3: {
                "profile_id": 13,
                "account_id": 3,
                "teacher_id": 10,
                "school_id": None,
                "teacher_code": "TCH0001",
                "legacy_login": "TCH001",
                "profile_status": "active",
                "full_name": "Teacher User",
                "staff_id": 2,
                "assigned_group": "IGCSE",
            }
        }
        self.staff_profiles = {
            4: {
                "profile_id": 14,
                "account_id": 4,
                "staff_id": 1,
                "job_title": "system_admin",
                "department": "system_admin",
                "profile_status": "active",
                "staff_login": "admin",
                "legacy_staff_role": "owner",
                "is_owner": 1,
            }
        }

    def execute(self, sql, params=None):
        params = tuple(params or ())
        if "FROM msi_v2.account_telegram_links" in sql:
            return _Result(self.links.get(int(params[0])))
        if "FROM msi_v2.accounts" in sql:
            return _Result(self.accounts.get(int(params[0])))
        if "FROM msi_v2.student_profiles" in sql:
            return _Result(self.student_profiles.get(int(params[0])))
        if "FROM msi_v2.teacher_profiles" in sql:
            return _Result(self.teacher_profiles.get(int(params[0])))
        if "FROM msi_v2.parent_profiles" in sql:
            return _Result(self.parent_profiles.get(int(params[0])))
        if "FROM msi_v2.staff_profiles" in sql:
            return _Result(self.staff_profiles.get(int(params[0])))
        raise AssertionError(f"Unexpected SQL: {sql}")


def _authenticate(telegram_user_id):
    return account_telegram_auth.authenticate_account_telegram(telegram_user_id, conn=_FakeConn())


def test_previous_account_telegram_auth_import_path_is_gone():
    with pytest.raises(ModuleNotFoundError):
        import backend.identity.account_telegram_auth  # noqa: F401


def test_active_parent_telegram_link_authenticates():
    result = _authenticate(9001)

    assert result is not None
    assert result["account"]["role"] == "parent"
    assert result["session"]["auth_role"] == "parent"
    assert result["session"]["account_id"] == 1
    assert result["session"]["account_role"] == "parent"
    assert result["session"]["canonical_role"] == "parent"
    assert result["session"]["parent_id"] == 50
    assert result["session"]["telegram_user_id"] == 9001


def test_active_student_telegram_link_authenticates():
    result = _authenticate(9002)

    assert result is not None
    assert result["account"]["role"] == "student"
    assert result["session"]["auth_role"] == "student"
    assert result["session"]["auth_login"] == "MSI00001"
    assert result["session"]["student_db_id"] == 101
    assert "student_legacy_row_id" not in result["session"]
    assert result["session"]["student_enrollment_id"] == 321
    assert result["session"]["telegram_user_id"] == 9002


def test_active_teacher_telegram_link_authenticates_to_teacher_workspace():
    result = _authenticate(9003)
    assert result["session"]["auth_role"] == "teacher"
    assert result["session"]["teacher_id"] == 10


def test_removed_system_admin_telegram_link_cannot_authenticate():
    assert _authenticate(9004) is None


def test_revoked_link_rejected():
    assert _authenticate(9005) is None


def test_missing_link_rejected():
    assert _authenticate(9999) is None


def test_disabled_account_rejected():
    assert _authenticate(9006) is None


def test_missing_profile_rejected():
    assert _authenticate(9007) is None


def test_unknown_role_rejected():
    assert _authenticate(9008) is None
