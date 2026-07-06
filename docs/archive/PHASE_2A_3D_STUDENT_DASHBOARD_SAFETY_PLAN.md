# Phase 2A-3D Student Dashboard Safety Plan

Date: 2026-07-06  
Project: MSI LMS Portal  
Branch: FastAPI-Run-System

This is a planning document only. Do not implement code, change Account Authentication, change `/admin` compatibility, change parent Telegram flow, change database schema, delete legacy code, or deeply redesign the frontend in this phase.

## Goal

Review the current Student workspace/dashboard and define a safe improvement path.

The Student dashboard is already a working, user-facing academic area. Phase 2A-3D should therefore be mostly safety review and test coverage. Any v1 improvement must be minimal, read-only, and based only on data already present in the current dashboard payload.

## 1. Current Student Routes And Pages

Student route registration starts in:

- `backend/roles/student/routes/student_page.py`

Registered route modules:

- `backend/roles/student/routes/students.py`
- `backend/roles/student/routes/dashboard.py`
- `backend/roles/student/routes/rating_board.py`
- `backend/roles/student/routes/resources.py`
- `backend/roles/student/routes/chat_page.py`
- `backend/roles/student/routes/chat_routes.py`
- `backend/roles/student/routes/comment_routes.py`
- `backend/roles/student/routes/office_hours_routes.py`

Current primary student routes:

| Route | Purpose | Frontend page |
| --- | --- | --- |
| `GET /student` | Student entry route; redirects to dashboard when session has enrollment id | `student-home` only when no enrollment redirect is possible |
| `POST /search` | Student-only form search by subject/group/student id | redirects to `/dashboard/{student_id}` |
| `POST /profile/password` | Student password change from dashboard modal | redirects back to dashboard or `/student` |
| `GET /dashboard/{student_id}` | Main academic dashboard | `student-dashboard` |
| `GET /dashboard/{student_id}/aap-lessons` | AAP lesson mastery | `student-aap` |
| `GET /dashboard/{student_id}/ar-lessons` | attendance by lesson | `student-ar` |
| `GET /dashboard/{student_id}/rating-board` | subject rating board | `student-rating` |
| `GET /dashboard/{student_id}/resources` | subject resources | `student-resources` |
| `GET /dashboard/{student_id}/chat` | student chat room | `student-chat` |
| `GET /dashboard/{student_id}/office-hours` | office-hour booking page | `student-office-hours` |
| `GET /api/students/{student_id}/dashboard` | JSON dashboard payload | API JSON |
| `GET /api/activity/ping` | student activity heartbeat | API JSON |
| `GET /api/metadata` | student home metadata | API JSON |
| `GET /api/students/search` | student search API | API JSON |

Current frontend student pages:

- `frontend/src/roles/student/pages/Home.tsx`
- `frontend/src/roles/student/pages/Dashboard.tsx`
- `frontend/src/roles/student/pages/AAP.tsx`
- `frontend/src/roles/student/pages/AR.tsx`
- `frontend/src/roles/student/pages/Rating.tsx`
- `frontend/src/roles/student/pages/Resources.tsx`
- `frontend/src/roles/student/pages/Chat.tsx`
- `frontend/src/roles/student/pages/OfficeHours.tsx`
- `frontend/src/roles/student/pages/Login.tsx`
- `frontend/src/roles/student/pages/StudentNotFound.tsx`

Current dashboard page behavior:

- `Dashboard.tsx` already renders program progress and summary cards for:
  - AAP
  - AR
  - EP
  - Coins
- The dashboard also lazy-loads charts through `DashboardChartsSection`.
- The page supports admin embedded mode through `AdminEmbedLayout` and `embed=admin`.

## 2. Current Data Sources And Services

Shared student payload access:

- `backend/roles/student/services/payload_service.py`
- Function: `load_student_payload_for_view(...)`

Dashboard context:

- `backend/roles/student/services/dashboard_service.py`
- Function: `build_dashboard_page_context(...)`

Academic payload loader:

- `backend/domains/academics/rating_service.py`
- Function: `load_dashboard_payload(...)`
- It first reads PostgreSQL through `get_enrollment_dashboard(...)`.
- It falls back to cached/group dataset data only when needed.

