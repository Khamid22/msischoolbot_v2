# Phase 2A-3B Parent Workspace Cards Plan

Date: 2026-07-06  
Project: MSI LMS Portal  
Branch: FastAPI-Run-System

This is a planning document only. Do not implement code, change parent Telegram linking flow, change Auth V2, change the student dashboard, change `/admin` compatibility, change database schema, or delete legacy code in this phase.

## Goal

Add lightweight, read-only Parent workspace cards that summarize the data already available to the current parent portal.

The first implementation should be additive and safe:

- Use existing parent session fields.
- Use the existing linked-children payload where possible.
- Keep the Telegram invite/linking flow unchanged.
- Keep existing per-child academic and payment sections intact.
- Show placeholders when data is missing or unavailable.

## Safety Rules

1. Do not touch `/auth/telegram`.
2. Do not change `/parent/invite/{code}`, `/parent/link/{token}`, or parent invite token behavior.
3. Do not change `set_parent_session()` behavior.
4. Do not change student dashboard routes or `/parent/dashboard/{student_row_id}` redirect behavior.
5. Do not change Auth V2.
6. Do not change database schema.
7. Do not add payment enforcement or account restriction logic.
8. Do not expose private student, parent, phone, Telegram, or raw grade data in tests or docs.
9. Card data must fail closed into placeholders rather than breaking the parent page.

## 1. Current Parent Route Path And Page/Component

Current parent routes are implemented in `backend/roles/parent/routes.py`.

Workspace route:

- `GET /parent`

Child dashboard route:

- `GET /parent/dashboard/{student_row_id}`

Parent invite/linking routes:

- `GET /parent/invite/{code}`
- `GET /parent/link/{token}`
- `POST /parent/link/{token}`

Current React page:

- Frontend file: `frontend/src/roles/parent/pages/ParentHome.tsx`
- React page key: `parent-home`

Current route behavior:

- `/parent` is protected by `require_role("parent")`.
- `/parent` renders `parent-home` through `render_react_page()`.
- `/parent/dashboard/{student_row_id}` checks parent-child access first, then redirects to the existing student dashboard route.
- Invite/link routes are HTML pages and forms, not part of the React `parent-home` workspace shell.

## 2. Current Parent Session Fields

Session fields are set by `set_parent_session()` in `backend/utils/session.py`.

Current parent session fields:

- `auth_role = "parent"`
- `auth_login`
- `parent_id`
- `parent_full_name`
- `telegram_user_id`, when available

Compatibility details:

- `build_render_parent_page()` currently reads `parent_id` directly from `session`.
- It also reads `admin_id` for legacy parent/admin compatibility fallback.
- Auth V2 Telegram and legacy invite flows both need to keep producing the same compatible session shape.

## 3. Current Parent-Child Linking Data Source

Primary tables:

- `msi_v2.parents`
- `msi_v2.parent_student_links`
- `msi_v2.students`

Current service/query flow:

- `backend/roles/parent/routes.py`
  - calls `list_parent_client_children(parent_id)` for normal parent clients.
  - falls back to `list_parent_children(admin_id)` only for legacy compatibility if no parent children are found.
- `backend/roles/parent/services.py`
  - `list_parent_client_children(parent_id)`
  - `parent_can_access_student(parent_id, student_row_id)`
  - `resolve_parent_child_dashboard(student_row_id)`
- `backend/identity/parent_accounts.py`
  - `parent_children(parent_id)`
  - `link_parent_via_invite(...)`
  - `parent_from_telegram_user_id(...)`
- `database/queries/parent_account_queries.py`
  - `list_parent_client_child_rows(conn, parent_id)`
  - `get_parent_child_link(conn, parent_id, student_row_id)`
  - `get_parent_child_link_by_dashboard_id(conn, parent_id, dashboard_student_id)`

Important behavior:

- Parent-child links are resolved by `msi_v2.parents.id` and student legacy row id exposed as `student_row_id`.
- The student dashboard redirect uses `resolve_parent_child_dashboard()` and should not be changed in the card phase.
- Parent invite links create/update `msi_v2.parents` and activate `msi_v2.parent_student_links`.

## 4. Existing Data Already Available For Parent Dashboard

`build_render_parent_page()` currently passes these props to `ParentHome`:

- `authLogin`
- `parentChildren`
- `resourcesList`
- `adminAnnouncements`
- `currentSchool`
- `csrfToken`
- `logoutUrl`

Each child row can already include:

- student display fields, such as name, code, school, class.
- `academic_indicators`
- `recent_lessons`
- `payment_summary`

Existing frontend behavior in `ParentHome.tsx`:

- Shows a linked-child empty state when no children are present.
- Shows one `ChildStatsCard` per linked child.
- Per-child metrics already include AAP, attendance, exam, and progress.
- Per-child payment display already shows debt, due, and paid totals when summary values are present.
- Recent lessons are already listed per child when available.

Current safe card source:

- Prefer deriving parent summary cards from the existing `parentChildren` payload.
- Avoid adding new live queries in the first card implementation unless a small backend helper needs to normalize the existing payload.

## 5. Minimum Useful Cards

Add read-only cards above the current per-child list.

### Linked Children

Purpose:

- Show how many children are linked to the current parent account.

Source:

- `len(parentChildren)` from the already-rendered payload.

Fallback:

- `0` if no linked children.
- `-` if payload is invalid or unavailable.

### Attendance/Progress

Purpose:

- Give parents a lightweight summary before they inspect each child card.

Source options:

- Average attendance from child `academic_indicators[].ar`.
- Average progress from child `academic_indicators[].program_completion_rate`.

Recommended first version:

- Show a safe combined summary label such as `Progress`.
- Use `-` when there are no indicators.
- Do not expose raw row-level grades.

Fallback:

