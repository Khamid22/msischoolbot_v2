"""add school classes above subject groups

Revision ID: 0009_academic_classes
Revises: 0008_remove_teacher_portal
Create Date: 2026-07-11
"""

from alembic import op


revision = "0009_academic_classes"
down_revision = "0008_remove_teacher_portal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE msi_v2.classes (
            id BIGSERIAL PRIMARY KEY,
            school_id BIGINT NOT NULL REFERENCES msi_v2.schools(id) ON DELETE CASCADE,
            class_name TEXT NOT NULL,
            class_code TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT classes_status_check CHECK (status IN ('active', 'completed', 'archived'))
        );
        CREATE UNIQUE INDEX classes_school_name_ci
        ON msi_v2.classes (school_id, lower(btrim(class_name)));

        ALTER TABLE msi_v2.groups
        ADD COLUMN class_id BIGINT REFERENCES msi_v2.classes(id) ON DELETE RESTRICT,
        ADD COLUMN set_name TEXT NOT NULL DEFAULT 'Set 1';

        INSERT INTO msi_v2.classes (school_id, class_name, class_code)
        SELECT school_id, min(btrim(group_name)), max(coalesce(group_code, ''))
        FROM msi_v2.groups
        WHERE lower(btrim(group_name)) <> 'online'
        GROUP BY school_id, lower(btrim(group_name));

        UPDATE msi_v2.groups g
        SET class_id = c.id
        FROM msi_v2.classes c
        WHERE c.school_id = g.school_id
          AND lower(btrim(c.class_name)) = lower(btrim(g.group_name));

        CREATE TABLE msi_v2.class_students (
            class_id BIGINT NOT NULL REFERENCES msi_v2.classes(id) ON DELETE CASCADE,
            student_id BIGINT NOT NULL REFERENCES msi_v2.students(id) ON DELETE CASCADE,
            enrollment_status TEXT NOT NULL DEFAULT 'active',
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            left_at TIMESTAMPTZ,
            PRIMARY KEY (class_id, student_id),
            CONSTRAINT class_students_status_check
              CHECK (enrollment_status IN ('active', 'inactive', 'completed'))
        );

        INSERT INTO msi_v2.class_students (class_id, student_id, enrollment_status, joined_at)
        SELECT DISTINCT g.class_id, gs.student_id, 'active', min(gs.joined_at)
        FROM msi_v2.group_students gs
        JOIN msi_v2.groups g ON g.id = gs.group_id
        WHERE g.class_id IS NOT NULL AND gs.enrollment_status = 'active'
        GROUP BY g.class_id, gs.student_id;

        CREATE INDEX idx_groups_class_id ON msi_v2.groups (class_id);
        CREATE INDEX idx_class_students_student_id ON msi_v2.class_students (student_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS msi_v2.class_students;
        DROP INDEX IF EXISTS msi_v2.idx_groups_class_id;
        ALTER TABLE msi_v2.groups DROP COLUMN IF EXISTS set_name, DROP COLUMN IF EXISTS class_id;
        DROP TABLE IF EXISTS msi_v2.classes;
        """
    )
