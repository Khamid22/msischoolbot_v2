# Phase 2A-3 Core User Workspaces Plan

Date: 2026-07-05  
Project: MSI LMS Portal  
Branch: FastAPI-Run-System

This is a planning document only. Do not implement code, change auth logic, deeply redesign frontend, delete legacy code, or change database schema in this phase.

## Goal

Plan safe next improvements for the core user workspaces:

- Teacher
- Parent
- Student
- System Admin

These are higher-risk than CEO, Academic Director, Customer Support, and HR Manager because they already contain working workflows, Telegram flows, embedded dashboards, and legacy admin compatibility.

## Safety Rules

1. Do not break the existing student dashboard.
2. Do not break parent Telegram invite/linking flow.
3. Do not break the teacher workspace.
4. Do not break `/admin` compatibility.
5. Do not remove legacy auth.
6. Do not change Account Authentication behavior in this phase.
7. Do not change database schema.
8. System Admin still uses admin compatibility for now.
9. Add read-only cards first; avoid new write actions until ownership and permissions are tested.
10. Keep placeholders explicit where business rules are not ready.

## Implementation Order Proposal

1. Teacher workspace cards first.
2. Parent workspace cards second.
3. System Admin technical shell third.
4. Student dashboard cleanup last.

Reasoning:

- Teacher already has scoped workspace data and is lower risk than student/admin.
- Parent already has useful child summary data, but the Telegram flow must be protected.
- System Admin should remain compatible with `/admin` until Account Authentication and account management are stable.
- Student dashboard is mature and central to current users, so it should be touched last.

## Teacher Workspace

### 1. Current Route Path

- `GET /teacher`
- Teacher office-hours APIs:
  - `GET /teacher/api/office-hours/availability`
  - `POST /teacher/api/office-hours/availability`
  - `PATCH /teacher/api/office-hours/availability/{availability_id}`
  - `GET /teacher/api/office-hours/bookings`
  - `PATCH /teacher/api/office-hours/bookings/{booking_id}`

### 2. Current Page/Rendering Behavior

- Backend route: `backend/roles/teacher/routes.py`
- Frontend page: `frontend/src/roles/teacher/pages/TeacherHome.tsx`
- React page key: `teacher-home`
- Access guard: `current_auth_role() == "teacher"`
- Unauthenticated/wrong non-AJAX request redirects to `/`.
- AJAX/API wrong-role request returns JSON with `Teacher authentication required.`

The page currently renders the teacher workspace with tabs such as home, lesson reports, timetable, career growth, and updates.

### 3. Existing Backend Service/Data Source

- Service: `backend/roles/teacher/services.py`
- Main function: `build_teacher_workspace(teacher_id, staff_id=None)`
- Reads from:
  - `msi_v2.teachers`
  - teacher account/profile helpers
  - `msi_v2.groups`
  - admin academic gradebook service
  - teacher academy service
  - office-hours service

Current route also loads subject options from `msi_v2.subjects` and `msi_v2.teacher_subjects`.

### 4. What Already Works

- Teacher login/session reaches `/teacher`.
- Teacher page receives teacher profile data.
- Teacher page receives assigned group gradebooks.
- Teacher can see students in assigned groups through gradebook payloads.
- Teacher academy journey, lesson reports, and training timetable can appear when available.
- Teacher office-hours APIs are registered and guarded.
- Teacher data is intended to be scoped to the logged-in teacher.

### 5. What Is Risky To Touch

- Teacher scoping currently depends heavily on `teacher_id`, `teacher_staff_id`, and assigned group matching.
- Multi-subject/multi-group teacher assignment is not fully normalized in the workspace yet.
- `build_teacher_workspace()` reuses admin academic services; changing those could affect admin gradebooks.
- Office-hours write APIs already exist and should not be altered while adding cards.
- The route currently performs a live DB query for subject options.

### 6. Minimum Useful v1 Cards/Data

Add read-only cards only:

- Assigned groups count.
- Students in assigned groups count.
- Lesson reports count.
- Upcoming office-hours or scheduled training count if available.
- Resources placeholder.
- Attendance/homework placeholder.

Suggested first card source:

- Use the existing `workspace["groups"]` payload.
- Count `groups`.
- Count unique enrollments/students across groups.
- Count `lessonReports`.
- Count `trainingTimetable`.

### 7. What Should Stay Placeholder For Now

