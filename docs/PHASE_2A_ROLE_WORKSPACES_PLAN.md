# Phase 2A Role Workspaces Plan

Date: 2026-07-05  
Project: MSI LMS Portal  
Branch: FastAPI-Run-System

This is a planning document only. Do not implement code, refactor backend files, delete legacy code, change auth logic, or redesign frontend in Phase 2A planning.

## Current Checkpoint

- Auth V2 works for password login and Telegram login behind `ACCOUNT_AUTH_V2_ENABLED`.
- Legacy auth and legacy session compatibility remain active.
- Backend structure has started moving toward `backend/api/v1`, `backend/core`, and `backend/integrations`.
- `/api/v1/auth/me` and `/api/v1/system/status` were moved successfully.
- Current test suite passes: `148 passed`.
- Student dashboard, `/admin` compatibility, and existing role routes must stay stable.

## Goal

Define the first real role workspaces for:

- system_admin/admin
- ceo
- academic_director
- customer_support
- hr_manager
- teacher
- parent
- student

The first implementation should create stable workspace shells and connect real data role by role without forcing a full frontend redesign.

## Current Workspace Inventory

| Role | Current route path | Current frontend page/component | Current backend route/service | Data already available | Missing today | Minimum useful dashboard for v1 |
| --- | --- | --- | --- | --- | --- | --- |
| system_admin/admin | `/admin` | `frontend/src/roles/admin/pages/Admin.tsx` via `admin-home` | `backend/roles/admin/routes/admin_page.py`; service `backend/roles/admin/services/page_service.py`; many `/admin/api/*` routes | Admin overview, students, teachers, parents, complaints, payments routes, resources, announcements, academic context, teacher candidates, teacher academy, school/subject/group summaries | Dedicated `system_admin` route naming, shared accounts UI, audit/settings UI, clean split between business admin and technical system admin | Technical/admin tools, user/account management placeholder, settings/audit placeholder, existing admin tools preserved |
| ceo | `/ceo` | `frontend/src/roles/common/pages/RoleHome.tsx` via `ceo-home`; admin mode components exist under `frontend/src/roles/admin/modes/ceo/` | `backend/roles/ceo/routes.py` with `render_role_home()` | Role-guarded shell; admin context has schools, quick stats, students, teachers, complaints, academic summaries | Dedicated CEO data API; payment summary; company operations dashboard; audit logged drilldowns | Company overview, schools, student count, teacher count, payments summary placeholder, academic performance summary placeholder |
| academic_director | `/academic-director`; alias `/academic_director` | `frontend/src/roles/common/pages/RoleHome.tsx` via `academic-director-home` | `backend/roles/academic_director/routes.py` with `render_role_home()` | Role-guarded shell; admin academic context already has schools, subjects, groups, enrollments, lessons, schedules, sessions, curriculum programs/items | Dedicated academic director page/API; safe academic write permissions; overview cards from PostgreSQL | Groups/classes, teachers, subjects, attendance/AAP overview, exam/progress overview |
| customer_support | `/support`; alias `/customer-support` | `frontend/src/roles/common/pages/RoleHome.tsx` via `support-home`; support mode components exist under `frontend/src/roles/admin/modes/support/` | `backend/roles/customer_support/routes.py` with `render_role_home()` | Role-guarded shell; admin context has parents, complaints, students, payments routes, parent invite endpoint | Dedicated support API; support ticket domain separate from complaints; B2C-only permissions; payment/access policy integration | Parent list/search, payment/support status placeholder, parent invite links, student basic info |
| hr_manager | `/hr`; alias `/hr-manager` | `frontend/src/roles/common/pages/RoleHome.tsx` via `hr-home`; HR mode components exist under `frontend/src/roles/admin/modes/hr/` | `backend/roles/hr_manager/routes.py` with `render_role_home()` | Role-guarded shell; admin context has teacher candidates, teacher academy, active teachers | Dedicated HR API; candidate workflow ownership; academy dashboard separated from admin panel | Candidates, hiring stages, teacher academy placeholder, active teachers list |
| teacher | `/teacher` | `frontend/src/roles/teacher/pages/TeacherHome.tsx` via `teacher-home` | `backend/roles/teacher/routes.py`; service `backend/roles/teacher/services.py` | Teacher profile, assigned group gradebooks, students in groups, academy journey, lesson reports, training timetable, subject options, office-hour APIs | Teacher attendance/homework write flows, resources management, multi-group assignment model beyond assigned group matching | Assigned groups, students in groups, attendance/homework placeholder, resources placeholder |
| parent | `/parent`; child dashboard redirect `/parent/dashboard/{student_row_id}`; invite routes `/parent/invite/{code}`, `/parent/link/{token}` | `frontend/src/roles/parent/pages/ParentHome.tsx` via `parent-home` | `backend/roles/parent/routes.py`; service `backend/roles/parent/services.py` | Linked children, child academic indicators, recent lessons, payment summary, resources, announcements, parent invite flow, Telegram-first linking | Parent support contact/tickets, policy-controlled restriction messaging, richer payment status/actions, password login optional later | Linked children, attendance/progress, payment status placeholder, support contact |
| student | `/student` redirects to `/dashboard/{student_id}` when session has enrollment; dashboard routes under `/dashboard/{student_id}` | `frontend/src/roles/student/pages/*` via `student-dashboard`, `student-resources`, `student-rating`, `student-aap`, `student-ar`, `student-chat`, `student-office-hours` | `backend/roles/student/routes/student_page.py`; dashboard/resources/chat/office-hours route modules; services under `backend/roles/student/services/` | Own dashboard, attendance/progress, AAP/AR, resources, rating board, chat, office hours, activity heartbeat, password change | Payment/access policy display, cleaner `/student` workspace shell if no direct redirect, richer resource grouping | Own dashboard, attendance/progress, resources |

