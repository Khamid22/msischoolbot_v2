"""enforce canonical LMS identity and academic integrity

Revision ID: 0007_lms_integrity
Revises: 0006_secure_parent_invites
Create Date: 2026-07-10
"""

from alembic import op


revision = "0007_lms_integrity"
down_revision = "0006_secure_parent_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- One historical local slot had its UTC/local end instant reversed.
        -- It is already in the past, so repair the interval and retire it.
        UPDATE msi_v2.office_hour_slots
        SET ends_at = starts_at + (slot_minutes * interval '1 minute'),
            status = 'cancelled'
        WHERE ends_at <= starts_at;

        ALTER TABLE msi_v2.account_invites
        DROP CONSTRAINT IF EXISTS account_invites_type_check;
        ALTER TABLE msi_v2.account_invites
        ADD CONSTRAINT account_invites_type_check
        CHECK (invite_type IN ('parent'));

        ALTER TABLE msi_v2.account_invites
        DROP CONSTRAINT IF EXISTS account_invites_status_check;
        ALTER TABLE msi_v2.account_invites
        ADD CONSTRAINT account_invites_status_check
        CHECK (status IN ('pending', 'consumed', 'expired', 'revoked'));

        ALTER TABLE msi_v2.account_invites
        DROP CONSTRAINT IF EXISTS account_invites_parent_single_use_check;
        ALTER TABLE msi_v2.account_invites
        ADD CONSTRAINT account_invites_parent_single_use_check
        CHECK (invite_type <> 'parent' OR max_uses = 1);

        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_must_change_has_credentials_check;
        ALTER TABLE msi_v2.accounts
        ADD CONSTRAINT accounts_must_change_has_credentials_check
        CHECK (
            must_change_password IS FALSE
            OR (login IS NOT NULL AND password_hash IS NOT NULL)
        );

        ALTER TABLE msi_v2.accounts
        DROP CONSTRAINT IF EXISTS accounts_active_password_role_credentials_check;
        ALTER TABLE msi_v2.accounts
        ADD CONSTRAINT accounts_active_password_role_credentials_check
        CHECK (
            status <> 'active'
            OR role = 'parent'
            OR (login IS NOT NULL AND password_hash IS NOT NULL)
        );

        ALTER TABLE msi_v2.office_hour_slots
        DROP CONSTRAINT IF EXISTS office_hour_slots_interval_check;
        ALTER TABLE msi_v2.office_hour_slots
        ADD CONSTRAINT office_hour_slots_interval_check
        CHECK (ends_at > starts_at AND slot_minutes BETWEEN 5 AND 180 AND capacity BETWEEN 1 AND 50);

        ALTER TABLE msi_v2.office_hour_slots
        DROP CONSTRAINT IF EXISTS office_hour_slots_status_check;
        ALTER TABLE msi_v2.office_hour_slots
        ADD CONSTRAINT office_hour_slots_status_check
        CHECK (status IN ('open', 'cancelled'));

        ALTER TABLE msi_v2.office_hour_bookings
        DROP CONSTRAINT IF EXISTS office_hour_bookings_status_check;
        ALTER TABLE msi_v2.office_hour_bookings
        ADD CONSTRAINT office_hour_bookings_status_check
        CHECK (status IN ('booked', 'cancelled', 'completed', 'no_show'));

        CREATE UNIQUE INDEX IF NOT EXISTS idx_office_hour_bookings_active_student
        ON msi_v2.office_hour_bookings (slot_id, student_id)
        WHERE status = 'booked';

        CREATE UNIQUE INDEX IF NOT EXISTS idx_group_students_legacy_enrollment
        ON msi_v2.group_students (legacy_enrollment_id)
        WHERE legacy_enrollment_id IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_group_students_legacy_dashboard
        ON msi_v2.group_students (legacy_public_dashboard_id)
        WHERE legacy_public_dashboard_id IS NOT NULL;

        ALTER TABLE msi_v2.attendance_records
        ALTER COLUMN lesson_session_id SET NOT NULL,
        ALTER COLUMN group_id SET NOT NULL,
        ALTER COLUMN student_id SET NOT NULL;

        ALTER TABLE msi_v2.attendance_records
        DROP CONSTRAINT IF EXISTS attendance_records_status_check;
        ALTER TABLE msi_v2.attendance_records
        ADD CONSTRAINT attendance_records_status_check
        CHECK (attendance_status IN ('present', 'absent', 'justified'));

        ALTER TABLE msi_v2.homework_scores
        ALTER COLUMN lesson_session_id SET NOT NULL,
        ALTER COLUMN group_id SET NOT NULL,
        ALTER COLUMN student_id SET NOT NULL;

        ALTER TABLE msi_v2.homework_scores
        DROP CONSTRAINT IF EXISTS homework_scores_scale_check;
        ALTER TABLE msi_v2.homework_scores
        ADD CONSTRAINT homework_scores_scale_check
        CHECK (score_scale > 0 AND score >= 0 AND score <= score_scale);

        ALTER TABLE msi_v2.exam_results
        DROP CONSTRAINT IF EXISTS exam_results_scale_check;
        ALTER TABLE msi_v2.exam_results
        ADD CONSTRAINT exam_results_scale_check
        CHECK (score_scale > 0 AND score >= 0 AND score <= score_scale);

        ALTER TABLE msi_v2.coin_events
        DROP CONSTRAINT IF EXISTS coin_events_nonzero_check;
        ALTER TABLE msi_v2.coin_events
        ADD CONSTRAINT coin_events_nonzero_check
        CHECK (amount <> 0);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.coin_events DROP CONSTRAINT IF EXISTS coin_events_nonzero_check;
        ALTER TABLE msi_v2.exam_results DROP CONSTRAINT IF EXISTS exam_results_scale_check;
        ALTER TABLE msi_v2.homework_scores DROP CONSTRAINT IF EXISTS homework_scores_scale_check;
        ALTER TABLE msi_v2.attendance_records DROP CONSTRAINT IF EXISTS attendance_records_status_check;
        ALTER TABLE msi_v2.homework_scores
            ALTER COLUMN lesson_session_id DROP NOT NULL,
            ALTER COLUMN group_id DROP NOT NULL,
            ALTER COLUMN student_id DROP NOT NULL;
        ALTER TABLE msi_v2.attendance_records
            ALTER COLUMN lesson_session_id DROP NOT NULL,
            ALTER COLUMN group_id DROP NOT NULL,
            ALTER COLUMN student_id DROP NOT NULL;
        DROP INDEX IF EXISTS msi_v2.idx_group_students_legacy_dashboard;
        DROP INDEX IF EXISTS msi_v2.idx_group_students_legacy_enrollment;
        DROP INDEX IF EXISTS msi_v2.idx_office_hour_bookings_active_student;
        ALTER TABLE msi_v2.office_hour_bookings DROP CONSTRAINT IF EXISTS office_hour_bookings_status_check;
        ALTER TABLE msi_v2.office_hour_slots DROP CONSTRAINT IF EXISTS office_hour_slots_status_check;
        ALTER TABLE msi_v2.office_hour_slots DROP CONSTRAINT IF EXISTS office_hour_slots_interval_check;
        ALTER TABLE msi_v2.accounts DROP CONSTRAINT IF EXISTS accounts_active_password_role_credentials_check;
        ALTER TABLE msi_v2.accounts DROP CONSTRAINT IF EXISTS accounts_must_change_has_credentials_check;
        ALTER TABLE msi_v2.account_invites DROP CONSTRAINT IF EXISTS account_invites_parent_single_use_check;
        ALTER TABLE msi_v2.account_invites DROP CONSTRAINT IF EXISTS account_invites_status_check;
        ALTER TABLE msi_v2.account_invites DROP CONSTRAINT IF EXISTS account_invites_type_check;
        """
    )
