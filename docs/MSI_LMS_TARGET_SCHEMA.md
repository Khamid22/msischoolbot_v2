# MSI LMS Portal Target Schema

Status: planning document. Do not treat this as implemented code.

PostgreSQL is the only source of truth.

Excel and Google Sheets are import/export sources only.

## Schema Principles

- Store canonical data in PostgreSQL.
- Use stable primary keys and foreign keys.
- Keep one concept in one table block.
- Do not store plaintext passwords.
- Do not use route-level hardcoded access blocking.
- Preserve migrated academic data.
- Keep legacy compatibility columns only while needed for transition.
- Add destructive cleanup only after backup, report, and approval.

## Current Working Schema

The current working schema is `msi_v2`.

Important existing tables:

- `schools`
- `students`
- `student_auth`
- `parents`
- `parent_student_links`
- `msi_staff`
- `teachers`
- `subjects`
- `subject_programs`
- `subject_program_items`
- `groups`
- `group_students`
- `lesson_sessions`
- `attendance_records`
- `homework_scores`
- `exam_results`
- `resources`
- `announcements`
- `support_tickets`
- `payments`

The academic data migration has populated PostgreSQL. Runtime academic reads should use these tables.

## Target Schema Blocks

### Identity And Access

Purpose: one account model, one role per user.

Proposed tables:

- `accounts`
- `account_credentials`
- `account_sessions`
- `account_telegram_links`
- `account_invites`
- `role_permissions`
- `audit_events`

Core rules:

- Use one physical `accounts` table for every login identity.
- One account has one role.
- Role-specific data belongs in separate profile/domain tables.
- Documentation role `system_admin` replaces business use of `admin`.
- Current code may still use `admin` during transition.
- Students use MSI code plus password.
- Teachers use `TCH0001` format.
- Parents are Telegram-first for first rebuild.

### Organization

Purpose: client schools and contracts.

Proposed tables:

- `schools`
- `school_contacts`
- `school_contracts`
- `school_contract_terms`

Rules:

- School 5 and Sehriyo are current schools.
- More schools must be added without schema redesign.
- B2B unpaid contract issues escalate to CEO only.
- Do not automatically block a whole school.

### People

Purpose: people profiles and relationships.

Proposed tables:

- `students`
- `student_auth`
- `parents`
- `parent_student_links`
- `teachers`
- `teacher_subjects`
- `staff_profiles`

Rules:

- `students.student_code` is globally unique.
- Parent-child link is many-to-many.
- A parent can have children across schools.
- Teacher can teach multiple subjects.
- One teacher has one login account.

### Staff & Hiring

Purpose: hiring and teacher development.

Proposed tables:

- `teacher_candidates`
- `teacher_candidate_events`
- `academy_teachers`
- `academy_lesson_assignments`
- `academy_assessments`

### Academic Structure

Purpose: what MSI teaches and how it is organized.

Proposed tables:

- `subjects`
- `subject_programs`
- `subject_program_items`
- `groups`
- `group_students`
- `group_teachers`
- `group_schedule_rules`

Rules:

- Subjects are universal MSI subjects.
- Subject programs are versioned.
- Groups attach to subject programs.
- Students are enrolled into groups by academic staff.
- Students do not choose subjects themselves.

### Learning Delivery

Purpose: lesson-level delivery records.

Proposed tables:

- `lesson_sessions`
- `attendance_records`
- `homework_scores`
- `office_hour_slots`
- `office_hour_bookings`

Rules:

- Lesson, practice, and cancelled sessions are recognized.
- Session source metadata from Excel can remain for audit/import traceability.

### Assessment & Progress

Purpose: exam and progress records.

Proposed tables:

- `exam_results`
- `coin_events`
- optional future `progress_snapshots`
- optional future `rating_snapshots`

Rules:

- Existing duplicate exam keys are not cleaned yet.
- Duplicate exam keys need a separate investigation report.

### Learning Resources

Purpose: study materials.

Proposed tables:

- `resource_types`
- `resources`
- `resource_comments`
- optional future `resource_files`

### Operations

Purpose: payments, restrictions, audits, settings.

Proposed tables:

- `billing_accounts`
- `payment_agreements`
- `invoices`
- `invoice_items`
- `payments`
- `payment_warnings`
- `access_policies`
- `access_restrictions`
- `app_settings`

Rules:

- Payment state should be derived from invoices and payments.
- Access restriction should be a stored/audited decision.
- Routes should consult policy decisions, not hardcode blocking.

### Communication & Support

Purpose: B2C parent/student support and announcements.

Proposed tables:

- `support_tickets`
- `ticket_messages`
- `support_followups`
- `announcements`
- `notification_events`

Customer Support scope:

- Parents.
- Payments.
- Warnings.
- Follow-up.
- Support tickets.

### Analytics & Reports

Purpose: read models and snapshots.

Proposed tables:

- optional `report_snapshots`
- optional `dashboard_metrics`
- optional materialized views

CEO drilldown should be audit logged.

## Important Constraints

Recommended constraints:

- Unique `accounts.login`.
- Unique `students.student_code`.
- Unique teacher login format matching `TCH[0-9]{4,}`.
- Unique active parent Telegram link per Telegram account.
- Unique active parent-student link pair.
- Unique lesson session source key when source key exists.
- Unique attendance per lesson session and student.
- Unique homework score per lesson session and student.

Exam uniqueness should not be changed until duplicate exam keys are investigated.

## Current Schema Issues To Fix Later

- `payments.student_id` is currently used inconsistently by service code versus schema meaning.
- `password_plain` exists for compatibility and should be removed from target auth.
- `legacy_*` columns are useful during migration but should not define the future model.
- `student_auth` currently has fewer rows than `students`; student account readiness needs review.
- Duplicate exam keys exist and should be investigated later.