## Current Route Map

Current role entry routes:

```text
/admin
/ceo
/academic-director
/academic_director
/support
/customer-support
/hr
/hr-manager
/teacher
/parent
/student
/dashboard/{student_id}
```

Current important API/page routes already registered:

```text
/api/v1/auth/me
/api/v1/system/status
/admin/api/students
/admin/api/students/{student_row_id}/parent-invite
/admin/api/students/{student_row_id}/payments
/admin/api/student-payments/{payment_id}
/admin/api/academic/gradebook
/admin/api/academic/attendance
/admin/api/academic/homework
/admin/api/academic/exams
/admin/api/academic/lessons/{lesson_session_id}
/admin/api/complaints
/admin/api/resources
/teacher/api/office-hours/availability
/teacher/api/office-hours/bookings
/api/office-hours/availability
/api/office-hours/bookings
/api/resources/{resource_id}/comments
/api/chat/messages
```

Current frontend page names:

```text
admin-home
ceo-home
hr-home
support-home
academic-director-home
teacher-home
parent-home
student-home
student-dashboard
student-resources
student-rating
student-aap
student-ar
student-chat
student-office-hours
```

## MVP Workspace Definitions

### CEO

MVP:

- Company overview.
- Schools list/summary.
- Students count.
- Teachers count.
- Payments summary placeholder.
- Academic performance summary placeholder.

Current starting point:

- `/ceo` already exists and is role guarded.
- It currently renders a generic `RoleHome` shell.
- Some CEO-oriented React mode components exist inside the admin UI, but they are not yet mounted as the standalone CEO workspace.

Data source plan:

- Start with aggregated data already available through admin page services.
- Later introduce CEO-specific APIs under `/api/v1/workspaces/ceo/*`.
- Use placeholders for payments and academic performance until the payment policy and analytics blocks are formalized.

### Academic Director

MVP:

- Groups/classes.
- Teachers.
- Subjects.
- Attendance/AAP overview.
- Exam/progress overview.

Current starting point:

- `/academic-director` already exists and is role guarded.
- It currently renders a generic `RoleHome` shell.
- Admin academic services already expose schools, subjects, groups, enrollments, lessons, schedules, sessions, and curriculum data.

