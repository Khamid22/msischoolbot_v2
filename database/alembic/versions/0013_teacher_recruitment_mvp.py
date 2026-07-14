"""add the teacher recruitment HR MVP

Revision ID: 0013_teacher_recruitment
Revises: 0012_calendar_closures
Create Date: 2026-07-14
"""

from alembic import op


revision = "0013_teacher_recruitment"
down_revision = "0012_calendar_closures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE msi_v2.teacher_candidates
            ADD COLUMN IF NOT EXISTS applied_position TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS application_date DATE,
            ADD COLUMN IF NOT EXISTS age SMALLINT,
            ADD COLUMN IF NOT EXISTS address TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS english_level TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS motivation_expectations TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS interests_hobbies TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS preferred_schedule TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS employment_availability TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS work_experience TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS teaching_experience TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS previous_workplace TEXT NOT NULL DEFAULT '',
            ADD COLUMN IF NOT EXISTS expected_salary_uzs NUMERIC(14, 2),
            ADD COLUMN IF NOT EXISTS available_start_date DATE,
            ADD COLUMN IF NOT EXISTS stage_changed_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS updated_by_account_id BIGINT
                REFERENCES msi_v2.accounts(id) ON DELETE SET NULL;

        UPDATE msi_v2.teacher_candidates
        SET status = CASE lower(btrim(status))
            WHEN 'new' THEN 'new_candidate'
            WHEN 'interview' THEN 'job_interview'
            WHEN 'math_test' THEN 'test_and_demo'
            WHEN 'training_ready' THEN 'test_and_demo'
            WHEN 'training_passed' THEN 'under_review'
            WHEN 'hired' THEN 'active_teacher'
            WHEN 'rejected' THEN 'rejected'
            WHEN 'withdrawn' THEN 'candidate_withdrew'
            WHEN 'new_candidate' THEN 'new_candidate'
            WHEN 'job_interview' THEN 'job_interview'
            WHEN 'test_and_demo' THEN 'test_and_demo'
            WHEN 'under_review' THEN 'under_review'
            WHEN 'teacher_academy' THEN 'teacher_academy'
            WHEN 'active_teacher' THEN 'active_teacher'
            WHEN 'on_hold' THEN 'on_hold'
            WHEN 'candidate_withdrew' THEN 'candidate_withdrew'
            ELSE 'new_candidate'
        END,
        stage_changed_at = COALESCE(stage_changed_at, updated_at, created_at),
        version = GREATEST(COALESCE(version, 1), 1);

        ALTER TABLE msi_v2.teacher_candidates
            ALTER COLUMN status SET DEFAULT 'new_candidate';
        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_stage_check CHECK (
                status IN (
                    'new_candidate', 'job_interview', 'test_and_demo',
                    'under_review', 'teacher_academy', 'active_teacher',
                    'rejected', 'on_hold', 'candidate_withdrew'
                )
            );
        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_age_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_age_check CHECK (
                age IS NULL OR age BETWEEN 14 AND 100
            );
        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_version_check;
        ALTER TABLE msi_v2.teacher_candidates
            ADD CONSTRAINT teacher_candidates_version_check CHECK (version > 0);

        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_stage_updated
        ON msi_v2.teacher_candidates (status, updated_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_name_ci
        ON msi_v2.teacher_candidates ((lower(full_name)));
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_position_ci
        ON msi_v2.teacher_candidates ((lower(applied_position)));
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_source_ci
        ON msi_v2.teacher_candidates ((lower(source)));
        CREATE INDEX IF NOT EXISTS idx_teacher_candidates_application_date
        ON msi_v2.teacher_candidates (application_date DESC NULLS LAST);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_documents (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            document_type TEXT NOT NULL,
            original_file_name TEXT NOT NULL,
            object_key TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes BIGINT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            replaces_document_id BIGINT REFERENCES msi_v2.teacher_candidate_documents(id) ON DELETE SET NULL,
            uploaded_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            removed_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            removed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_documents_type_check CHECK (
                document_type IN ('cv', 'a_level', 'igcse', 'id_passport', 'ielts', 'sat', 'diploma', 'other')
            ),
            CONSTRAINT teacher_candidate_documents_size_check CHECK (size_bytes > 0),
            CONSTRAINT teacher_candidate_documents_version_check CHECK (version > 0)
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_documents_candidate_created
        ON msi_v2.teacher_candidate_documents (candidate_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_interviews (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            interview_at TIMESTAMPTZ,
            interviewer_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            interview_format TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            english_level TEXT NOT NULL DEFAULT '',
            strengths TEXT NOT NULL DEFAULT '',
            concerns TEXT NOT NULL DEFAULT '',
            hr_recommendation TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL,
            created_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_interviews_result_check CHECK (
                result IN ('passed', 'failed', 'on_hold', 'additional_interview', 'candidate_withdrew')
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_interviews_candidate_created
        ON msi_v2.teacher_candidate_interviews (candidate_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_subject_tests (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            test_at TIMESTAMPTZ,
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            subject_label TEXT NOT NULL DEFAULT '',
            evaluator_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            score NUMERIC(10, 2),
            maximum_score NUMERIC(10, 2),
            notes TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL,
            created_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_subject_tests_result_check CHECK (
                result IN ('passed', 'failed', 'retake_required', 'not_completed')
            ),
            CONSTRAINT teacher_candidate_subject_tests_score_check CHECK (
                score IS NULL OR score >= 0
            ),
            CONSTRAINT teacher_candidate_subject_tests_max_check CHECK (
                maximum_score IS NULL OR maximum_score > 0
            ),
            CONSTRAINT teacher_candidate_subject_tests_range_check CHECK (
                score IS NULL OR maximum_score IS NULL OR score <= maximum_score
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_subject_tests_candidate_created
        ON msi_v2.teacher_candidate_subject_tests (candidate_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_demo_lessons (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            demo_at TIMESTAMPTZ,
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            subject_label TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL DEFAULT '',
            evaluator_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            overview TEXT NOT NULL DEFAULT '',
            strengths TEXT NOT NULL DEFAULT '',
            areas_for_improvement TEXT NOT NULL DEFAULT '',
            score NUMERIC(4, 2),
            result TEXT NOT NULL,
            recommendation TEXT NOT NULL DEFAULT '',
            created_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_demo_lessons_result_check CHECK (
                result IN ('passed', 'failed', 'additional_demo', 'on_hold')
            ),
            CONSTRAINT teacher_candidate_demo_lessons_score_check CHECK (
                score IS NULL OR score BETWEEN 0 AND 10
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_demo_lessons_candidate_created
        ON msi_v2.teacher_candidate_demo_lessons (candidate_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_assignments (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            assignee_account_id BIGINT NOT NULL REFERENCES msi_v2.accounts(id) ON DELETE CASCADE,
            assignment_type TEXT NOT NULL DEFAULT 'academic_evaluator',
            subject_id BIGINT REFERENCES msi_v2.subjects(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'active',
            assigned_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_assignments_type_check CHECK (
                assignment_type IN ('academic_evaluator')
            ),
            CONSTRAINT teacher_candidate_assignments_status_check CHECK (
                status IN ('active', 'removed')
            )
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_candidate_assignments_active_unique
        ON msi_v2.teacher_candidate_assignments (candidate_id, assignee_account_id, assignment_type)
        WHERE status = 'active';
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_assignments_assignee
        ON msi_v2.teacher_candidate_assignments (assignee_account_id, status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_tasks (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            due_at TIMESTAMPTZ,
            responsible_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            note TEXT NOT NULL DEFAULT '',
            completed_at TIMESTAMPTZ,
            cancelled_at TIMESTAMPTZ,
            created_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            updated_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_tasks_title_check CHECK (length(btrim(title)) > 0),
            CONSTRAINT teacher_candidate_tasks_status_check CHECK (
                status IN ('pending', 'completed', 'cancelled')
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_tasks_due_status
        ON msi_v2.teacher_candidate_tasks (status, due_at ASC NULLS LAST, id ASC);
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_tasks_responsible
        ON msi_v2.teacher_candidate_tasks (responsible_account_id, status, due_at ASC NULLS LAST);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_notes (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            body TEXT NOT NULL,
            author_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            author_login TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_notes_body_check CHECK (length(btrim(body)) > 0)
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_notes_candidate_created
        ON msi_v2.teacher_candidate_notes (candidate_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_hire_approvals (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            requested_outcome TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'requested',
            request_note TEXT NOT NULL DEFAULT '',
            review_comment TEXT NOT NULL DEFAULT '',
            requested_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            reviewed_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMPTZ,
            consumed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_hire_approvals_outcome_check CHECK (
                requested_outcome IN ('teacher_academy', 'active_teacher')
            ),
            CONSTRAINT teacher_candidate_hire_approvals_status_check CHECK (
                status IN ('requested', 'approved', 'returned', 'revoked', 'consumed')
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_hire_approvals_candidate_created
        ON msi_v2.teacher_candidate_hire_approvals (candidate_id, created_at DESC, id DESC);

        CREATE TABLE IF NOT EXISTS msi_v2.teacher_candidate_final_decisions (
            id BIGSERIAL PRIMARY KEY,
            candidate_id BIGINT NOT NULL REFERENCES msi_v2.teacher_candidates(id) ON DELETE CASCADE,
            decision TEXT NOT NULL,
            rejection_reason TEXT NOT NULL DEFAULT '',
            reason_detail TEXT NOT NULL DEFAULT '',
            follow_up_at TIMESTAMPTZ,
            approval_id BIGINT REFERENCES msi_v2.teacher_candidate_hire_approvals(id) ON DELETE SET NULL,
            decided_by_account_id BIGINT REFERENCES msi_v2.accounts(id) ON DELETE SET NULL,
            decided_by_login TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT teacher_candidate_final_decisions_decision_check CHECK (
                decision IN ('teacher_academy', 'active_teacher', 'rejected', 'on_hold', 'candidate_withdrew')
            )
        );
        CREATE INDEX IF NOT EXISTS idx_teacher_candidate_final_decisions_candidate_created
        ON msi_v2.teacher_candidate_final_decisions (candidate_id, created_at DESC, id DESC);

        ALTER TABLE msi_v2.academy_teachers
            ADD COLUMN IF NOT EXISTS recruitment_candidate_id BIGINT
                REFERENCES msi_v2.teacher_candidates(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS account_onboarding_status TEXT NOT NULL DEFAULT 'complete';
        ALTER TABLE msi_v2.academy_teachers
            DROP CONSTRAINT IF EXISTS academy_teachers_account_onboarding_check;
        ALTER TABLE msi_v2.academy_teachers
            ADD CONSTRAINT academy_teachers_account_onboarding_check CHECK (
                account_onboarding_status IN ('pending', 'complete')
            );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_academy_teachers_recruitment_candidate
        ON msi_v2.academy_teachers (recruitment_candidate_id)
        WHERE recruitment_candidate_id IS NOT NULL;

        ALTER TABLE msi_v2.teachers
            ADD COLUMN IF NOT EXISTS recruitment_candidate_id BIGINT
                REFERENCES msi_v2.teacher_candidates(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS account_onboarding_status TEXT NOT NULL DEFAULT 'complete';
        ALTER TABLE msi_v2.teachers
            DROP CONSTRAINT IF EXISTS teachers_account_onboarding_check;
        ALTER TABLE msi_v2.teachers
            ADD CONSTRAINT teachers_account_onboarding_check CHECK (
                account_onboarding_status IN ('pending', 'complete')
            );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_teachers_recruitment_candidate
        ON msi_v2.teachers (recruitment_candidate_id)
        WHERE recruitment_candidate_id IS NOT NULL;

        INSERT INTO msi_v2.teacher_candidate_notes (
            candidate_id, body, author_login, created_at
        )
        SELECT c.id, c.notes, 'Legacy import', c.created_at
        FROM msi_v2.teacher_candidates c
        WHERE length(btrim(COALESCE(c.notes, ''))) > 0
          AND NOT EXISTS (
              SELECT 1 FROM msi_v2.teacher_candidate_notes n
              WHERE n.candidate_id = c.id AND n.author_login = 'Legacy import'
          );

        INSERT INTO msi_v2.audit_events (
            event_type, entity_type, entity_id, detail_json, created_at
        )
        SELECT
            'candidate.legacy_event',
            'teacher_candidate',
            event.candidate_id,
            jsonb_build_object(
                'legacy_event_id', event.id,
                'event_type', event.event_type,
                'result', event.result,
                'score', event.score,
                'notes', event.notes,
                'created_by', event.created_by,
                'detail', event.detail_json
            ),
            event.created_at
        FROM msi_v2.teacher_candidate_events event
        WHERE NOT EXISTS (
            SELECT 1
            FROM msi_v2.audit_events audit
            WHERE audit.entity_type = 'teacher_candidate'
              AND audit.entity_id = event.candidate_id
              AND audit.event_type = 'candidate.legacy_event'
              AND audit.detail_json ->> 'legacy_event_id' = event.id::text
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS msi_v2.idx_teachers_recruitment_candidate;
        ALTER TABLE msi_v2.teachers
            DROP CONSTRAINT IF EXISTS teachers_account_onboarding_check,
            DROP COLUMN IF EXISTS account_onboarding_status,
            DROP COLUMN IF EXISTS recruitment_candidate_id;

        DROP INDEX IF EXISTS msi_v2.idx_academy_teachers_recruitment_candidate;
        ALTER TABLE msi_v2.academy_teachers
            DROP CONSTRAINT IF EXISTS academy_teachers_account_onboarding_check,
            DROP COLUMN IF EXISTS account_onboarding_status,
            DROP COLUMN IF EXISTS recruitment_candidate_id;

        DROP TABLE IF EXISTS msi_v2.teacher_candidate_final_decisions;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_hire_approvals;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_notes;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_tasks;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_assignments;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_demo_lessons;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_subject_tests;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_interviews;
        DROP TABLE IF EXISTS msi_v2.teacher_candidate_documents;

        ALTER TABLE msi_v2.teacher_candidates
            DROP CONSTRAINT IF EXISTS teacher_candidates_stage_check,
            DROP CONSTRAINT IF EXISTS teacher_candidates_age_check,
            DROP CONSTRAINT IF EXISTS teacher_candidates_version_check,
            DROP COLUMN IF EXISTS updated_by_account_id,
            DROP COLUMN IF EXISTS version,
            DROP COLUMN IF EXISTS stage_changed_at,
            DROP COLUMN IF EXISTS available_start_date,
            DROP COLUMN IF EXISTS expected_salary_uzs,
            DROP COLUMN IF EXISTS previous_workplace,
            DROP COLUMN IF EXISTS teaching_experience,
            DROP COLUMN IF EXISTS work_experience,
            DROP COLUMN IF EXISTS employment_availability,
            DROP COLUMN IF EXISTS preferred_schedule,
            DROP COLUMN IF EXISTS interests_hobbies,
            DROP COLUMN IF EXISTS motivation_expectations,
            DROP COLUMN IF EXISTS english_level,
            DROP COLUMN IF EXISTS address,
            DROP COLUMN IF EXISTS age,
            DROP COLUMN IF EXISTS application_date,
            DROP COLUMN IF EXISTS applied_position;
        ALTER TABLE msi_v2.teacher_candidates ALTER COLUMN status SET DEFAULT 'new';
        """
    )
