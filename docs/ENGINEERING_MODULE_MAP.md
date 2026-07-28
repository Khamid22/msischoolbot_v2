# Engineering Module Map

Audience: engineers locating the owner of a change.

## Change Routing

| Change | Backend owner | Frontend owner |
| --- | --- | --- |
| account, password, session identity | `modules/domains/identity` | `features/identity` |
| school, subject, class | `modules/domains/organization` | composed by academic workspaces |
| student records | `modules/domains/student_records` | `features/people/students` |
| parent records and links | `modules/domains/parent_relationships` | `features/people/parents` |
| Customer Support orchestration | `modules/people/customer_support/{dashboard,parents,teachers,tickets}` | `workspaces/customer_support` |
| teacher records | `modules/domains/teacher_records` | `features/people/teachers` |
| staff account registration | `modules/domains/identity/staff_accounts` | authorized workspace adapters |
| Teacher Academy | `modules/domains/teacher_academy` | `features/teacher-academy` |
| teacher recruitment | `modules/domains/recruitment` | `features/recruitment` |
| curriculum/program | `modules/domains/academics/curriculum` | `features/academics` |
| groups/enrollment | `modules/domains/academics/groups` | `features/academics` |
| schedules/reflow/office hours | `modules/domains/academics/timetable` | `features/academics/timetable` |
| lesson overrides | `modules/domains/academics/lessons` | timetable details UI |
| attendance | `modules/domains/academics/attendance` | `features/academics/gradebook` |
| homework/rewards/trends | `modules/domains/academics/gradebook` | `features/academics/gradebook` |
| exams | `modules/domains/academics/assessments` | Gradebook exam view |
| holiday closures | `modules/domains/academics/calendar` | timetable closure UI |
| learning resources | `modules/domains/academics/resources` | `features/academics/resources` |
| payments | `modules/domains/finance` | `features/finance` |
| admissions, contracts, and first invoices | `modules/domains/admissions` | `features/customer-support/admissions`, `workspaces/public_admission` |
| support tickets | `modules/domains/support_cases/tickets` | `features/support` |
| announcements/chat | `modules/domains/communications` | `features/communications` |
| dashboards/read models | `modules/domains/reporting` | `features/reporting` |
| shared API/web/runtime infrastructure | `core/api`, `core/web`, `core/runtime` | n/a |
| storage, Redis, Telegram adapter | `platform` | n/a |

## Table Ownership

| Owner | Principal tables |
| --- | --- |
| Identity | `accounts`, `account_telegram_links`, `student_auth`, `staff_profiles`, `msi_staff`, `staff_subject_scopes`, `audit_events` |
| Organization | `schools`, `subjects`, `classes`, `class_students` |
| Student Records | `students`, `student_profiles` |
| Parent Relationships | `parents`, `parent_profiles`, parent links/invites |
| Teacher Records | `teachers`, `teacher_profiles` |
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
| Admissions | `admissions`, `admission_group_selections`, `admission_access_tokens`, `admission_contracts`, `invoices`, `invoice_lines`, `invoice_payments`, `payme_transactions` |
| Finance | legacy `payments`; admission invoices are owned by Admissions and exposed through Finance compatibility reads |
| Support Cases | complaint/support tables |
| Communications | announcement and chat tables |
| Reporting | no transactional ownership; read-only projections |

When one physical table serves closely related academic concerns, the write contract is owned by the row's domain service; other domains consume a public read contract.

## Recruitment Internal Map

`modules/domains/recruitment/service.py` and `repository.py` are compatibility facades that preserve existing imports and API behavior. New Recruitment work belongs in the focused owner:

| Capability | Service owner | Persistence owner |
| --- | --- | --- |
| candidate lifecycle and profiles | `candidates/service.py`, `candidates/read_service.py` | `candidates/repository.py`, `candidates/read_repository.py` |
| appointments and interview sessions | `appointments/service.py` | `appointments/repository.py` |
| interview, test, and demo evaluations | `evaluations/service.py` | `evaluations/repository.py` |
| approvals and final decisions | `decisions/service.py` | `decisions/repository.py` |
| candidate documents | `documents/service.py` | `documents/repository.py` |
| Academy and active-teacher handoffs | `handoffs/service.py` | `handoffs/intake_repository.py`, `handoffs/lifecycle_repository.py` |
| tasks and assignments | compatibility service facade | `tasks/repository.py` |
| settings and options | compatibility service facade | `settings_repository.py` |
| browser appointment reminders | `notifications.py` | `notification_repository.py` |

Recruitment browser reminders remain client-claimed for compatibility. New durable background work uses
`msi_v2.outbox_jobs` and the PostgreSQL-backed worker; reminder delivery will move behind a typed job
handler when that compatibility surface is migrated.

## Customer Support Internal Map

The Customer Support person module composes reusable domain contracts. Its
`module.py` records a separate domain allowlist and capability set for each
section.