Data source plan:

- Reuse read-only academic context first.
- Do not grant structure-changing actions until permissions are explicit.
- Later add `/api/v1/workspaces/academic-director/*` endpoints for academic summaries and drilldowns.

### Customer Support

MVP:

- Parent list/search.
- Payment/support status placeholder.
- Parent invite links.
- Student basic info.

Current starting point:

- `/support` already exists and is role guarded.
- It currently renders a generic `RoleHome` shell.
- Support-oriented admin mode components exist.
- Parent invite generation exists at `/admin/api/students/{student_row_id}/parent-invite`.

Data source plan:

- Start with parent and student lookup data.
- Keep Customer Support B2C-only.
- Do not let Customer Support directly edit academic structure by default.
- Payment status should stay placeholder until the policy engine is ready.

### HR Manager

MVP:

- Candidates.
- Hiring stages.
- Teacher academy placeholder.
- Active teachers list.

Current starting point:

- `/hr` and `/hr-manager` already exist and are role guarded.
- It currently renders a generic `RoleHome` shell.
- Teacher candidates, active teachers, and teacher academy data already exist in admin services.

Data source plan:

- Reuse teacher candidate and academy read models first.
- Create dedicated HR workspace API later.
- Keep teacher account/profiles changes separated from hiring workflow until ownership is clear.

### Teacher

MVP:

- Assigned groups.
- Students in groups.
- Attendance/homework placeholder.
- Resources placeholder.

Current starting point:

- `/teacher` already exists and is role guarded.
- It renders `TeacherHome`.
- Current service `build_teacher_workspace()` provides teacher profile, assigned group gradebooks, academy journey, reports, timetable, and subject options.
- Office-hour APIs already exist under `/teacher/api/office-hours/*`.

Data source plan:

- Preserve current teacher dashboard.
- Later add attendance/homework actions behind explicit teacher permissions.
- Add resources view as read-only first.

### Parent

MVP:

- Linked children.
- Attendance/progress.
- Payment status placeholder.
- Support contact.

Current starting point:

- `/parent` already exists and is role guarded.
- It renders `ParentHome`.
- Parent invite/linking flow exists.
- Parent child dashboard redirect exists.
- Parent data includes linked children, academic indicators, recent lessons, resources, announcements, and a payment summary.

Data source plan:

- Preserve Telegram-first parent flow.
- Keep payment status as display/placeholder until payment access policy is implemented.
- Add support contact/ticket entry without exposing admin-only operations.

### Student

MVP:

- Own dashboard.
- Attendance/progress.
- Resources.

Current starting point:

- `/student` redirects to the student dashboard when the session has `student_enrollment_id`.
- Student dashboard routes are already substantial and should not be disturbed.
- Student pages cover dashboard, resources, rating, AAP, AR, chat, and office hours.

Data source plan:

- Preserve existing dashboard as the student v1 workspace.
- Do not rebuild student dashboard in Phase 2A.
- Later add payment/access messaging in a policy-controlled way.

### System Admin

MVP:

- Technical/admin tools.
- User/account management placeholder.
- Settings/audit placeholder.

Current starting point:

- `system_admin` currently reaches `/admin` through Auth V2 compatibility.
- Legacy admin route code still expects `auth_role == "admin"`.
- `/admin` renders the large admin panel with many business operations.

Data source plan:

- Do not break `/admin`.
- Keep `system_admin` compatibility until admin/business role separation is implemented.
- Add account management and audit placeholders first, then wire to `accounts`, profile tables, and `audit_events`.

## Route And API Plan

### Routes Already Existing

- Role shell/page routes already exist for CEO, Academic Director, Customer Support, HR Manager, Teacher, Parent, Student, and Admin.
- Student and Admin have the most complete route/API surface.
- Teacher and Parent have useful role-specific pages and data.
- CEO, Academic Director, Customer Support, and HR Manager are currently lightweight shells.

### New API Endpoints Needed

Target namespace:

