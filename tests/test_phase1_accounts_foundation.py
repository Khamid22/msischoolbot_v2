from pathlib import Path

from scripts.migrate_legacy_identity_to_accounts import (
    build_plan,
    generate_teacher_code_map,
    run_migration,
)


def _sample_rows():
    return {
        "staff_rows": [
            {
                "staff_id": 1,
                "login": "admin",
                "password_hash": "hash-admin",
                "display_name": "Admin",
                "phone": "",
                "telegram_user_id": None,
                "telegram_username": "",
                "role": "owner",
                "status": "active",
                "teacher_id": None,
            },
            {
                "staff_id": 2,
                "login": "oldt001",
                "password_hash": "hash-teacher",
                "display_name": "Teacher",
                "phone": "",
                "telegram_user_id": None,
                "telegram_username": "",
                "role": "teacher",
                "status": "active",
                "teacher_id": 10,
            },
        ],
        "student_rows": [
            {
                "student_db_id": 100,
                "student_code": "MSI00001",
                "full_name": "Student",
                "school_id": 5,
                "telegram_user_id": None,
                "status": "active",
                "legacy_student_row_id": 1000,
                "password_hash": "hash-student",
                "must_change_password": False,
                "last_login_at": None,
            }
        ],
        "teacher_rows": [
            {
                "teacher_id": 10,
                "teacher_name": "Teacher",
                "status": "active",
                "telegram_user_id": None,
                "telegram_username": "",
            }
        ],
        "teacher_staff_rows": [
            {
                "staff_id": 2,
                "old_login": "oldt001",
                "password_hash": "hash-teacher",
                "display_name": "Teacher",
                "phone": "",
                "telegram_user_id": None,
                "telegram_username": "",
                "staff_status": "active",
                "teacher_id": 10,
                "teacher_name": "Teacher",
                "teacher_status": "active",
            }
        ],
        "parent_rows": [
            {
                "parent_id": 50,
                "display_name": "Parent",
                "phone": "",
                "telegram_user_id": 999,
                "telegram_username": "parent_user",
                "status": "active",
            }
        ],
    }


def test_teacher_code_generation_creates_tch0001_format():
    mapping = generate_teacher_code_map(
        [
            {
                "staff_id": 2,
                "teacher_id": 10,
                "teacher_name": "Teacher",
                "old_login": "oldt001",
            }
        ]
    )

    assert mapping[0]["new_teacher_code"] == "TCH0001"
    assert mapping[0]["conflict_status"] == "generated"


def test_migration_dry_run_writes_reports_without_database(tmp_path):
    plan, apply_stats, (md_path, json_path) = run_migration(
        apply=False,
        report_dir=tmp_path,
        rows=_sample_rows(),
    )

    assert apply_stats is None
    assert plan["blocking"] is False
    assert md_path.exists()
    assert json_path.exists()
    assert "Phase 1 Legacy Identity To Accounts Report" in md_path.read_text()


def test_migration_plan_is_idempotent_for_same_input():
    first = build_plan(_sample_rows())
    second = build_plan(_sample_rows())

    first_logins = [row["login"] for row in first["accounts"]]
    second_logins = [row["login"] for row in second["accounts"]]
    assert first_logins == second_logins
    assert first["teacher_code_map"] == second["teacher_code_map"]


def test_parent_accounts_are_telegram_first_without_login_values():
    plan = build_plan(_sample_rows())

    parent_account = next(row for row in plan["accounts"] if row["role"] == "parent")

    assert parent_account["login"] is None
    assert parent_account["status"] == "active"
    assert parent_account["legacy_source_table"] == "parents"
    assert parent_account["legacy_source_id"] == 50
    assert parent_account["telegram_user_id"] == 999


def test_parent_without_telegram_is_pending_without_login_or_link():
    rows = _sample_rows()
    rows["parent_rows"] = [
        {
            "parent_id": 51,
            "display_name": "Parent Pending",
            "phone": "",
            "telegram_user_id": None,
            "telegram_username": "",
            "status": "active",
        }
    ]

    plan = build_plan(rows)
    parent_account = next(row for row in plan["accounts"] if row["role"] == "parent")

    assert parent_account["login"] is None
    assert parent_account["status"] == "pending"
    assert parent_account["legacy_source_table"] == "parents"
    assert parent_account["legacy_source_id"] == 51
    assert parent_account["telegram_user_id"] is None
    assert plan["counts"]["telegram_links"] == 0
    assert plan["validations"]["parents_without_telegram"] == [51]


def test_unknown_staff_role_is_rejected():
    rows = _sample_rows()
    rows["staff_rows"] = [
        {
            "staff_id": 99,
            "login": "ghost",
            "password_hash": "hash",
            "display_name": "Ghost",
            "phone": "",
            "telegram_user_id": None,
            "telegram_username": "",
            "role": "ghost_role",
            "status": "active",
            "teacher_id": None,
        }
    ]
    rows["teacher_staff_rows"] = []
    rows["teacher_rows"] = []
    rows["student_rows"] = []
    rows["parent_rows"] = []

    plan = build_plan(rows)

    assert plan["blocking"] is True
    assert plan["validations"]["invalid_roles"][0]["role"] == "ghost_role"
    assert plan["accounts"] == []


def test_accounts_login_uniqueness_is_declared_in_alembic_migration():
    migration = Path("database/alembic/versions/0003_shared_accounts_foundation.py")
    text = migration.read_text()

    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_login_ci" in text
    assert "lower(btrim(login))" in text
    assert "WHERE login IS NOT NULL" in text
    assert "accounts_login_not_blank_check" in text
    assert "login IS NULL OR btrim(login) <> ''" in text


def test_legacy_source_uniqueness_is_declared_in_alembic_migration():
    migration = Path("database/alembic/versions/0003_shared_accounts_foundation.py")
    text = migration.read_text()

    assert "legacy_source_table TEXT NOT NULL DEFAULT ''" in text
    assert "legacy_source_id BIGINT" in text
    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_legacy_source" in text
    assert "ON msi_v2.accounts (legacy_source_table, legacy_source_id)" in text


def test_parent_telegram_link_uniqueness_is_declared_in_alembic_migration():
    migration = Path("database/alembic/versions/0003_shared_accounts_foundation.py")
    text = migration.read_text()

    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_account_telegram_links_user_id" in text
    assert "ON msi_v2.account_telegram_links (telegram_user_id)" in text


def test_existing_dashboard_application_still_imports_and_starts():
    from backend.server import create_app

    app = create_app()

    assert app.title == "MSI School API"
