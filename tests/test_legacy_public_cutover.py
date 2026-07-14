from pathlib import Path


MIGRATION = Path(
    "database/alembic/versions/0015_legacy_public_cutover.py"
)


def test_legacy_cutover_follows_hr_decision_queue_and_preserves_source_tables():
    source = MIGRATION.read_text()

    assert 'revision = "0015_legacy_public_cutover"' in source
    assert 'down_revision = "0014_hr_decision_queue"' in source
    assert "DROP TABLE" not in source
    assert "ALTER TABLE public." not in source
    assert "legacy_tables_preserved" in source


def test_legacy_cutover_imports_every_login_authority_and_retained_dataset():
    source = MIGRATION.read_text()

    for table_name in (
        "public.admins",
        "public.students",
        "public.student_auth",
        "public.teachers",
        "public.resources",
        "public.chat_messages",
    ):
        assert table_name in source

    assert "generate_password_hash(code)" in source
    assert "must_change_password = false" in source
    assert "legacy_public.cutover" in source


def test_legacy_cutover_downgrade_requires_restoring_the_backup():
    source = MIGRATION.read_text()

    assert "intentionally irreversible" in source
    assert "pre-cutover database backup" in source
