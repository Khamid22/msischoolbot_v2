# Engineering Module Map

Audience: engineers locating the owner of a change.

## Change Routing

| Change | Backend owner | Frontend owner |
| --- | --- | --- |
| account, password, session identity | `modules/identity` | `features/identity` |
| school, subject, class | `modules/organization` | composed by academic workspaces |
| student records | `modules/people/students` | `features/people/students` |
| parent records and links | `modules/people/parents` | `features/people/parents` |
| teacher records | `modules/people/teachers` | `features/people/teachers` |
| staff account registration | `modules/people/staff` | authorized workspace adapters |
| Teacher Academy | `modules/teacher_academy` | `features/teacher-academy` |
| teacher recruitment | `modules/hr/recruitment` | `features/recruitment` |
| curriculum/program | `modules/academics/curriculum` | `features/academics` |
| groups/enrollment | `modules/academics/groups` | `features/academics` |
| schedules/reflow/office hours | `modules/academics/timetable` | `features/academics/timetable` |
| lesson overrides | `modules/academics/lessons` | timetable details UI |
| attendance | `modules/academics/attendance` | `features/academics/gradebook` |
| homework/rewards/trends | `modules/academics/gradebook` | `features/academics/gradebook` |
| exams | `modules/academics/assessments` | Gradebook exam view |
| holiday closures | `modules/academics/calendar` | timetable closure UI |
| learning resources | `modules/academics/resources` | `features/academics/resources` |
| payments | `modules/finance` | `features/finance` |
| complaints | `modules/support` | `features/support` |
| announcements/chat | `modules/communications` | `features/communications` |
| dashboards/read models | `modules/reporting` | `features/reporting` |
| System Admin page composition | `internal_operations/pages` | `internal_operations` |
| System Admin academic transport | `internal_operations/academics` | `internal_operations` |
| System Admin people/staffing transport | `internal_operations/people`, `internal_operations/staffing` | `internal_operations` |
| System Admin finance/support/resources transport | corresponding `internal_operations` package | `internal_operations` |
| shared API/web/runtime infrastructure | `core/api`, `core/web`, `core/runtime` | n/a |
| storage, Redis, Telegram adapter | `platform` | n/a |

## Table Ownership

| Owner | Principal tables |
| --- | --- |
| Identity | `accounts`, `account_telegram_links`, `student_auth`, `staff_profiles`, `audit_events` |
| Organization | `schools`, `subjects`, `classes`, `class_students` |
| People / Students | `students`, `student_profiles` |
| People / Parents | `parents`, `parent_profiles`, parent links/invites |
| People / Teachers and Staff | `teachers`, `teacher_profiles`, `msi_staff`, `staff_subject_scopes` |
| Academics / Curriculum | `subject_programs`, `subject_program_items` |
| Academics / Groups | `groups`, `group_students` |
| Academics / Timetable | `group_schedule_rules`, `lesson_sessions`, office-hour tables |
| Academics / Lessons | group-specific lesson-session overrides (within `lesson_sessions`) |
| Academics / Attendance | `attendance_records` |
| Academics / Gradebook | `homework_scores`, `coin_events` |
| Academics / Assessments | `exam_results` |
| Academics / Calendar | `academic_calendar_closures`, `lesson_schedule_exceptions` |
| Academics / Resources | resource type/resource/comment tables |
| Recruitment | `teacher_candidates`, normalized candidate document/evaluation/assignment/task/note/approval/decision tables; legacy candidate events are read-only history |
| Teacher Academy | training, evaluation, assignment, and development tables |
| Finance | `payments` |
| Support | complaint/support tables |
| Communications | announcement and chat tables |
| Reporting | no transactional ownership; read-only projections |

When one physical table serves closely related academic concerns, the write contract is owned by the row's domain service; other domains consume a public read contract.

## Explicit Size Exceptions

These existing stateful orchestrators remain above the target threshold after extracting their models, calculations, dialogs, or child views. They are documented compatibility exceptions and must not grow without first extracting another focused unit:

- `features/academics/AcademicPanel.tsx`
- `features/academics/gradebook/GroupGradebook.tsx`
- `features/academics/timetable/SchedulePanel.tsx`
- `features/academics/timetable/Timetable.tsx`
- `features/academics/timetable/ModernGroupTimetable.tsx`
- `features/teacher-academy/TeacherAcademyPanel.tsx`
- `features/finance/PaymentsPanel.tsx`
- `features/reporting/overview/RoleOverviewPanel.tsx`
- `features/reporting/overview/SchoolOverviewPanel.tsx`
- `features/academics/office-hours/OfficeHoursPanel.tsx`
- `features/people/students/StudentsPanel.tsx`
- `features/communications/AnnouncementsPanel.tsx`
- internal-operation and workspace orchestrators (transport composition, not domain features)
- `modules/reporting/insights.py`, `modules/people/students/dashboard.py`, and `platform/storage/r2.py`
- `modules/hr/recruitment/service.py` — cohesive transaction/orchestration boundary for the MVP; persistence remains extracted to its repository and the next expansion should split documents and decisions into focused services.
- `modules/hr/recruitment/repository.py` — one SQL ownership boundary for the normalized recruitment aggregate; split read projections from mutation persistence before adding another recruitment subdomain.

No new backend domain implementation may exceed 800 lines and no new frontend feature component may exceed 600 lines without adding a named rationale here.

## Removed Owners

Do not import or recreate:

- old module packages: `accounts`, `complaints`, `learning_resources`, `parent_access`, `payments`, `staff_records`, `student_records`;
- academic catch-alls: `academics/operations.py`, `academics/service.py`, `academics/repository.py`;
- `backend/integrations` (use `backend/platform`);
- `frontend/src/features/management` and `frontend/src/features/accounts`;
- generic backend `api`, `pages`, `services`, `repositories`, or `schemas` trees.

Future observations, interventions, payroll, and expanded finance capabilities remain documentation-only until implemented.