- `Placeholder` or `-` if no children, no indicators, or data is malformed.

### Payment Status

Purpose:

- Show that payment visibility is part of the parent workspace.

Current data:

- `payment_summary` may include debt, due, paid, currency, and program-progress-derived values.

Recommended first version:

- Use a conservative display:
  - `No debt` when all known debt/due totals are zero.
  - `Attention` when known debt or due totals are greater than zero.
  - `Placeholder` when payment summary is absent or policy is not ready.

Do not implement:

- payment blocking.
- payment buttons.
- warning generation.
- restriction policy.

### Support Contact

Purpose:

- Make support visible without introducing a ticket workflow yet.

Recommended first version:

- Static placeholder card:
  - label: `Support`
  - value: `Placeholder`
  - detail: `Customer Support contact later`

Do not implement:

- support ticket creation.
- Telegram support bot flow.
- parent messaging.

## 6. Safe Fallback Behavior

### If `parent_id` Is Missing

Current route guard only checks `auth_role == "parent"`, so a malformed session can still reach the page.

Planned behavior:

- Render the parent page safely.
- Use empty `parentChildren`.
- Show cards with:
  - linked children: `-` or `0`
  - attendance/progress: `-`
  - payment status: `Placeholder`
  - support contact: `Placeholder`
- Do not redirect or mutate the session in this card phase.

### If No Linked Children Exist

Current behavior:

- The page shows the existing empty-state message asking the parent to open the invite link in Telegram.

Planned behavior:

- Preserve the empty state.
- Cards may still render above the empty state only if they do not make the page noisier.
- Recommended first implementation: show no summary cards when there are no children, or show a small safe card row with `0` linked children and placeholders.

### If DB Is Unavailable

Current behavior:

- `build_render_parent_page()` catches exceptions around children, resources, and announcements and falls back to empty arrays.

Planned behavior:

- Keep that behavior.
- Card helper should accept invalid or empty payloads and return placeholders.
- Do not raise from card building.
- Do not add new uncaught DB calls for cards.

## 7. Proposed Implementation Shape For Later

Do not implement in this planning phase.

Suggested backend helper:

- `backend/roles/parent/workspace_cards.py`
- Main function:
  - `build_parent_workspace_cards(parent_id, children=None)`

Suggested output shape:

```text
[
  {label: "Linked Children", value: "2", detail: "active links", tone: "text-slate-900"},
  {label: "Progress", value: "74%", detail: "average child progress", tone: "text-blue-600"},
  {label: "Payment Status", value: "Placeholder", detail: "policy engine later", tone: "text-amber-700"},
  {label: "Support", value: "Placeholder", detail: "Customer Support contact later", tone: "text-emerald-700"}
]
```

Suggested route integration:

- In `build_render_parent_page()`, build cards after `children` is resolved.
- Pass cards as `workspaceCards` to `ParentHome`.
- Keep all existing props unchanged.
- Do not change parent invite routes.
- Do not change parent child dashboard route.

Suggested frontend integration:

- Add an optional `workspaceCards` prop to `ParentHome`.
- Render a compact summary card row above the current child statistics list.
- If `workspaceCards` is absent, keep current page behavior unchanged.

## 8. Tests

Add tests only when implementation starts.

Required tests:

1. Parent route loads for parent.
   - Set a signed session with `auth_role = "parent"` and `parent_id`.
   - Mock child/resource/announcement services.
   - Assert `/parent` returns `200` and renders `parent-home`.

2. Wrong role denied.
   - Set a non-parent role.
   - Assert `/parent` returns the existing unauthorized/redirect style from `require_role("parent")`.

3. Unauthenticated denied.
   - No session.
   - Assert `/parent` returns the existing authentication-required response.

4. Linked children count works with mocked data.
   - Mock `list_parent_client_children()` to return two safe fake child dictionaries.
   - Assert card payload or rendered HTML includes linked children count.
   - Do not use real child names or private data.

5. DB failure returns placeholders.
   - Mock `list_parent_client_children()` to raise.
   - Assert `/parent` still renders safely.
   - Assert placeholder card values are present if cards render.

6. Existing critical routes still registered.
   - `GET /`
   - `POST /login`
   - `POST /auth/telegram`
   - `GET /admin`
   - `GET /teacher`
   - `GET /parent`
   - `GET /api/v1/auth/me`

7. Parent invite/linking routes remain registered.
   - `GET /parent/invite/{code}`
   - `GET /parent/link/{token}`
   - `POST /parent/link/{token}`
   - `GET /parent/dashboard/{student_row_id}`

8. Telegram flow regression guard.
   - Existing Phase 1C Telegram route tests must continue passing.
   - Parent invite `start_param` behavior must remain first in `/auth/telegram`.

## Risks

- Parent route currently catches DB failures and returns empty children; summary cards must not accidentally turn this into an error.
- Parent page already renders detailed child cards; extra cards should not duplicate too much information or clutter the Telegram Mini App view.
- `payment_summary` exists, but payment/access restriction policy is not complete. Payment card wording must stay informational or placeholder.
- Existing parent route has legacy `admin_id` fallback. The card helper must not confuse parent-client records with admin compatibility.
- Tests must avoid real student names, parent phone numbers, Telegram IDs, and raw grade rows.

## Acceptance Criteria Before Implementation

Implementation can start only after this plan is approved.

Phase 2A-3B is acceptable when:

- No parent Telegram linking code changes.
- No Auth V2 changes.
- No student dashboard changes.
- No database schema changes.
- `/parent` still renders for parent sessions.
- Wrong roles and unauthenticated requests keep existing guard behavior.
- Existing empty state still works when no children are linked.
- DB failure renders placeholders safely.
- Full `python3 -m pytest` passes.
- Frontend type-check passes if `ParentHome.tsx` changes.
