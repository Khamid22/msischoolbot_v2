"""add HR-managed recruitment sources and rejection reasons

Revision ID: 0016_recruitment_settings
Revises: 0015_legacy_public_cutover
Create Date: 2026-07-15
"""

from alembic import op


revision = "0016_recruitment_settings"
down_revision = "0015_legacy_public_cutover"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS msi_v2.teacher_recruitment_settings (
            id BIGSERIAL PRIMARY KEY,
            category TEXT NOT NULL,
            value TEXT NOT NULL,
            label TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_recruitment_settings_category_check CHECK (
                category IN ('source', 'rejection_reason')
            ),
            CONSTRAINT teacher_recruitment_settings_value_check CHECK (length(btrim(value)) > 0),
            CONSTRAINT teacher_recruitment_settings_label_check CHECK (length(btrim(label)) > 0),
            CONSTRAINT teacher_recruitment_settings_category_value_unique UNIQUE (category, value)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_label_ci
        ON msi_v2.teacher_recruitment_settings (category, lower(label));

        CREATE INDEX IF NOT EXISTS idx_teacher_recruitment_settings_active_order
        ON msi_v2.teacher_recruitment_settings (category, is_active, sort_order, lower(label));

        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, sort_order
        ) VALUES
            ('source', 'hh.uz', 'hh.uz', 10),
            ('source', 'Telegram', 'Telegram', 20),
            ('source', 'Referral', 'Referral', 30),
            ('source', 'Instagram', 'Instagram', 40),
            ('source', 'LinkedIn', 'LinkedIn', 50),
            ('source', 'University', 'University', 60),
            ('source', 'MSI website', 'MSI website', 70),
            ('source', 'Other', 'Other', 80),
            ('rejection_reason', 'insufficient_subject_knowledge', 'Insufficient subject knowledge', 10),
            ('rejection_reason', 'insufficient_english_level', 'Insufficient English level', 20),
            ('rejection_reason', 'weak_demo_lesson', 'Weak demo lesson', 30),
            ('rejection_reason', 'schedule_incompatibility', 'Schedule incompatibility', 40),
            ('rejection_reason', 'salary_expectation_incompatibility', 'Salary expectation incompatibility', 50),
            ('rejection_reason', 'insufficient_experience', 'Insufficient experience', 60),
            ('rejection_reason', 'unprofessional_behaviour', 'Unprofessional behaviour', 70),
            ('rejection_reason', 'missing_or_invalid_documents', 'Missing or invalid documents', 80),
            ('rejection_reason', 'candidate_did_not_attend', 'Candidate did not attend', 90),
            ('rejection_reason', 'position_already_filled', 'Position already filled', 100),
            ('rejection_reason', 'other', 'Other', 110)
        ON CONFLICT (category, value) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.teacher_recruitment_settings;
        """
    )
