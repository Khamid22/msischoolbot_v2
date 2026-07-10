# Naming Glossary

Use one explicit name per identity or boundary. Do not use a generic `user_id` or `student_id` when two different identifiers could fit.

## Accounts and People

| Preferred name | Meaning | Avoid in new code |
| --- | --- | --- |
| `account_id` | primary key from `msi_v2.accounts`; canonical authentication identity | old admin/staff row ID called an account |
| `canonical_role` | normalized `accounts.role` | inferring business role only from presentation `auth_role` |
| `staff_id` | primary key from `msi_staff`, connected through `staff_profiles` | `account_id` when the value is a staff profile entity |
| `teacher_id` | primary key from `teachers`, connected through `teacher_profiles` | staff row ID or teacher login code |
| `parent_id` | primary key from `parents`, connected through `parent_profiles` | `parent_admin_id`, `parent_account_id` when the entity ID is intended |
| `telegram_user_id` | Telegram numeric identifier; trusted only after HMAC verification or an active canonical link | `tg_user_id`, unsigned query/form identity |
| `session_version` | account version stored in DB and cookie to invalidate older sessions | treating a valid cookie signature as sufficient after account changes |

## Students

| Preferred name | Meaning | Avoid in new code |
| --- | --- | --- |
| `student_db_id` or `canonical_student_id` | primary key from `msi_v2.students.id`; authorization and foreign-key identity | ambiguous `student_id` |
| `legacy_student_row_id` | value from `students.legacy_student_row_id` used at old admin/parent compatibility boundaries | treating it as the canonical primary key |
| `student_code` | canonical login/display code, for example `MSI00001` | `student_id` when it means a login |
| `enrollment_id` | canonical `group_students.id` when the relational enrollment row is intended | public dashboard ID |
| `legacy_enrollment_id` | imported correlation value in `group_students.legacy_enrollment_id` | canonical enrollment primary key |
| `public_dashboard_id` or `student_enrollment_id` in session compatibility | `group_students.legacy_public_dashboard_id`, used by `/dashboard/{student_id}` | canonical student identity |

Existing route parameter names such as `student_row_id` and `/dashboard/{student_id}` are compatibility contracts. Resolve them at the HTTP boundary and use `students.id` inside authorization and domain writes.

## Academics

| Preferred name | Meaning | Avoid in new code |
| --- | --- | --- |
| `school_id` | canonical `schools.id` foreign key | matching only by display text |
| `school_code` | normalized external/UI key such as `school5` | raw workbook school label |
| `subject_id` | canonical `subjects.id` | subject display name as identity |
| `subject_program_id` | canonical program used to constrain group/enrollment moves | assuming subject name alone proves program equality |
| `group_id` | canonical `groups.id` | group label as identity |
| `lesson_session_id` | canonical lesson delivery record | lesson number/order without group/program context |
| `lesson_number` | human-facing/source lesson label | `lesson_order` unless actual sort order is meant |
| `source_order` | source-defined ordering metadata when verified | an inferred sequence substituted for source truth |
| `attendance_rate` | percentage derived from attendance records | ambiguous `ar` in new service code |
| `exam_performance` | exam metric derived from results | ambiguous `ep` in new service code |

## Dates and Time

| Preferred name | Meaning | Avoid in new code |
| --- | --- | --- |
| `lesson_date` | database date for a lesson | locale-formatted string as storage identity |
| `starts_at`, `ends_at` | timezone-aware instants | timezone-less browser strings |
| `school_date_key` | `YYYY-MM-DD` calendar day in `Asia/Tashkent` | browser-local day when filtering school data |
| `created_at`, `updated_at` | timezone-aware audit timestamps | display-formatted timestamps in persistence code |

If a workbook supplies a date but no start time, retain the date and leave time unknown. Do not manufacture a timetable time.

## Invites and Telegram

| Preferred name | Meaning | Avoid in new code |
| --- | --- | --- |
| `invite_code` | raw random capability held by the user/URL only | persisting it |
| `invite_code_hash` / `token_hash` at the DB boundary | SHA-256 digest stored in `account_invites` | plaintext token/code storage |
| `init_data` | raw Telegram Mini App payload verified server-side | `initDataUnsafe` as trusted identity |
| `account_telegram_link` | canonical account mapping after verified Telegram identity | a second Telegram-owned account model |

## Migration Rule

Keep legacy database columns only while they serve a documented migration/public compatibility boundary. New code should translate at the edge, name the canonical value explicitly, and add a reviewed Alembic migration for physical schema changes.