PostgreSQL dashboard source:

- `backend/domains/academics/internal_dashboard_service.py`
- Function: `get_enrollment_dashboard(public_dashboard_id, school_code="", subject_name="", group_name="")`
- Uses:
  - `msi_v2.students`
  - `msi_v2.group_students`
  - `msi_v2.groups`
  - `msi_v2.schools`
  - `msi_v2.subject_programs`
  - `msi_v2.subjects`
  - `msi_v2.attendance_records`
  - `msi_v2.homework_scores`
  - `msi_v2.exam_results`
  - `msi_v2.coin_events`
  - `msi_v2.lesson_sessions`
  - `msi_v2.subject_program_items`

Subject switcher source:

- Primary: `get_student_subject_enrollments(public_dashboard_id)`
- Fallback: loaded dataset matching.

Parent dashboard access source:

- `backend/roles/parent/routes.py`
- `GET /parent/dashboard/{student_row_id}`
- `backend/roles/parent/services.py`
  - `parent_can_access_student(parent_id, student_row_id)`
  - `resolve_parent_child_dashboard(student_row_id)`
  - `parent_can_access_dashboard(parent_id, dashboard_student_id)`

Admin embedded dashboard source:

- `backend/roles/admin/routes/student_routes.py`
- `/admin/students/{student_row_id}/dashboard`
- `/admin/students/{student_row_id}/dashboard/{target}`
- `backend/roles/admin/services/route_service.py`
  - `resolve_sheet_student_for_admin(student_row_id, get_admin_student_profile, ...)`

## 3. Current Student Session Fields

Student sessions are set by `set_student_session(...)` in `backend/utils/session.py`.

Current fields:

- `auth_role = "student"`
- `auth_login`
- `student_db_id`
- `student_id`
- `student_enrollment_id`, when available
- `student_full_name`
- `student_school_code`, when available
- `telegram_user_id`, when available

Important meaning:

- `student_db_id` is the internal student row id used for activity and student-owned actions.
- `student_enrollment_id` is the public dashboard id used in `/dashboard/{student_id}` URLs.
- `student_school_code` scopes default dashboard URLs when available.

## 4. Public Dashboard ID Behavior

Current URL behavior:

- The route parameter in `/dashboard/{student_id}` is a public dashboard/enrollment id, not the internal `msi_v2.students.id`.
- PostgreSQL resolves it through:
  - `COALESCE(group_students.legacy_public_dashboard_id, students.legacy_public_dashboard_id)`
- The dashboard query also requires active enrollment and excludes the `online` group in `get_enrollment_dashboard(...)`.

Why this is risky:

- The name `student_id` is misleading in routes and frontend props.
- It can be confused with:
  - `msi_v2.students.id`
  - `legacy_student_row_id`
  - `student_code`
  - `student_enrollment_id`
- Do not rename this in Phase 2A-3D. Any rename requires a compatibility plan and route tests.

## 5. Parent Return And Dashboard Access Behavior

Parent path:

- Parent opens `/parent/dashboard/{student_row_id}`.
- The route reads `parent_id` from the parent session.
- It verifies the parent-child link using `parent_can_access_student(parent_id, student_row_id)`.
- It resolves the child to a public dashboard id using `resolve_parent_child_dashboard(student_row_id)`.
- It redirects to `/dashboard/{public_dashboard_id}` with subject, group, school, and `parent_return=1`.

Dashboard access:

- `payload_service.load_student_payload_for_view(...)` checks `current_auth_role() == "parent"`.
- It validates `current_parent_id()`.
- It calls `parent_can_access_dashboard(parent_id, dashboard_student_id)`.
- If the dashboard id is not linked to the parent, the request is rejected.

Current dashboard back behavior:

- In `dashboard_service.build_dashboard_page_context(...)`, parent role sets:
  - `show_dashboard_back = True`
  - `dashboard_back_url = "/"`
- The `parent_return=1` query parameter is preserved by the URL helper, but current back behavior is primarily role/session based.

What must not change:

- Parent link verification.
- Parent dashboard redirect route.
- Parent Telegram linking flow.
- Parent session shape.
- `parent_return=1` compatibility.

