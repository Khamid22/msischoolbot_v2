"""consolidate recruitment rejection and withdrawal reasons

Revision ID: 0041_consolidate_reasons
Revises: 0040_outcome_reasons
Create Date: 2026-07-23
"""

from alembic import op


revision = "0041_consolidate_reasons"
down_revision = "0040_outcome_reasons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- Option identity is normally immutable. This migration preserves one
        -- existing row per merged group and changes that row into the canonical
        -- option, so audit references keep resolving to a real setting.
        ALTER TABLE msi_v2.teacher_recruitment_settings
            DISABLE TRIGGER trg_validate_recruitment_setting;

        DO $$
        DECLARE
            reason_group RECORD;
            canonical_setting_id BIGINT;
        BEGIN
            FOR reason_group IN
                SELECT *
                FROM (
                    VALUES
                        (
                            'rejection_reason'::text,
                            'low_english_level'::text,
                            'Low English Level'::text,
                            'insufficient_english_level'::text,
                            ARRAY[
                                'failed_job_interview',
                                'insufficient_english_level',
                                'other'
                            ]::text[],
                            ARRAY[
                                'failed job interview',
                                'insufficient english level',
                                'other'
                            ]::text[],
                            10
                        ),
                        (
                            'rejection_reason'::text,
                            'low_subject_knowledge'::text,
                            'Low Subject Knowledge'::text,
                            'insufficient_subject_knowledge'::text,
                            ARRAY[
                                'insufficient_subject_knowledge',
                                'failed_subject_test'
                            ]::text[],
                            ARRAY[
                                'insufficient subject knowledge',
                                'failed subject test'
                            ]::text[],
                            20
                        ),
                        (
                            'rejection_reason'::text,
                            'poor_soft_skills'::text,
                            'Poor Soft Skills'::text,
                            'failed_demo_lesson'::text,
                            ARRAY[
                                'failed_demo_lesson',
                                'insufficient_experience'
                            ]::text[],
                            ARRAY[
                                'failed demo lesson',
                                'insufficient experience'
                            ]::text[],
                            30
                        ),
                        (
                            'withdrawal_reason'::text,
                            'received_counter_offer'::text,
                            'Recieved Counter-Offer'::text,
                            'accepted_another_offer'::text,
                            ARRAY[
                                'accepted_another_offer'
                            ]::text[],
                            ARRAY[
                                'accepted another offer',
                                'hired by another private school',
                                'hired by other education center',
                                'hired by other private school',
                                'hunted by other education center',
                                'hunted by other private school',
                                'she got offer',
                                'she got another job offer',
                                'she got another offer'
                            ]::text[],
                            20
                        ),
                        (
                            'withdrawal_reason'::text,
                            'personal_reasons'::text,
                            'Personal Reasons'::text,
                            'personal_circumstances'::text,
                            ARRAY[
                                'personal_circumstances'
                            ]::text[],
                            ARRAY[
                                'personal circumstances',
                                'personal reasons',
                                'plans changed'
                            ]::text[],
                            30
                        )
                ) AS groups(
                    category,
                    canonical_value,
                    canonical_label,
                    preferred_value,
                    source_values,
                    source_labels,
                    sort_order
                )
            LOOP
                -- Remap candidate outcome records before changing the catalog.
                IF reason_group.category = 'rejection_reason' THEN
                    UPDATE msi_v2.teacher_candidate_final_decisions decision
                    SET rejection_reason = reason_group.canonical_value
                    WHERE decision.decision = 'rejected'
                      AND (
                          decision.rejection_reason = ANY(reason_group.source_values)
                          OR lower(btrim(decision.rejection_reason))
                              = ANY(reason_group.source_labels)
                          OR EXISTS (
                              SELECT 1
                              FROM msi_v2.teacher_recruitment_settings setting
                              WHERE setting.category = reason_group.category
                                AND setting.value = decision.rejection_reason
                                AND lower(btrim(setting.label))
                                    = ANY(reason_group.source_labels)
                          )
                      );
                ELSE
                    UPDATE msi_v2.teacher_candidate_final_decisions decision
                    SET withdrawal_reason = reason_group.canonical_value
                    WHERE decision.decision = 'candidate_withdrew'
                      AND (
                          decision.withdrawal_reason = ANY(reason_group.source_values)
                          OR lower(btrim(decision.withdrawal_reason))
                              = ANY(reason_group.source_labels)
                          OR lower(btrim(decision.reason_detail))
                              = ANY(reason_group.source_labels)
                          OR EXISTS (
                              SELECT 1
                              FROM msi_v2.teacher_recruitment_settings setting
                              WHERE setting.category = reason_group.category
                                AND setting.value = decision.withdrawal_reason
                                AND lower(btrim(setting.label))
                                    = ANY(reason_group.source_labels)
                          )
                      );
                END IF;

                SELECT setting.id
                INTO canonical_setting_id
                FROM msi_v2.teacher_recruitment_settings setting
                WHERE setting.category = reason_group.category
                  AND (
                      setting.value = reason_group.canonical_value
                      OR lower(btrim(setting.label))
                          = lower(btrim(reason_group.canonical_label))
                      OR setting.value = ANY(reason_group.source_values)
                      OR lower(btrim(setting.label))
                          = ANY(reason_group.source_labels)
                  )
                ORDER BY
                    CASE
                        WHEN setting.value = reason_group.canonical_value THEN 0
                        WHEN lower(btrim(setting.label))
                            = lower(btrim(reason_group.canonical_label)) THEN 1
                        WHEN setting.value = reason_group.preferred_value THEN 2
                        ELSE 3
                    END,
                    setting.id
                LIMIT 1;

                IF canonical_setting_id IS NULL THEN
                    INSERT INTO msi_v2.teacher_recruitment_settings (
                        category, value, label, is_active, sort_order,
                        is_system, is_legacy, created_at, updated_at
                    ) VALUES (
                        reason_group.category,
                        reason_group.canonical_value,
                        reason_group.canonical_label,
                        true,
                        reason_group.sort_order,
                        false,
                        false,
                        now(),
                        now()
                    )
                    RETURNING id INTO canonical_setting_id;
                ELSE
                    -- Remove only redundant catalog aliases. Candidate outcome
                    -- rows were already remapped above; candidates are never
                    -- deleted by this migration.
                    DELETE FROM msi_v2.teacher_recruitment_settings setting
                    WHERE setting.category = reason_group.category
                      AND setting.id <> canonical_setting_id
                      AND (
                          setting.value = reason_group.canonical_value
                          OR lower(btrim(setting.label))
                              = lower(btrim(reason_group.canonical_label))
                          OR setting.value = ANY(reason_group.source_values)
                          OR lower(btrim(setting.label))
                              = ANY(reason_group.source_labels)
                      );

                    UPDATE msi_v2.teacher_recruitment_settings
                    SET value = reason_group.canonical_value,
                        label = reason_group.canonical_label,
                        is_active = true,
                        sort_order = reason_group.sort_order,
                        is_system = false,
                        is_legacy = false,
                        updated_at = now()
                    WHERE id = canonical_setting_id;
                END IF;

                canonical_setting_id := NULL;
            END LOOP;
        END
        $$;

        ALTER TABLE msi_v2.teacher_recruitment_settings
            ENABLE TRIGGER trg_validate_recruitment_setting;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE msi_v2.teacher_candidate_final_decisions
        SET rejection_reason = CASE rejection_reason
            WHEN 'low_english_level' THEN 'insufficient_english_level'
            WHEN 'low_subject_knowledge' THEN 'insufficient_subject_knowledge'
            WHEN 'poor_soft_skills' THEN 'insufficient_experience'
            ELSE rejection_reason
        END
        WHERE rejection_reason IN (
            'low_english_level',
            'low_subject_knowledge',
            'poor_soft_skills'
        );

        UPDATE msi_v2.teacher_candidate_final_decisions
        SET withdrawal_reason = CASE withdrawal_reason
            WHEN 'received_counter_offer' THEN 'accepted_another_offer'
            WHEN 'personal_reasons' THEN 'personal_circumstances'
            ELSE withdrawal_reason
        END
        WHERE withdrawal_reason IN (
            'received_counter_offer',
            'personal_reasons'
        );

        DELETE FROM msi_v2.teacher_recruitment_settings
        WHERE (category = 'rejection_reason' AND value IN (
                   'low_english_level',
                   'low_subject_knowledge',
                   'poor_soft_skills'
               ))
           OR (category = 'withdrawal_reason' AND value IN (
                   'received_counter_offer',
                   'personal_reasons'
               ));

        INSERT INTO msi_v2.teacher_recruitment_settings (
            category, value, label, is_active, sort_order, is_system,
            is_legacy, created_at, updated_at
        ) VALUES
            ('rejection_reason', 'failed_job_interview', 'Failed job interview', true, -30, false, false, now(), now()),
            ('rejection_reason', 'failed_subject_test', 'Failed subject test', true, -20, false, false, now(), now()),
            ('rejection_reason', 'failed_demo_lesson', 'Failed demo lesson', true, -10, false, false, now(), now()),
            ('rejection_reason', 'insufficient_subject_knowledge', 'Insufficient subject knowledge', true, 10, false, false, now(), now()),
            ('rejection_reason', 'insufficient_english_level', 'Insufficient English level', true, 20, false, false, now(), now()),
            ('rejection_reason', 'insufficient_experience', 'Insufficient experience', true, 60, false, false, now(), now()),
            ('rejection_reason', 'other', 'Other', true, 110, false, false, now(), now()),
            ('withdrawal_reason', 'accepted_another_offer', 'Accepted another offer', true, 20, false, false, now(), now()),
            ('withdrawal_reason', 'personal_circumstances', 'Personal circumstances', true, 30, false, false, now(), now())
        ON CONFLICT DO NOTHING;
        """
    )
