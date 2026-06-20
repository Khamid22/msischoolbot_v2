# Naming Glossary

Use these names when adding or renaming code. The goal is simple: one concept,
one name.

## People and Accounts

| Preferred name | Meaning | Avoid / old names |
|---|---|---|
| `account_id` | Primary key from `admins.id`; any staff/admin-style login account. | vague `user_id`, sometimes `admin_id` |
| `admin_account_id` | Staff/admin account id when the admin role matters. | `admin_id` when the value is not clearly an admin |
| `parent_account_id` | Parent account id from `admins.id` when role is parent. | `parent_admin_id` in new code |
| `teacher_id` | Primary key for a teacher row. | no change |
| `telegram_user_id` | Telegram numeric user id. This is not a password or proof of identity by itself. | `tg_user_id`, `user_id` |
| `role` | Account role, such as `owner`, `admin`, `ceo`, `customer_support`, `teacher`, `parent`, `student`. | mixed booleans when a role string is clearer |

## Students

| Preferred name | Meaning | Avoid / old names |
|---|---|---|
| `student_row_id` | Primary key from `students.id`. | `student_id` when it means DB row id |
| `student_code` | Public/login student code, for example `MSI00001`. | `student_id` when it means login code |
| `student_full_name` | Student display name. | vague `name` |
| `enrollment_id` | Imported/public dashboard id, historically from Google Sheets. Used by several dashboard URLs. | `sheet_student_id`, route `student_id` when it means enrollment |
| `school_code` | Normalized school code, for example `school5`. | `school_key` outside DB/query layer |

Important: old route parameters like `/dashboard/<int:student_id>` often mean
`enrollment_id`, not `students.id`. Rename carefully and verify behavior before
changing URL names.

## Academics

| Preferred name | Meaning | Avoid / old names |
|---|---|---|
| `subject_name` | Canonical full subject name, for example `IGCSE Mathematics A`. | raw sheet subject names |
| `subject_short` | Display short name, for example `Math`, `Chem`, `Eng`. | ad hoc abbreviations |
| `subject_key` | Stable lowercase key used for matching/filtering, for example `math`, `chem`, `eng`. | raw lowercased subject names |
| `group_name` | Class/group label. | vague `group` |
| `lesson_number` | Human-facing lesson number. | mixed `lesson_order` unless order specifically matters |
| `aap_score` | Average academic performance score. | bare `aap` in new service internals |
| `attendance_rate` | AR percentage. | bare `ar` in new service internals |
| `exam_performance` | EP score. | bare `ep` in new service internals |

## Dates and Time

| Preferred name | Meaning | Avoid / old names |
|---|---|---|
| `lesson_date` | Date of a lesson. Store/display canonically as `dd/mm/yyyy` where the existing app expects text dates. | mixed date strings |
| `created_at` | Creation timestamp. | no change |
| `updated_at` | Last update timestamp. | no change |
| `last_seen_at` | Last user activity timestamp. | vague `activity` |

## Files and Resources

| Preferred name | Meaning | Avoid / old names |
|---|---|---|
| `resource_id` | Primary key from `resources.id`. | vague `id` across service boundaries |
| `resource_type` | Category such as video, PDF, worksheet. | vague `type` across service boundaries |
| `storage_key` | Cloud/R2 object key. | vague `key` |
| `public_url` | URL usable by the frontend/user. | vague `url` when multiple URLs exist |

## Migration Notes

Do not rename everything at once. Rename at boundaries first:

1. route parameter names and payload builders
2. service function arguments
3. query function arguments
4. database columns only with explicit migrations

Database columns can keep old names temporarily if changing them risks data
loss. Use clear Python variable names around them so reviewers understand what
the old column represents.