- Teacher attendance entry.
- Teacher homework grading.
- Teacher resource management.
- Multi-group assignment editing.
- Payment/access messaging.
- Any write action outside current office-hours APIs.

### 8. Tests Needed

- Correct teacher session loads `/teacher`.
- Wrong role is rejected from `/teacher`.
- Unauthenticated teacher route behavior remains unchanged.
- Teacher cards render with fake workspace data.
- Teacher cards do not require a real DB in tests.
- Teacher API office-hours routes remain registered.
- Teacher workspace remains scoped to `teacher_id`.
- Existing teacher tests still pass.

## Parent Workspace

### 1. Current Route Path

- `GET /parent`
- `GET /parent/dashboard/{student_row_id}`
- Parent invite/linking:
  - `GET /parent/invite/{code}`
  - `GET /parent/link/{token}`
  - `POST /parent/link/{token}`

### 2. Current Page/Rendering Behavior

- Backend route: `backend/roles/parent/routes.py`
- Frontend page: `frontend/src/roles/parent/pages/ParentHome.tsx`
- React page key: `parent-home`
- Access guard: `require_role("parent")`
- Parent page is Telegram-friendly and renders linked children.
- Parent child dashboard route redirects to the student dashboard only if the parent can access that student.

The parent invite/link pages are HTML flows, not the same React workspace shell. They are tied to Telegram Mini App behavior.

### 3. Existing Backend Service/Data Source

- Parent route helper: `build_render_parent_page()`
- Parent service: `backend/roles/parent/services.py`
- Admin parent service fallback: `backend/roles/admin/services/parent_service.py`
- Invite helper: `backend/identity/parent_invites.py`
- Reads from:
  - `msi_v2.parents`
  - `msi_v2.parent_student_links`
  - `msi_v2.students`
  - academic indicator queries
  - payment summaries
  - resources service
  - announcements service

### 4. What Already Works

- Parent role reaches `/parent`.
- Parent page lists linked children.
- Parent page shows academic indicators per child when available.
- Parent page shows recent lessons when available.
- Parent page shows payment summary values when available.
- Parent page receives resources and announcements.
- Parent invite links can link a parent to a student.
- Telegram-first linking is already implemented.
- Parent can open a linked child dashboard through `/parent/dashboard/{student_row_id}`.

### 5. What Is Risky To Touch

- Telegram Mini App start parameter behavior.
- Parent invite token/code behavior.
- Session setup through `set_parent_session`.
- Parent child access checks.
- Parent dashboard redirect to student dashboard.
- Payment summary shape used by frontend.
- Fallback behavior using `admin_id` for legacy parent/admin compatibility.

### 6. Minimum Useful v1 Cards/Data

Add read-only cards only:

- Linked children count.
- Average attendance/progress summary across linked children.
- Open payment/debt summary if already present.
- Recent lessons count.
- Support contact placeholder.

Suggested first card source:

- Use the existing `parentChildren` payload already passed to `ParentHome`.
- Count children.
- Derive average AAP/attendance/exam/progress from `academic_indicators`.
- Sum visible payment summary fields if present.

### 7. What Should Stay Placeholder For Now

- Parent support ticket creation.
- Payment action buttons.
- Account restriction/ban state.
- Parent password login.
- Parent profile editing.
- Any flow that changes invite/linking behavior.

### 8. Tests Needed

- Parent session loads `/parent`.
- Wrong role cannot access `/parent`.
- Parent with no linked children still gets a safe empty state.
- Parent with fake linked children renders summary cards.
- Parent child dashboard rejects unlinked child.
- Parent child dashboard redirects linked child correctly.
- Parent invite start/link routes still work.
- Telegram invite flow tests stay green.
- `/auth/telegram` behavior remains unchanged.

## Student Workspace

### 1. Current Route Path

- `GET /student`
- `POST /search`
- `POST /profile/password`
- `GET /dashboard/{student_id}`
- `GET /dashboard/{student_id}/aap-lessons`
- `GET /dashboard/{student_id}/ar-lessons`
- `GET /dashboard/{student_id}/rating-board`
- `GET /dashboard/{student_id}/resources`
- `GET /dashboard/{student_id}/chat`
- `GET /dashboard/{student_id}/office-hours`
- `GET /api/activity/ping`
- Student APIs for chat, resources comments, office-hours, and dashboard data.

### 2. Current Page/Rendering Behavior

