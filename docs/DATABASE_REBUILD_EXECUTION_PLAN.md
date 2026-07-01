# Database Rebuild Execution Plan

Goal: replace the messy inherited schema with a clean MSI School schema and
remove old duplicate tables after the app is switched to the new tables.

## Decision

We will not keep the old tables as permanent compatibility tables.

We will use this sequence:

1. Create the clean schema.
2. Import/merge only useful data into the clean schema.
3. Update backend queries to the clean schema.
4. Verify every workspace.
5. Drop old tables.

Dropping old tables before step 3 would break the app, because the current
FastAPI/backend code still queries names such as `academic_enrollments`,
`academic_subjects`, `students`, `admins`, `parent_children`, and
`subject_summaries`.

## Phase 1: Clean Schema

Create the new schema around the real business model:

```text
MSI -> subject programs -> client schools -> groups -> students
staff -> role/scope -> workspace permissions
parents/students -> Telegram invite linking
```

Core tables:

1. `msi_staff`
2. `telegram_accounts`
3. `account_invites`
4. `audit_events`
5. `schools`
6. `students`
7. `student_auth`
8. `student_telegram_links`
9. `parents`
10. `parent_student_links`
11. `subjects`
12. `subject_programs`
13. `subject_program_items`
14. `groups`
15. `group_students`
16. `teachers`
17. `teacher_subjects`
18. `group_teachers`
19. `group_schedule_rules`
20. `lesson_sessions`
21. `attendance_records`
22. `homework_scores`
23. `exam_results`
24. `coin_events`
25. `resource_types`
26. `resources`
27. `announcements`
28. `support_tickets`
29. `ticket_messages`
30. `payments`
31. `office_hour_slots`
32. `office_hour_bookings`
33. `teacher_candidates`
34. `app_settings`

`import_jobs` can be added only if we need permanent import history.

## Phase 2: Subject Programs From Excel

Import official SOW files as the source of truth:

- IGCSE Mathematics A
- English as a Second Language
- IGCSE Chemistry
- IGCSE Biology
- IGCSE Physics

Rules:

- `subjects` contains one universal subject row per offered subject.
- `subject_programs` contains the version/year/source file.
- `subject_program_items` contains every lesson and exam.
- groups attach to `subject_programs`, not to duplicated school-specific
  subject rows.

## Phase 3: Merge Current Useful Data

Old-to-new mapping:

| Current table | New table |
|---|---|
| `admins` staff rows | `msi_staff` |
| `academic_schools` | `schools` |
| `academic_subjects` | `subjects` / `subject_programs` |
| `academic_curriculum_programs` | `subject_programs` |
| `academic_curriculum_items` | `subject_program_items` |
| `academic_groups` | `groups` |
| `students` | `students` |
| `student_auth` | `student_auth` |
| `academic_enrollments` | `group_students` |
| `teachers` | `teachers` |
| `teacher_auth` | `msi_staff` or removed if teacher login is not ready |
| `parents` | `parents` |
| `parent_student_links` | `parent_student_links` |
| `parent_children` | migrate only, then remove |
| `parent_complaints` | `support_tickets` |
| `parent_complaint_messages` | `ticket_messages` |
| `academic_lessons` / `lesson_catalog` | `lesson_sessions` |
| `academic_attendance_records` | `attendance_records` |
| `academic_homework_scores` | `homework_scores` |
| `academic_exam_results` | `exam_results` |
| `academic_coin_events` | `coin_events` |
| `resources` | `resources` |
| `resource_types` | `resource_types` |
| `announcements` | `announcements` |
| `office_hour_availability` | `office_hour_slots` |
| `office_hour_bookings` | `office_hour_bookings` |
| `teacher_candidates` | `teacher_candidates` |

Do not migrate demo rows marked `[DEMO]`.

## Phase 4: Backend Switch

Update backend in this order:

1. `shared/db/tables.py`
2. `shared/db/queries/`
3. `shared/identity/`
4. `web/backend/domains/`
5. `web/backend/roles/`
6. `tgbot/`

Priority workspaces:

1. CEO
2. Academic Director
3. Head of Department
4. HR Manager
5. Customer Support
6. Teacher
7. Student
8. Parent

## Phase 5: Drop Old Tables

Only after verification passes, drop old tables:

- `admins`
- `academic_*` old tables after replacement
- `parent_children`
- `parent_complaints`
- `parent_complaint_messages`
- `lesson_catalog`
- `students_sheet_map`
- `subject_summaries`
- `teacher_auth`
- old unused chat/payment/resource leftovers if replaced

## Verification

Backend:

```bash
python3 -m compileall -q shared tgbot web/backend scripts main.py
python3 - <<'PY'
from web.backend.server import app
print(app.name)
PY
```

Frontend:

```bash
cd web/frontend
npm run check-types
npm run build
```

Database:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
order by table_name;
```

## Next Work Item

Create the exact SQL file:

```text
scripts/rebuild_database_v2.sql
```

Current reusable importer script:

```text
scripts/import_subject_programs_v2.py
```

The old one-time public-table migration and destructive drop scripts were
removed after the `msi_v2` cutover. Do not recreate them unless there is a new
approved migration plan with a backup and exact SQL review.