| Section | Person orchestration | Domain boundary |
| --- | --- | --- |
| Dashboard | `people/customer_support/dashboard` | `reporting/customer_support` |
| Parents | `people/customer_support/parents` | `parent_relationships/support_contracts.py`, plus typed Student, Finance, and Support Cases contracts |
| Teachers | `people/customer_support/teachers` | `teacher_records/support_contracts.py` |
| Tickets | `people/customer_support/tickets` | `support_cases/tickets` |
| Admissions | `people/customer_support/admissions` | `admissions/contracts.py` |
| Payments | `people/customer_support/admissions` | `admissions/contracts.py`, plus Finance compatibility reads |

The current Customer Support workspace adapter and
`support_cases/customer_records_*` files remain compatibility boundaries.
New workflows must enter one of the focused packages above.

## Explicit Size Exceptions

These existing stateful orchestrators remain above the target threshold. The owning domain team must
not add another capability to one of these files before satisfying its removal condition:

| Existing exception | Owner | Removal condition |
|---|---|---|
| `features/academics/AcademicPanel.tsx` | Academics | Extract the next added panel into its own feature component. |
| `features/academics/gradebook/GroupGradebook.tsx` | Academics | Extract grading dialogs and bulk actions before adding another grade workflow. |
| `features/academics/timetable/SchedulePanel.tsx` | Academics | Extract the next schedule editor workflow. |
| `features/academics/timetable/Timetable.tsx` | Academics | Extract rendering and interaction controllers before another timetable mode. |
| `features/academics/timetable/ModernGroupTimetable.tsx` | Academics | Extract the next group timetable interaction. |
| `features/teacher-academy/TeacherAcademyPanel.tsx` | Teacher Academy | Move remaining orchestration state into capability hooks before another workflow. |
| `features/teacher-academy/TeacherAcademyWorkflowModals.tsx` | Teacher Academy | Split one component per modal family before adding a modal. |
| `features/recruitment/CandidateProfile.tsx` | Recruitment | Extract the remaining tab panels and form drawers before another profile subdomain. |
| `features/recruitment/ScheduleView.tsx` | Recruitment | Extract appointment editing before another calendar workflow. |
| `features/recruitment/PipelineView.tsx` | Recruitment | Extract stage columns and drag policy before another pipeline behavior. |
| `features/recruitment/AcademicCandidateListView.tsx` | Recruitment | Extract filters and bulk actions before another list workflow. |
| `features/recruitment/SettingsView.tsx` | Recruitment | Split each settings capability before adding a settings section. |
| `features/recruitment/AnalyticsView.tsx` | Recruitment | Extract each report card before adding a metric family. |
| workspace orchestrators | Application | Keep them transport-only and extract any business rule immediately. |
| `modules/people/student/dashboard.py` | Student | Split the next dashboard projection into a focused query module. |
| `platform/storage/r2.py` | Platform | Extract provider operations before adding another storage capability. |
| `modules/domains/recruitment/service.py` | Recruitment | Keep it as a compatibility facade; put every new use case in a focused command or query. |
| `modules/domains/recruitment/api.py` | Recruitment | Extract route groups before adding another Recruitment capability. |
| `modules/domains/recruitment/candidates/read_repository.py` | Recruitment | Split candidate list and candidate detail SQL before adding another read model. |
| `modules/domains/recruitment/evaluations/service.py` | Recruitment | Split rubric and submission commands before adding an evaluation type. |
| `modules/domains/reporting/recruitment/repository.py` | HR Analytics | Split each report family before adding another analytics query. |
| `modules/domains/support_cases/customer_records_service.py` | Support Cases | Split Student, Parent, and Payment commands before adding another support workflow. |
| `modules/domains/support_cases/customer_records_repository.py` | Support Cases | Move student, parent, and payment writes behind their owning domain contracts before adding another records workflow. |
| `modules/domains/admissions/contracts.py` | Admissions | Split admission commands and read projections after the initial Merchant sandbox is certified; no additional admission capability may be added here first. |
| `modules/domains/admissions/repository.py` | Admissions | Split contract, invoice, token, and activation persistence into focused repository files before adding another billing provider. |

No new backend domain implementation may exceed 800 lines and no new frontend feature component may exceed 600 lines without adding a named rationale here.

## Removed Owners

Do not import or recreate:

- old module packages: `accounts`, `complaints`, `learning_resources`, `parent_access`, `payments`, `staff_records`, `student_records`;
- academic catch-alls: `academics/operations.py`, `academics/service.py`, `academics/repository.py`;
- `backend/integrations` (use `backend/platform`);
- `frontend/src/features/management` and `frontend/src/features/accounts`;
- the former `backend/internal_operations` and `frontend/src/internal_operations` trees;
- generic backend `api`, `pages`, `services`, `repositories`, or `schemas` trees.

Future observations, interventions, payroll, and expanded finance capabilities remain documentation-only until implemented.