- Backend route coordinator: `backend/roles/student/routes/student_page.py`
- Dashboard route: `backend/roles/student/routes/dashboard.py`
- Frontend pages:
  - `frontend/src/roles/student/pages/Dashboard.tsx`
  - `Resources.tsx`
  - `Rating.tsx`
  - `AAP.tsx`
  - `AR.tsx`
  - `Chat.tsx`
  - `OfficeHours.tsx`
  - `Home.tsx`
- React page keys include:
  - `student-dashboard`
  - `student-resources`
  - `student-rating`
  - `student-aap`
  - `student-ar`
  - `student-chat`
  - `student-office-hours`

`/student` redirects directly to `/dashboard/{student_enrollment_id}` when the session has an enrollment id.

### 3. Existing Backend Service/Data Source

- Dashboard services:
  - `backend/roles/student/services/dashboard_service.py`
  - `backend/roles/student/services/payload_service.py`
  - `backend/roles/student/services/page_service.py`
- Academic data:
  - PostgreSQL academic tables under `msi_v2`
  - internal dashboard service
  - rating service
  - resources service
  - announcements service
  - office-hours service

Session fields are important:

- `auth_role`
- `auth_login`
- `student_db_id`
- `student_enrollment_id`
- `student_school_code`

### 4. What Already Works

- Student login redirects to own dashboard.
- Account Authentication can create legacy-compatible student session payload.
- Student dashboard shows attendance/progress/exam/resource/navigation data.
- Subject switcher exists.
- AAP/AR pages exist.
- Rating board exists.
- Resources page exists.
- Chat and office-hours pages exist.
- Student activity tracking and heartbeat exist.
- Student password change flow exists.
- Admin/parent embedding paths reuse the dashboard.

### 5. What Is Risky To Touch

- Student dashboard payload shape.
- Session/enrollment id handling.
- Parent/admin embed behavior.
- Subject switching.
- Student activity heartbeat.
- Dashboard access checks.
- AAP/AR/rating/resources URLs.
- Current mobile layout and Telegram viewport behavior.

### 6. Minimum Useful v1 Cards/Data

The student dashboard already has the minimum useful v1 data:

- Attendance rate.
- Exam performance.
- Program progress.
- Homework/AAP data.
- Coins/rating.
- Resources link.
- Chat link.
- Office-hours link.
- Subject switcher.

Near-term improvement should be cleanup, not new structure:

- Add a small policy-safe payment/access notice placeholder only after payment policy is ready.
- Add clearer empty states where data is missing.
- Keep existing card data stable.

### 7. What Should Stay Placeholder For Now

- Payment/access restriction logic.
- Parent-facing payment actions.
- Adaptive learning.
- AI recommendations.
- Google Slides/resources automation.
- Full student workspace redesign.
- Any change that affects current dashboard authorization.

### 8. Tests Needed

- Student login redirects to own dashboard.
- `/student` redirects to own dashboard with enrollment session.
- Student cannot open another student's dashboard.
- Parent/admin embed behavior still works.
- Dashboard response includes `student-dashboard`.
- AAP/AR/rating/resources/chat/office-hours routes still load.
- Activity ping works and does not duplicate behavior.
- Subject switcher remains present when multiple enrollments exist.
- Existing student dashboard service tests remain green.

## System Admin Workspace

### 1. Current Route Path

- `GET /admin`
- Many existing admin routes and APIs under `/admin/*` and `/admin/api/*`.

Current Account Authentication behavior:

- Canonical account role is `system_admin`.
- Compatibility session sets `auth_role = "admin"` so legacy `/admin` routes keep working.
- Canonical metadata remains in session as `account_role` and `canonical_role`.

### 2. Current Page/Rendering Behavior

- Backend route: `backend/roles/admin/routes/admin_page.py`
- Frontend page: `frontend/src/roles/admin/pages/Admin.tsx`
- React page key: `admin-home`
- Access guard: `current_auth_role() == "admin"`
- Current admin panel renders a large operational UI.

The system_admin role does not yet have a separate `/system-admin` route.

### 3. Existing Backend Service/Data Source

- Main page context: `backend/roles/admin/services/page_service.py`
- Academic context: `backend/roles/admin/services/academic_service.py`
- Admin route modules:
  - students
  - teachers
  - parents
  - payments
  - complaints
  - resources
  - announcements
  - chat
  - office-hours
  - academic operations
- Shared accounts tables now exist:
  - `accounts`
  - `student_profiles`
  - `teacher_profiles`
  - `parent_profiles`
  - `staff_profiles`
  - `account_telegram_links`
  - `audit_events`