```text
/api/v1/workspaces/system-admin/*
/api/v1/workspaces/ceo/*
/api/v1/workspaces/academic-director/*
/api/v1/workspaces/customer-support/*
/api/v1/workspaces/hr-manager/*
/api/v1/workspaces/teacher/*
/api/v1/workspaces/parent/*
/api/v1/workspaces/student/*
```

Suggested first endpoints:

| Endpoint | Purpose | First version |
| --- | --- | --- |
| `/api/v1/workspaces/ceo/summary` | Company overview | Counts plus placeholders |
| `/api/v1/workspaces/academic-director/summary` | Academic overview | Schools, subjects, groups, attendance/progress placeholders |
| `/api/v1/workspaces/customer-support/parents` | Parent search/list | Reuse parent account read model |
| `/api/v1/workspaces/customer-support/students` | Student basic search | Reuse admin student list safely |
| `/api/v1/workspaces/customer-support/parent-invites` | Generate parent invite links | Reuse existing invite logic with customer_support authorization |
| `/api/v1/workspaces/hr-manager/summary` | HR overview | Candidate counts, teacher counts, academy placeholder |
| `/api/v1/workspaces/teacher/summary` | Teacher workspace data | Wrap current teacher service later |
| `/api/v1/workspaces/parent/summary` | Parent workspace data | Wrap current parent page data later |
| `/api/v1/workspaces/system-admin/summary` | Technical admin overview | Placeholder first |

### Placeholder First

Safe placeholders:

- CEO payments summary.
- CEO academic performance summary.
- Academic Director attendance/AAP overview.
- Academic Director exam/progress overview.
- Customer Support payment/support status.
- HR Teacher Academy summary.
- Teacher attendance/homework controls.
- Teacher resources.
- Parent payment status/support contact.
- System Admin account/settings/audit cards.

Placeholders must be honest in UI copy and docs. They should not fake counts that are not available.

## Safety Rules

1. Do not break existing student dashboard.
2. Do not break `/admin` compatibility.
3. Do not remove legacy auth.
4. Do not require frontend redesign all at once.
5. Do not change Auth V2 cutover behavior in Phase 2A.
6. Do not change payment/access restrictions in workspace shell work.
7. Do not expose private student, parent, phone, Telegram, or raw grade data in logs/docs/tests.
8. Do not let Customer Support modify academic structure by default.
9. Do not let B2B unpaid school contracts block whole-school access automatically.
10. Keep PostgreSQL as source of truth; Excel/Sheets remain import/export only.

## Implementation Order

### Phase 2A-1: Route/Page Shell Stabilization

- Keep current route paths.
- Add or refine role workspace shells without moving high-risk student/admin behavior.
- Ensure every role has a route, page key, guard, and smoke test.
- Keep CEO, Academic Director, Customer Support, and HR Manager on low-risk shell pages first.

### Phase 2A-2: CEO Workspace Data

- Add CEO summary endpoint.
- Show company overview, schools, student count, teacher count, and placeholders.
- Keep drilldowns read-only first.

### Phase 2A-3: Academic Director Workspace Data

- Add academic summary endpoint.
- Show groups/classes, teachers, subjects, and progress placeholders.
- Reuse existing academic context read models.

### Phase 2A-4: Customer Support Workspace Data

- Add parent/student search endpoints.
- Add parent invite generation for approved support role.
- Keep payment/support status placeholder until payment policy exists.

### Phase 2A-5: HR Manager Workspace Data

- Add candidate and active teacher summaries.
- Surface teacher academy placeholder.
- Avoid changing teacher candidate workflows until tests cover them.

### Phase 2A-6: Teacher/Parent/Student Refinement

- After shell/data patterns are stable, refine teacher, parent, and student workspaces.
- Teacher: keep current dashboard, then add read-only resources and placeholders.
- Parent: keep Telegram-first flow, then add support contact/status.
- Student: preserve current dashboard and only add policy-driven payment/access messaging later.

### Phase 2A-7: System Admin Separation

