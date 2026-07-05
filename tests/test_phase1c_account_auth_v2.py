from werkzeug.security import generate_password_hash

from backend.identity import account_auth_v2 as auth_v2


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(self):
        password_hash = generate_password_hash("correct-password")
        self.accounts = {
            "msi00001": {
                "id": 1,
                "login": "MSI00001",
                "password_hash": password_hash,
                "role": "student",
                "status": "active",
                "full_name": "Student User",
                "phone": None,
                "legacy_source_table": "students",
                "legacy_source_id": 101,
            },
            "msi00002": {
                "id": 2,
                "login": "MSI00002",
                "password_hash": password_hash,
                "role": "student",
                "status": "disabled",
                "full_name": "Disabled Student",
                "phone": None,
                "legacy_source_table": "students",
                "legacy_source_id": 102,
            },
            "tch0001": {
                "id": 3,
                "login": "TCH0001",
                "password_hash": password_hash,
                "role": "teacher",
                "status": "active",
                "full_name": "Teacher User",
                "phone": None,
                "legacy_source_table": "teachers",
                "legacy_source_id": 10,
            },
            "admin": {
                "id": 4,
                "login": "admin",
                "password_hash": password_hash,
                "role": "system_admin",
                "status": "active",
                "full_name": "System Admin",
                "phone": None,
                "legacy_source_table": "msi_staff",
                "legacy_source_id": 1,
            },
            "parent-login": {
                "id": 5,
                "login": "parent-login",
                "password_hash": password_hash,
                "role": "parent",
                "status": "pending",
                "full_name": "Pending Parent",
                "phone": None,
                "legacy_source_table": "parents",
                "legacy_source_id": 50,
            },
            "ghost": {
                "id": 6,
                "login": "ghost",
                "password_hash": password_hash,
                "role": "ghost",
                "status": "active",
                "full_name": "Ghost",
                "phone": None,
                "legacy_source_table": "msi_staff",
                "legacy_source_id": 6,
            },
            "missing-profile": {
                "id": 7,
                "login": "missing-profile",
                "password_hash": password_hash,
                "role": "student",
                "status": "active",
                "full_name": "Missing Profile",
                "phone": None,
                "legacy_source_table": "students",
                "legacy_source_id": 107,
            },
        }
        self.student_profiles = {
            1: {
                "profile_id": 11,
                "account_id": 1,
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
            }
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
                "teacher_staff_id": 2,
                "assigned_group": "IGCSE",
            }
        }
        self.parent_profiles = {
            5: {
                "profile_id": 15,
                "account_id": 5,
                "parent_id": 50,
                "telegram_username": "parent_user",
                "profile_status": "pending",
                "full_name": "Pending Parent",
                "telegram_user_id": None,
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
        if "FROM msi_v2.accounts" in sql:
            return _Result(self.accounts.get(auth_v2.normalize_login(params[0])))
        if "FROM msi_v2.student_profiles" in sql:
            return _Result(self.student_profiles.get(int(params[0])))
        if "FROM msi_v2.teacher_profiles" in sql:
            return _Result(self.teacher_profiles.get(int(params[0])))
        if "FROM msi_v2.parent_profiles" in sql:
            return _Result(self.parent_profiles.get(int(params[0])))
        if "FROM msi_v2.staff_profiles" in sql:
            return _Result(self.staff_profiles.get(int(params[0])))
        raise AssertionError(f"Unexpected SQL: {sql}")


def _authenticate(login, password="correct-password"):
    return auth_v2.authenticate_account_password(login, password, conn=_FakeConn())


def test_feature_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("ACCOUNT_AUTH_V2_ENABLED", raising=False)

    assert auth_v2.account_auth_v2_enabled() is False


def test_active_student_authenticates():
    result = _authenticate(" msi00001 ")

    assert result is not None
    assert result["account"]["role"] == "student"
    assert result["session"] == {
        "account_id": 1,
        "account_role": "student",
        "canonical_role": "student",
        "auth_login": "MSI00001",
        "auth_role": "student",
        "student_db_id": 1001,
        "student_id": "MSI00001",
        "student_full_name": "Student User",
        "student_enrollment_id": 321,
        "student_school_code": "sehriyo",
    }


def test_disabled_student_rejected():
    assert _authenticate("MSI00002") is None


def test_active_teacher_tch0001_authenticates():
    result = _authenticate("TCH0001")

    assert result is not None
    assert result["account"]["role"] == "teacher"
    assert result["session"]["auth_role"] == "teacher"
    assert result["session"]["auth_login"] == "TCH0001"
    assert result["session"]["teacher_id"] == 10
    assert result["session"]["teacher_staff_id"] == 2
    assert result["session"]["teacher_full_name"] == "Teacher User"


def test_system_admin_authenticates_with_legacy_admin_compatibility():
    result = _authenticate("admin")

    assert result is not None
    assert result["account"]["role"] == "system_admin"
    assert result["session"]["account_role"] == "system_admin"
    assert result["session"]["canonical_role"] == "system_admin"
    assert result["session"]["auth_role"] == "admin"
    assert result["session"]["staff_role"] == "system_admin"
    assert result["session"]["staff_id"] == 1
    assert result["session"]["admin_id"] == 1
    assert result["session"]["admin_role"] == "owner"
    assert result["session"]["admin_is_owner"] is True


def test_parent_pending_cannot_password_login():
    assert _authenticate("parent-login") is None


def test_unknown_role_rejected():
    assert _authenticate("ghost") is None


def test_missing_profile_rejected():
    assert _authenticate("missing-profile") is None


def test_password_mismatch_rejected():
    assert _authenticate("MSI00001", password="wrong-password") is None