### 4. What Already Works

- `/admin` loads for legacy admin-compatible session.
- System admin Account Authentication redirects to `/admin`.
- Admin panel can manage existing operational data.
- Admin panel can access academic context, students, teachers, parents, resources, payments, complaints, and announcements.
- Existing tests cover admin route registration and system_admin compatibility.

### 5. What Is Risky To Touch

- Changing `auth_role = "admin"` compatibility before `/admin` is refactored.
- Splitting technical system admin from business admin too early.
- Moving admin APIs before route guards are fully covered.
- Introducing account management writes without audit tests.
- Touching payments, parent linking, or academic writes from a technical admin shell.
- Breaking admin embedded student dashboard behavior.

### 6. Minimum Useful v1 Cards/Data

Add a technical shell area or cards inside existing `/admin` compatibility:

- Total accounts count.
- Active accounts count.
- Pending parent accounts count.
- Telegram linked accounts count.
- Audit/events placeholder.
- Settings placeholder.

Suggested first implementation:

- Keep `/admin`.
- Add read-only system/admin cards into existing admin props or a new safe panel.
- Do not create `/system-admin` yet unless separately approved.

### 7. What Should Stay Placeholder For Now

- Account creation/editing UI.
- Role reassignment.
- Staff profile editing.
- Audit event explorer.
- Settings management.
- Production migration controls.
- Any destructive admin/database tool.

### 8. Tests Needed

- system_admin Account Authentication still redirects to `/admin`.
- system_admin session still includes canonical role metadata.
- `/admin` still loads with `auth_role = "admin"`.
- Non-admin roles cannot access `/admin`.
- System admin cards render with fake counts.
- Existing admin API route registration remains unchanged.
- Route snapshot stays stable unless a new route is explicitly approved.
- No legacy auth removal.

## Cross-Role Data Plan

Use read-only data functions first. Avoid schema changes.

Suggested future helpers:

- `backend/roles/teacher/summary.py`
- `backend/roles/parent/summary.py`
- `backend/roles/admin/system_summary.py`
- No new student summary helper until the existing dashboard code is stabilized and documented.

All helpers should:

- Fail closed to placeholders/empty values.
- Avoid logging private data.
- Return aggregate counts or already-authorized scoped data.
- Be unit-testable with fake data or monkeypatches.
- Not require a live database in route smoke tests.

## Route/API Plan

No new APIs are required for the first card pass.

Possible later APIs:

```text
GET /api/v1/workspaces/teacher/summary
GET /api/v1/workspaces/parent/summary
GET /api/v1/workspaces/system-admin/summary
```

Do not add student dashboard API changes in this phase. The current student dashboard routes should remain the source for the student page until a separate student-specific cleanup plan is approved.

## Acceptance Criteria Before Implementation

- Full test suite passes before and after each step.
- Teacher, Parent, Student, and `/admin` routes still load.
- Parent invite and Telegram flows remain unchanged.
- Account Authentication tests remain green.
- Route snapshot remains stable unless a new route is intentionally approved.
- New cards are read-only.
- New tests do not require real private data.
- No schema migration is created.

## Mermaid Flow

```mermaid
flowchart TD
    Auth[Account Authentication or legacy auth] --> Session[Legacy-compatible session]
    Session --> Teacher[/teacher/]
    Session --> Parent[/parent/]
    Session --> Student[/dashboard/{student_id}/]
    Session --> Admin[/admin compatibility/]

    Teacher --> TeacherData[Existing teacher workspace service]
    Parent --> ParentData[Existing parent child/service data]
    Student --> StudentData[Existing student dashboard payload]
    Admin --> AdminData[Existing admin page context]

    TeacherData --> TeacherCards[Teacher read-only cards first]
    ParentData --> ParentCards[Parent read-only cards second]
    AdminData --> SystemCards[System Admin technical shell third]
    StudentData --> StudentCleanup[Student cleanup last]
```

## Phase 2A-3 Proposed Steps

1. Add teacher read-only summary cards using existing `workspace` data.
2. Add tests for teacher route with monkeypatched workspace data.
3. Add parent read-only summary cards using existing `parentChildren` data.
4. Add tests for parent route with fake linked children.
5. Add system admin technical shell/cards inside existing `/admin` compatibility.
6. Add tests for system_admin compatibility and cards.
7. Document a separate student dashboard cleanup plan before touching student UI or payloads.