- Keep `/admin` compatibility.
- Add system_admin placeholders for account management, settings, and audit.
- Do not split technical admin from business operations until Auth V2 is stable in production.

## Tests Needed

Authentication and routing:

- Each role can log in.
- Each role redirects to the correct workspace:
  - `system_admin` -> `/admin`
  - `ceo` -> `/ceo`
  - `academic_director` -> `/academic-director`
  - `customer_support` -> `/support`
  - `hr_manager` -> `/hr`
  - `teacher` -> `/teacher`
  - `parent` -> `/parent`
  - `student` -> own dashboard
- Each workspace route loads.
- Unauthorized roles cannot access the wrong workspace.
- `/api/v1/auth/me` still works.

Workspace shell tests:

- `data-react-page` matches expected page name.
- Page receives expected role/auth props.
- Placeholder cards render without private data.
- Route aliases continue to work where they already exist.

Data endpoint tests when APIs are added:

- CEO summary returns counts and placeholders.
- Academic Director summary returns academic read model safely.
- Customer Support parent/student search returns allowed fields only.
- Customer Support can generate parent invite links only when authorized.
- HR summary returns candidate/teacher counts.
- Teacher summary remains scoped to the logged-in teacher.
- Parent summary returns only linked children.
- Student summary returns only the logged-in student's data.

Regression tests:

- Existing student dashboard tests still pass.
- Existing `/admin` tests still pass.
- Existing Auth V2 tests still pass with flag on and off.
- Existing Telegram parent invite tests still pass.

## Mermaid Overview

```mermaid
flowchart TD
    Login[Login or Telegram Auth] --> Session[Legacy-compatible session payload]
    Session --> RoleRoute{Canonical role}
    RoleRoute -->|system_admin compatibility| Admin[/admin/]
    RoleRoute -->|ceo| CEO[/ceo/]
    RoleRoute -->|academic_director| AD[/academic-director/]
    RoleRoute -->|customer_support| Support[/support/]
    RoleRoute -->|hr_manager| HR[/hr/]
    RoleRoute -->|teacher| Teacher[/teacher/]
    RoleRoute -->|parent| Parent[/parent/]
    RoleRoute -->|student| Student[/dashboard/{student_id}/]

    CEO --> CEOApi[/api/v1/workspaces/ceo/summary/]
    AD --> ADApi[/api/v1/workspaces/academic-director/summary/]
    Support --> SupportApi[/api/v1/workspaces/customer-support/*/]
    HR --> HRApi[/api/v1/workspaces/hr-manager/summary/]
    Teacher --> TeacherExisting[Current teacher service]
    Parent --> ParentExisting[Current parent service]
    Student --> StudentExisting[Current student dashboard]
    Admin --> AdminExisting[Current admin compatibility]
```

## Key Risks

- `/admin` still depends on legacy `auth_role == "admin"` checks, while the canonical role is `system_admin`.
- Student dashboard is a mature flow and can regress if route/session fields change.
- Teacher workspace currently scopes by assigned group matching; future multi-group teaching needs a cleaner relationship model.
- Parent flow depends on Telegram invite behavior and should not be altered during workspace shell work.
- Customer Support needs B2C-only permissions; reusing admin panels directly could expose academic/admin actions.
- CEO broad visibility needs audit logging before deep drilldowns become powerful.
- Payment/access restrictions must be policy controlled and should not be hardcoded into route guards.
- Placeholder UI can confuse staff if it looks operational; labels must make current readiness clear.

## Open Decisions

- Should CEO and Academic Director use dedicated React pages immediately, or continue with the shared `RoleHome` component for the first shell?
- Which fields may Customer Support see in student search results?
- Who can generate parent invite links in the first workspace release: CEO, Academic Director, Customer Support, or all three?
- What is the first payment status source for parent/support dashboards before the full payment policy engine?
- Should system_admin get a separate `/system-admin` route later, or remain `/admin` until legacy cleanup?
- Which workspace should be the first production-facing non-admin role after student/parent/teacher: CEO, Academic Director, or Customer Support?