## 6. Admin Embedded Student Dashboard Behavior

Admin path:

- `/admin/students/{student_row_id}/dashboard`
- `/admin/students/{student_row_id}/dashboard/{target}`

Current flow:

- Admin route resolves `student_row_id` to a public dashboard id through `resolve_sheet_student_for_admin(...)`.
- It redirects to the student page target with:
  - `student_id = public_dashboard_id`
  - `subject`
  - `group`
  - `school`
  - `admin_return_panel = students`
  - `admin_return_school`
  - `embed = admin`

Dashboard behavior:

- Student dashboard pages detect `embed=admin`.
- `Dashboard.tsx` uses `AdminEmbedLayout` in admin embedded mode.
- Subpage links preserve embed mode using `withEmbedMode(...)`.
- `dashboard_service.build_dashboard_page_context(...)` sets:
  - `show_dashboard_back = True`
  - `dashboard_back_url` back to admin home with panel/school.

What must not change:

- Admin redirect route paths.
- `embed=admin` behavior.
- `admin_return_panel` and `admin_return_school`.
- Admin route registration.
- Admin compatibility through `auth_role = "admin"`.

## 7. What Already Works

- Student password login redirects to `/dashboard/{student_enrollment_id}` when the session has an enrollment id.
- Student Telegram login through Account Authentication/legacy flow redirects to the current dashboard when linked.
- `/student` redirects to dashboard for valid student sessions.
- Dashboard, AAP, AR, rating, resources, chat, and office-hours pages share the same payload access service.
- Student dashboard ownership is checked by session enrollment id, not by name.
- Parent dashboard access is checked against parent-child links.
- Admin embedded dashboard resolves from student row id to public dashboard id.
- Subject switcher can use PostgreSQL enrollments first, with dataset fallback.
- Existing dashboard cards already show AAP, AR, EP, coins, and progress.
- Activity ping can repair stale `student_db_id` by enrollment id.

## 8. What Is Risky To Touch

- `/dashboard/{student_id}` URL shape.
- The meaning of route `student_id`.
- `student_enrollment_id` session behavior.
- `student_db_id` activity behavior.
- Parent access checks.
- Admin embedded dashboard redirects.
- Subject switcher logic for multi-subject students.
- `payload_service.load_student_payload_for_view(...)`, because it protects all student-facing dashboard pages.
- `get_enrollment_dashboard(...)`, because it builds the canonical PostgreSQL dashboard payload.
- Rating/global leaderboard logic, because it can load data across schools.
- Password change routes and CSRF behavior.

## 9. Minimum Safe v1 Improvement

Recommended Phase 2A-3D implementation, only after approval:

- Do not add new dashboard data sources.
- Do not add new schema.
- Do not change access logic.
- Do not rename routes.
- Do not change parent/admin redirects.
- If any visual change is made, only normalize or lightly polish existing summary cards already present in `Dashboard.tsx`.

Possible safe improvement:

- Add an optional, backend-shaped `studentSummaryCards` prop only if it is built entirely from the existing dashboard context:
  - AAP from `payload.averageGrade`
  - AR from `attendanceRate`
  - EP from `examPerformance`
  - Coins from `payload.coins`
  - Progress from `programCompletedRate`
- But this is mostly duplication because `Dashboard.tsx` already renders these cards.

Preferred first implementation:

- Add safety tests before any UI change.
- Keep the UI unchanged unless tests reveal a clear gap.

## 10. What Must Remain Unchanged

Phase 2A-3D must not change:

- Existing dashboard URLs.
- `/student` redirect behavior.
- `/dashboard/{student_id}` route.
- AAP/AR/rating/resources/chat/office-hours dashboard subroutes.
- Parent dashboard access.
- Parent Telegram linking.
- Admin embedded dashboard.
- `embed=admin`.
- `admin_return_panel` and `admin_return_school`.
- Student Telegram/login behavior.
- Account Authentication.
- `/admin` compatibility.
- Database schema.
- Legacy route aliases and route snapshot.

## 11. Safe Fallback Behavior If DB/Data Is Unavailable

Current behavior:

- `load_dashboard_payload(...)` returns `"Student dashboard was not found in internal academic data."` when no payload exists.
- `payload_service.load_student_payload_for_view(...)` converts missing/invalid/forbidden states into page-specific errors and status codes.
- Dashboard routes render `student-not-found` with a message and return URL on errors.
- Student metadata/search APIs return JSON error messages and status codes.

Required fallback behavior for any future improvement:

- Do not crash the dashboard page when optional summary data is missing.
- Show existing `student-not-found` page for missing payload.
- Keep 401 for invalid student/parent sessions.
- Keep 403 for ownership/access violations.
- Keep 503 for data load failures.
- For optional cards, use `-` or existing computed zero values when data is absent.
- Do not reveal whether an unrelated student exists when access is denied.

## 12. Tests Needed

Add tests before any Student dashboard UI or service change.

Required tests:

1. Student route loads/redirects.
   - Student session with `student_enrollment_id` redirects `/student` to `/dashboard/{student_enrollment_id}`.
   - Student session without enrollment renders `student-home` safely.

2. Student dashboard loads.
   - Mock `load_student_payload_for_view(...)` and dashboard context.
   - Assert `/dashboard/{student_id}` renders `student-dashboard`.
   - Assert existing summary values are present.

3. Student ownership is enforced.
   - Student session for enrollment A cannot open dashboard B.
   - Expected 403 student-not-found response remains.

4. Parent child dashboard access still works.
   - Linked parent route redirects from `/parent/dashboard/{student_row_id}` to `/dashboard/{public_dashboard_id}`.
   - Unlinked parent receives existing access-denied response.
   - Parent direct dashboard access uses `parent_can_access_dashboard(...)`.

5. Admin embedded dashboard still works.
   - `/admin/students/{student_row_id}/dashboard` redirects to `/dashboard/{public_dashboard_id}?embed=admin...`.
   - `/admin/students/{student_row_id}/dashboard/resources` or another target preserves `embed=admin`.
   - Embedded dashboard renders with `AdminEmbedLayout` behavior.

6. Wrong role denied where required.
   - Unauthenticated `/dashboard/{student_id}` still redirects home.
   - Non-owner student cannot access another dashboard.
   - Parent cannot access unlinked child dashboard.

7. Critical routes still registered.
   - `GET /`
   - `POST /login`
   - `POST /auth/telegram`
   - `GET /student`
   - `GET /dashboard/{student_id}`
   - `GET /dashboard/{student_id}/resources`
   - `GET /dashboard/{student_id}/chat`
   - `GET /dashboard/{student_id}/office-hours`
   - `GET /admin`
   - `GET /parent`
   - `GET /api/v1/auth/me`

8. Route snapshot remains stable.
   - `tests/test_route_snapshot.py` must pass unless a route change is explicitly approved.

9. Existing Phase 1C auth tests stay green.
   - Student password login.
   - Student Telegram login.
   - `record_student_activity()` calls.

## 13. Recommended Implementation Order Later

1. Add safety tests only.
2. Add a tiny student dashboard card provider only if needed.
3. Pass optional card data through the existing dashboard route.
4. Render optional cards without changing the current visual hierarchy.
5. Re-run full backend tests and frontend type-check.
6. Review parent/admin embedded flows manually before pushing.

## 14. Open Questions

- Should the route parameter name eventually become `dashboard_id` or `public_dashboard_id` in internal code while keeping the URL unchanged?
- Should `parent_return=1` become an explicit dashboard behavior, or should role-based parent back behavior remain enough?
- Should student summary cards be backend-shaped like teacher/parent/admin cards, or should the current frontend-computed cards remain the source of truth?
- Should payment/access restriction messaging appear on the student dashboard in a later payment-policy phase?
- Should the global rating board remain cross-school by default, or become school-scoped first?

## Acceptance Criteria Before Implementation

Phase 2A-3D implementation can start only after this plan is approved.

The implementation is acceptable when:

- Existing student dashboard URLs still work.
- Parent child dashboard access still works.
- Admin embedded dashboard still works.
- Student login and Telegram login still work.
- No access logic is weakened.
- No schema changes are made.
- No legacy code is deleted.
- Full `python3 -m pytest` passes.
- Frontend type-check passes if any frontend file changes.
