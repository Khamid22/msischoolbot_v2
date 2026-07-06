# Phase 2A-3C System Admin Workspace Plan

Date: 2026-07-06  
Project: MSI LMS Portal  
Branch: FastAPI-Run-System

This is a planning document only. Do not implement code, change Account Authentication, change `/admin` compatibility, change the student dashboard, change parent Telegram flow, change database schema, or delete legacy code in this phase.

## Goal

Plan lightweight System Admin workspace cards inside the existing `/admin` compatibility surface.

The first implementation should be read-only and additive:

- Keep `/admin` as the entry point.
- Keep `system_admin` mapped into legacy admin compatibility.
- Add technical account-status cards without changing existing admin tools.
- Show placeholders if account-count data cannot be read.
- Do not create a new `/system-admin` route yet.

## 1. Current `/admin` Route Behavior

Current entry route:

- `GET /admin`
- Defined in `backend/domains/identity/routes.py`.
- Calls `render_admin_page(...)` when `current_auth_role() == "admin"`.
- Returns a 403 unauthorized response for any other authenticated role.
- Shows the login page when there is no authenticated role.

Current admin renderer:

- `backend/roles/admin/routes/admin_page.py`
- Function: `render_admin_page(...)`
- React page key: `admin-home`
- Frontend page: `frontend/src/roles/admin/pages/Admin.tsx`

Current route registration:

- `backend/server.py` calls `register_admin_page_routes(...)`.
- `register_admin_page_routes(...)` registers the legacy `/admin/*` and `/admin/api/*` routers.
- `register_student_page_routes(...)` receives `render_admin_page` and owns the `/admin` entry route through the identity/student route module.

Current behavior after rendering:

- `render_admin_page(...)` builds `page_context` through `build_admin_page_context(...)`.
- It also loads academic context through `list_admin_academic_context()`.
- It passes many existing props to `admin-home`, including students, teachers, parents, payments-related data, complaints, resources, announcements, academic structures, and quick stats.
- If `current_auth_role() == "admin"`, it updates `admin_last_panel` and `admin_last_school` in session.

## 2. Current `system_admin` Compatibility Behavior

Target product role:

- `system_admin` is the internal technical/operator role.
- It is not an LMS business role.

Current compatibility:

- Canonical role helpers map `system_admin` to dashboard path `/admin`.
- Account Authentication password login builds canonical session metadata:
  - `account_role = "system_admin"`
  - `canonical_role = "system_admin"`
  - `staff_role = "system_admin"`
  - `staff_id`
- For Phase 1C compatibility, Account Authentication also sets:
  - `auth_role = "admin"`
  - `admin_id = staff_id`
  - `admin_role = "owner"` or `"system_admin"`
  - `admin_is_owner`
  - `admin_last_panel = "overview"`
  - `admin_last_school = "all"`

Reason this must stay:

- Current `/admin` route and admin guards still check `auth_role == "admin"`.
- The legacy admin tools are not split into a separate System Admin workspace yet.
- Changing this mapping now would break `/admin`.

## 3. Current Admin Frontend/Page/Component

Current frontend page:

- `frontend/src/roles/admin/pages/Admin.tsx`

Current shared types:

- `frontend/src/roles/admin/shared.ts`
- `AdminPageProps`
- `AdminMode`
- tab definitions and mode profiles.

Current page behavior:

- Renders the large `admin-home` React workspace.
- Supports panels such as overview, students, parents, teachers, subjects, groups, schedule, announcements, resources, payments, complaints, chat, career growth, curriculum, gradebook, and office hours.
- Supports role-preview/mode behavior for CEO, HR, Customer Support, teacher, student, parent, and Academic Director.
- Does not yet have a dedicated technical System Admin shell.

Important frontend constraint:

- Do not redesign the admin panel deeply.
- Add an optional card row/panel only if the backend prop exists.
- If the prop is absent, existing `Admin.tsx` behavior should remain unchanged.

## 4. Data Already Available Safely

Existing `/admin` page context already provides:

- `adminStudents`
- `adminTeachers`
- `adminParents`
- `adminTeacherCandidates`
- `adminTeacherAcademy`
- `adminComplaints`
- `adminParentChildren`
- `adminQuickStats`
- `adminSchoolInfo`
- `adminSubjectInfo`
- `adminGroupZones`
- resource lists and resource type lists
- academic schools, subjects, groups, enrollments, lessons, schedules, sessions, curriculum programs/items
- announcements

Account-specific data available from Phase 1:

- `msi_v2.accounts`
- `msi_v2.account_telegram_links`
- `msi_v2.student_profiles`
- `msi_v2.teacher_profiles`
- `msi_v2.parent_profiles`
- `msi_v2.staff_profiles`
- `msi_v2.audit_events`

Safe first card sources:

- `msi_v2.accounts`: total, active, pending.
- `msi_v2.account_telegram_links`: active Telegram links.
- Optional later: `msi_v2.audit_events` count or recent events, but keep as placeholder in the first card phase.

Do not use:

- raw student names.
- parent phone numbers.
- Telegram IDs.
- password hashes.
- row-level grades.
- private migration reports.

## 5. Minimum Useful Cards

Add read-only System Admin cards to `/admin`.

### Total Accounts

Purpose:

- Show total shared account identities after Phase 1.

Suggested source:

```sql
SELECT COUNT(*) FROM msi_v2.accounts;
```

Fallback:

- `-`

### Active Accounts

Purpose:

- Show currently usable accounts.

Suggested source:

```sql
SELECT COUNT(*) FROM msi_v2.accounts WHERE status = 'active';
```

Fallback:

- `-`

### Pending Accounts

Purpose:

- Show accounts waiting for completion, especially Telegram-first parent accounts.

Suggested source:

```sql
SELECT COUNT(*) FROM msi_v2.accounts WHERE status = 'pending';
```

Fallback:

- `-`

### Telegram Links

Purpose:

- Show how many account identities are connected to Telegram.

Suggested source:

```sql
SELECT COUNT(*) FROM msi_v2.account_telegram_links WHERE status = 'active';
```

Fallback:

- `-`

### Audit/Settings Placeholder

Purpose:

- Signal future technical operator tools without adding risky write controls.

Recommended first version:

- label: `Audit / Settings`
- value: `Placeholder`
- detail: `technical tools later`

Do not implement yet:

- audit event browser.
- settings editor.
- account creation/editing.
- role reassignment.
- destructive database or migration actions.

## 6. What Must Remain Unchanged

The Phase 2A-3C implementation must not change:

- `/admin` route path.
- `/admin/continue`.
- `system_admin` dashboard path `/admin`.
- Account Authentication system_admin session compatibility.
- `auth_role = "admin"` compatibility for system_admin.
- canonical metadata such as `account_role` and `canonical_role`.
- legacy admin tools.
- existing admin panels.
- `/admin/*` route registration.
- `/admin/api/*` route registration.
- student dashboard embedding from admin.
- parent invite generation.
- parent Telegram linking.
- payment routes and behavior.
- academic write routes.
- database schema.

## 7. Safe Fallback Behavior If DB Is Unavailable

The System Admin card provider should fail closed into placeholders.

Planned behavior:

- If `msi_v2.accounts` cannot be queried, return all account-count cards with `-`.
- If `msi_v2.account_telegram_links` cannot be queried, return Telegram links as `-`.
- Audit/settings card remains `Placeholder`.
- Do not raise into `render_admin_page(...)`.
- Do not block `/admin` because account summary cards failed.
- Do not mutate session.
- Do not mark the admin page as failed unless existing admin page context fails independently.

Suggested helper for later implementation:

- `backend/roles/admin/system_admin_cards.py`
- function: `system_admin_workspace_cards()`
- output shape:

```text
[
  {label: "Total Accounts", value: "185", detail: "shared login identities"},
  {label: "Active Accounts", value: "181", detail: "usable accounts"},
  {label: "Pending Accounts", value: "3", detail: "waiting for activation/linking"},
  {label: "Telegram Links", value: "1", detail: "active linked accounts"},
  {label: "Audit / Settings", value: "Placeholder", detail: "technical tools later"}
]
```

Suggested backend integration:

- Build the cards inside `render_admin_page(...)` or `build_admin_page_context(...)`.
- Prefer a small independent helper called by `render_admin_page(...)` so failures do not affect the large admin context.
- Pass the cards to React as an optional prop such as `systemAdminCards`.

Suggested frontend integration:

- Add optional `systemAdminCards` to `AdminPageProps`.
- Render compact cards near the overview/top area.
- Only show these cards for:
  - `authRole == "admin"` with `canonicalRole/accountRole == "system_admin"` if that metadata is exposed later, or
  - legacy admin while compatibility remains, if the business approves showing technical cards to all legacy admin sessions.
- First implementation can show cards in `/admin` overview only, avoiding panel-wide UI changes.

Open display decision:

- Current `AdminPageProps` does not expose `accountRole` or `canonicalRole`.
- The implementation must decide whether to expose canonical role metadata to the frontend or show cards for all `/admin` sessions.
- Safer v1: show the card prop only when backend determines the session is system_admin-compatible, and keep frontend dumb.

## 8. Tests

Add tests only when implementation starts.

Required tests:

1. `system_admin`/admin can access `/admin`.
   - Use a signed session with `auth_role = "admin"`.
   - Include canonical metadata such as `account_role = "system_admin"` and `canonical_role = "system_admin"` where relevant.
   - Assert `/admin` returns `200` and renders `admin-home`.

2. Wrong role denied.
   - Use a non-admin role session.
   - Request `/admin` with JSON/XHR headers.
   - Assert existing 403 unauthorized behavior remains.

3. Existing `/admin` tools still registered.
   - Verify representative routes remain registered:
     - `/admin/api/students`
     - `/admin/api/academic/gradebook`
     - `/admin/api/announcements`
     - `/admin/api/complaints`
     - `/admin/api/resources`
     - `/admin/api/students/{student_row_id}/parent-invite`
     - `/admin/teachers`
     - `/admin/parent-children`

4. Cards show mocked counts.
   - Mock the system admin card provider to return safe fake counts.
   - Assert rendered bootstrap contains labels and count values.
   - Do not query the real database in unit tests.

5. DB failure returns placeholders.
   - Mock the card provider or connection to raise.
   - Assert `/admin` still renders.
   - Assert placeholder values are present.

6. Critical routes still registered.
   - `GET /`
   - `POST /login`
   - `POST /auth/telegram`
   - `GET /admin`
   - `GET /teacher`
   - `GET /parent`
   - `GET /api/v1/auth/me`

7. Auth compatibility remains.
   - Existing Phase 1C tests for system_admin password login and Telegram login must stay green.
   - `system_admin` must still redirect to `/admin`.

## Risks

- Current `/admin` is a mixed legacy business/admin/technical workspace; adding technical cards should not imply the full split is complete.
- Account Authentication currently writes `auth_role = "admin"` for system_admin. Removing that compatibility too early would break `/admin`.
- Account counts depend on Phase 1 account tables existing in the target database.
- Exposing canonical role metadata to the frontend may be useful, but it must not become a new authorization boundary by itself.
- Admin page context already loads many domains; card provider failures must remain isolated.
- The old admin UI is large, so UI changes should be compact and optional.

## Acceptance Criteria Before Implementation

Phase 2A-3C can be implemented only after this plan is approved.

The implementation is acceptable when:

- `/admin` compatibility remains unchanged.
- system_admin Account Authentication still reaches `/admin`.
- Legacy admin routes and APIs remain registered.
- No parent Telegram flow changes.
- No student dashboard changes.
- No database schema changes.
- Cards are read-only.
- DB failure returns placeholders.
- Full `python3 -m pytest` passes.
- Frontend type-check passes if `Admin.tsx` or admin types change.
