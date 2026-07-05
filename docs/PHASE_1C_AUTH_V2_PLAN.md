# MSI LMS Portal - Phase 1C Auth V2 Plan

## Scope

Phase 1C introduces shared-account authentication behind a feature flag. It does not cut over auth by default, does not rebuild dashboards, does not redesign frontend pages, does not delete legacy auth/session tables, and does not implement payment/access policy.

Default behavior must stay legacy:

```text
ACCOUNT_AUTH_V2_ENABLED=0
```

When the flag is disabled, the current `/login` and `/auth/telegram` flows must behave exactly as they do now. When enabled locally, login and Telegram auth may resolve identities from `msi_v2.accounts` and compatibility profile tables, then write the same session fields current routes already expect.

## 1. Current Legacy Auth Flow

### Student Password Login

Current route: `backend/domains/identity/routes.py`, `POST /login`.

Current service path:

```text
/login
  -> detect_login_role(login)
  -> role_hint == "student" when login starts with MSI
  -> verify_student_credentials(login, password)
  -> database/cross_queries/student_queries.py:get_student_login_row()
  -> msi_v2.students + msi_v2.student_auth
  -> check_password_hash(student_auth.password_hash)
  -> optional verified Telegram initData link
  -> set_student_session()
  -> record_student_activity()
  -> redirect to /dashboard/{student_enrollment_id}
```

Important legacy shape:

- Login is `students.student_code`.
- Password hash is in `student_auth.password_hash`.
- The session `student_db_id` currently stores `students.legacy_student_row_id`, not the `students.id` primary key.
- `student_enrollment_id` comes from a public dashboard id resolved from active `group_students` or `students.legacy_public_dashboard_id`.
- Student activity updates `students.last_seen_at` by `legacy_student_row_id`.

### Teacher Password Login

Current route: `backend/domains/identity/routes.py`, `POST /login`.

Current service path:

```text
/login
  -> detect_login_role(login)
  -> role_hint == "teacher" when login starts with TCH or old subject-teacher pattern
  -> verify_teacher_credentials(login, password)
  -> database/queries/teacher_queries.py:get_teacher_login_row()
  -> msi_v2.msi_staff role=teacher + msi_v2.teachers + group assignment
  -> check_password_hash(msi_staff.password_hash)
  -> set_teacher_session()
  -> redirect /teacher
```

Important legacy shape:

- Current teacher credentials still read from `msi_staff`.
- Phase 1B generated new `TCH0001` style accounts, but legacy login code is still active.
- Teacher workspace depends on both `teacher_id` and sometimes `teacher_staff_id`.

### Staff And System Admin Login

Current route: `backend/domains/identity/routes.py`, `POST /login`.

Current service path:

```text
/login
  -> detect_login_role(login)
  -> role_hint == "admin" when login is admin or starts with staff
  -> verify_admin_credentials(login, password)
  -> database/queries/admin_queries.py:get_admin_credentials_row()
  -> msi_v2.msi_staff
  -> check_password_hash(msi_staff.password_hash)
  -> reject disabled rows
  -> set_admin_session()
  -> redirect based on normalized role
```

Current `set_admin_session()` supports:

- legacy `admin`
- `ceo`
- `hr_manager`
- `customer_support`
- legacy `parent`
- `academic_director`

The route `/admin` is still guarded by `current_auth_role() == "admin"`, so `system_admin` needs temporary compatibility with legacy admin routes during Phase 1C.

### Parent Telegram Login

Current parent login is Telegram-first through the parent invite flow and `msi_v2.parents`.

Current service path:

```text
/auth/telegram
  -> verify Telegram initData HMAC
  -> if start_param starts with parent_:
       load invite payload
       link_parent_via_invite()
       set_parent_session()
       redirect /parent
  -> else parent_from_telegram_user_id()
       set_parent_session()
       redirect /parent
```

Important legacy shape:

- Parent web password login is not part of the first rebuild.
- Parent portal expects `auth_role=parent` and `parent_id`.
- Existing parent invite routes must keep working even if account auth is enabled.

### Telegram `/auth/telegram` Flow

Current route: `backend/domains/identity/routes.py`, `POST /auth/telegram`.

Current ordering:

```text
verify signed initData
parse telegram_user_id, username, full_name, start_param
try parent invite link from start_param
try teacher by msi_staff.telegram_user_id
try staff by msi_staff.telegram_user_id
try parent by parents.telegram_user_id
try student by students.telegram_user_id
return linked=false when no identity found
```

This route is exempt from same-origin session-cookie gating because it trusts only HMAC-validated Telegram `initData`.

### Session Fields Currently Used By Routes

Current routes read session state through `backend/utils/session.py`.

| Field | Current Use |
|---|---|
| `auth_role` | Primary role gate for routes. |
| `auth_login` | Display/login metadata and `/api/v1/auth/me`. |
| `staff_id` | Staff identity for staff-like sessions. |
| `staff_role` | Staff role metadata. |
| `admin_id` | Legacy admin routes and legacy parent-client compatibility. |
| `admin_role` | Legacy owner/admin distinction. |
| `admin_is_owner` | Legacy owner flag. |
| `admin_last_panel` | Admin panel state. |
| `admin_last_school` | Admin school filter state. |
| `student_db_id` | Current student row id, practically `students.legacy_student_row_id`. |
| `student_id` | Student code display value. |
| `student_enrollment_id` | Public dashboard route id. |
| `student_full_name` | Student display name. |
| `student_school_code` | Student dashboard query scoping. |
| `teacher_id` | `msi_v2.teachers.id`. |
| `teacher_staff_id` | `msi_v2.msi_staff.id` for teacher workspace compatibility. |
| `teacher_full_name` | Teacher display name. |
| `teacher_group` | Current assigned group string. |
| `parent_id` | `msi_v2.parents.id`. |
| `parent_full_name` | Parent display name. |
| `telegram_user_id` | Telegram identity for Telegram-linked sessions. |

## 2. New Account Auth Flow

### Password Login With Accounts

When `ACCOUNT_AUTH_V2_ENABLED=1`, password login should use the shared account table first.

```text
/login
  -> validate CSRF exactly as today
  -> normalize login with lower(btrim(login))
  -> SELECT account WHERE lower(btrim(accounts.login)) = lower(btrim(input))
  -> reject missing account
  -> reject unknown role
  -> reject status disabled/archived/pending for normal password login
  -> verify password_hash with the existing password hash verifier
  -> load exactly one role profile
  -> build legacy-compatible session fields
  -> redirect using existing dashboard_path_for_role/build_dashboard_url
```

The account row is canonical for:

- `account_id`
- `auth_login`
- `auth_role`, with a temporary exception for `system_admin` route compatibility
- account `status`

The profile row is canonical for route compatibility IDs:

- student: `student_profiles`
- teacher: `teacher_profiles`
- parent: `parent_profiles`
- staff/system roles: `staff_profiles`

### Status Rules

Recommended Phase 1C status policy:

| Account Status | Password Login | Telegram Login |
|---|---|---|
| `active` | Allow when password/profile are valid. | Allow when link is active and profile is valid. |
| `pending` | Reject normal password login. | Allow only for explicit parent invite/link completion path if business rules require it; otherwise reject. |
| `disabled` | Reject. | Reject. |
| `archived` | Reject. | Reject. |

Parents without Telegram were migrated as `pending` with `NULL` login and no Telegram link. They cannot log in normally.

### Profile Loading

After account lookup:

```text
role student
  -> student_profiles.account_id
  -> msi_v2.students by student_profiles.student_id
  -> active enrollment/public dashboard id for student_enrollment_id

role teacher
  -> teacher_profiles.account_id
  -> msi_v2.teachers by teacher_profiles.teacher_id
  -> optional msi_staff by legacy source/staff mapping for teacher_staff_id

role parent
  -> parent_profiles.account_id
  -> msi_v2.parents by parent_profiles.parent_id

role system_admin, ceo, hr_manager, customer_support, academic_director
  -> staff_profiles.account_id
  -> msi_v2.msi_staff by staff_profiles.staff_id when available
```

The account auth service should fail closed if the account role and loaded profile table do not match.

## 3. Feature Flag Design

### Flag

```text
ACCOUNT_AUTH_V2_ENABLED=0
```

Default must be disabled. Missing, empty, `0`, `false`, `no`, and `off` should all mean disabled.

### Disabled Behavior

When disabled:

- `POST /login` uses existing `detect_login_role()`, `verify_*_credentials()`, and `set_*_session()` paths.
- `POST /auth/telegram` uses existing legacy lookup order.
- No query should read `msi_v2.accounts` during login.
- No session field shape changes.
- Existing tests for legacy routes should continue to pass unchanged.

### Enabled Behavior

When enabled:

- `POST /login` delegates to a new account auth service.
- `POST /auth/telegram` delegates to a new account Telegram auth service, while preserving parent invite linking.
- Sessions are still written in the current compatibility shape.
- Dashboard rendering and route guards stay unchanged.

### Rollback Plan

Rollback is configuration-only:

```text
ACCOUNT_AUTH_V2_ENABLED=0
```

This should immediately restore legacy login and Telegram lookup behavior without database rollback. Since legacy auth tables remain untouched, rollback does not require dropping accounts tables or undoing Phase 1B data.

## 4. Session Compatibility

Auth V2 must populate existing session fields so current routes continue working.

| Field | Auth V2 Source |
|---|---|
| `auth_role` | Canonical `accounts.role`, except `system_admin` may be written as `admin` for legacy `/admin` route compatibility in Phase 1C. |
| `auth_login` | `accounts.login` when present; fallback to student code, teacher code, parent display label, or staff login. |
| `account_id` | `accounts.id`, new additive field. Existing routes should ignore it for now. |
| `student_db_id` | Existing route-compatible student row id. Prefer `students.legacy_student_row_id`; do not silently switch to `students.id`. |
| `student_enrollment_id` | Existing public dashboard id from active enrollment or `students.legacy_public_dashboard_id`. Required for student dashboard redirect. |
| `teacher_id` | `teacher_profiles.teacher_id`. |
| `teacher_staff_id` | Current `msi_staff.id` if resolvable. Required by some teacher workspace logic. |
| `parent_id` | `parent_profiles.parent_id`. |
| `staff_id` | `staff_profiles.staff_id` when available. |
| `admin_id` | For `system_admin` compatibility only, set from `staff_profiles.staff_id` or legacy admin id if current admin routes require it. |
| `admin_role` | For `system_admin` compatibility, use `owner` or `system_admin` mapping as needed by legacy admin code. |

Recommended Phase 1C compatibility choices:

- For `system_admin`, set `auth_role="admin"` plus `account_id`, `staff_id`, and `staff_role="system_admin"` so legacy `/admin` routes work.
- Also keep enough metadata to know the canonical account role, for example `account_role="system_admin"` or `canonical_role="system_admin"`. This is additive and should not be used by old guards yet.
- For business roles (`ceo`, `hr_manager`, `customer_support`, `academic_director`), set `auth_role` directly to the account role.
- For student, teacher, and parent, use the existing `set_student_session()`, `set_teacher_session()`, and `set_parent_session()` style payloads, with `account_id` added after session initialization.

## 5. Role Mapping

| Account Role | Phase 1C Redirect/Workspace |
|---|---|
| `system_admin` | Temporary compatibility with legacy `/admin`. |
| `ceo` | `/ceo` |
| `hr_manager` | `/hr` |
| `customer_support` | `/support` |
| `academic_director` | `/academic-director` |
| `teacher` | `/teacher` |
| `student` | Existing student dashboard behavior, usually `/dashboard/{student_enrollment_id}`. |
| `parent` | `/parent` |

Unknown roles must fail closed and never become admin.

## 6. Telegram Account Auth

When `ACCOUNT_AUTH_V2_ENABLED=1`, `/auth/telegram` should use `account_telegram_links`.

```text
/auth/telegram
  -> verify Telegram initData exactly as today
  -> parse telegram_user_id/start_param
  -> if parent invite start_param exists:
       keep existing invite-link behavior
       ensure account/profile/link sync is planned or performed safely
       set parent-compatible session
  -> else lookup account_telegram_links.telegram_user_id
  -> require account_telegram_links.status = active
  -> load account
  -> require account.status = active
  -> load matching profile
  -> set compatibility session
  -> return existing JSON shape
```

Rules:

- Revoked links are rejected.
- Disabled/archived accounts are rejected.
- Pending parent accounts without Telegram links return `linked=false` or an explicit safe error; they do not become logged in.
- Parent invite linking must still work for Telegram Mini App startup.
- The existing Telegram Mini App startup JavaScript expects `/auth/telegram` to continue returning compatible JSON keys: `ok`, `linked`, `role`, `redirect`, and optionally `error`.
- The old Telegram lookup order should remain available behind flag off.

Open design point for implementation: parent invite linking currently creates/updates `msi_v2.parents` and `parent_student_links`. Auth V2 should either also create/update `accounts`, `parent_profiles`, and `account_telegram_links` for newly linked parents, or immediately fall back to a compatibility session for that invite event and leave account sync for a later small migration. The first option is cleaner, but must be designed as an idempotent additive write.

## 7. Tests Needed

### Feature Flag Tests

- Legacy password auth works when `ACCOUNT_AUTH_V2_ENABLED=0`.
- Legacy Telegram auth works when `ACCOUNT_AUTH_V2_ENABLED=0`.
- Account password auth is used when `ACCOUNT_AUTH_V2_ENABLED=1`.
- Account Telegram auth is used when `ACCOUNT_AUTH_V2_ENABLED=1`.
- Rollback to `ACCOUNT_AUTH_V2_ENABLED=0` restores legacy auth behavior.

### Password Login Tests

- Student logs in through `accounts` using MSI code and password.
- Teacher logs in through `accounts` using `TCH0001`.
- `system_admin` logs in and can still reach legacy `/admin`.
- CEO logs in and redirects to `/ceo`.
- HR Manager logs in and redirects to `/hr`.
- Customer Support logs in and redirects to `/support`.
- Academic Director logs in and redirects to `/academic-director`.
- Disabled student is rejected.
- Pending parent without Telegram cannot log in normally.
- Wrong role does not become admin.
- Unknown role is rejected.
- Missing profile for account role is rejected.
- Duplicate/ambiguous profile state fails closed.

### Telegram Tests

- `/auth/telegram` uses `account_telegram_links` when flag is on.
- Active Telegram link plus active account logs in.
- Revoked Telegram link is rejected.
- Disabled account is rejected.
- Pending parent without link is not logged in.
- Parent invite start param still links parent and returns `/parent`.
- Existing Telegram Mini App startup JSON shape is preserved.

### Compatibility Tests

- Existing dashboards still import/start.
- Student dashboard redirect still uses `student_enrollment_id`.
- Teacher workspace still receives `teacher_id` and `teacher_staff_id`.
- Parent portal still receives `parent_id`.
- `/api/v1/auth/me` still returns role and permissions.
- Legacy admin routes still work for system admin compatibility.

## 8. Implementation Files Likely Involved

Do not change these files yet. They are likely implementation touch points:

| File | Expected Phase 1C Use |
|---|---|
| `backend/domains/identity/routes.py` | Feature flag switch in `/login` and `/auth/telegram`. |
| `backend/domains/identity/service.py` | Facade exports for account auth service. |
| `backend/identity/account_auth_v2.py` or similar new file | New password auth service against `msi_v2.accounts`. |
| `backend/identity/account_telegram_auth_v2.py` or similar new file | New Telegram auth service against `account_telegram_links`. |
| `backend/utils/session.py` | Possibly add compatibility helpers that set account sessions without breaking old helpers. |
| `backend/identity/roles.py` | Verify role normalization and dashboard paths. |
| `backend/security/dependencies.py` | Confirm system admin/admin compatibility for API dependencies. |
| `backend/utils/guards.py` | Confirm route guard behavior; avoid broad changes if possible. |
| `backend/roles/parent/services.py` | Parent invite/account sync if Auth V2 links accounts during invite. |
| `database/queries/*` or new query module | Account/profile lookup queries. |
| `tests/test_phase1_accounts_foundation.py` | Existing foundation tests. |
| New `tests/test_phase1c_auth_v2.py` | Flag, password login, Telegram login, and compatibility tests. |
| `tests/test_role_routing.py` | Add or adjust system admin compatibility tests if needed. |

No frontend files should be needed in Phase 1C.

## 9. Risks

### Student Dashboard Enrollment Dependency

Current student dashboard behavior depends on `student_enrollment_id`, a public dashboard id. Auth V2 must not confuse this with `students.id` or `student_profiles.id`.

Mitigation:

- Add a dedicated account-auth query that resolves the same enrollment id logic as the legacy query.
- Test student login redirect exactly.

### Teacher Workspace Staff Dependency

Teacher workspace may depend on `teacher_staff_id`. The new `teacher_profiles` table stores `teacher_id` but not `staff_id`.

Mitigation:

- Resolve teacher staff row from `accounts.legacy_source_table/source_id`, `teacher_profiles.teacher_id`, or existing `msi_staff.teacher_id`.
- Preserve `teacher_staff_id` in session when available.

### Parent Flow Parent ID Dependency

Parent portal depends on `parent_id` from `msi_v2.parents`. A parent account without a `parent_profiles.parent_id` must fail closed.

Mitigation:

- Require `parent_profiles.parent_id` for parent login.
- Keep invite flow intact and explicitly test it.

### Admin Route Compatibility

Legacy `/admin` checks `current_auth_role() == "admin"`, but the target role is `system_admin`.

Mitigation:

- In Phase 1C only, either map `system_admin` session `auth_role` to `admin` with additive canonical role metadata, or adjust the admin guard to allow `system_admin` without rebuilding the admin routes.
- Prefer minimal compatibility to avoid dashboard changes.

### Telegram Auth Edge Cases

Telegram flows involve HMAC validation, parent invite start params, old linked users, revoked links, and pending parents.

Mitigation:

- Keep HMAC verification unchanged.
- Preserve JSON response shape.
- Add tests for active, revoked, missing, pending, and invite-link cases.

### Password Hash Compatibility

The existing system uses Werkzeug password hash verification. Accounts were migrated using existing `password_hash` values.

Mitigation:

- Reuse the same verifier in Phase 1C.
- Do not rehash or alter passwords in this phase.

## 10. Implementation Phases

### Phase 1C-1: Create Account Auth Service

- Add account lookup by normalized login.
- Verify password hash.
- Enforce account status.
- Load role-specific profile.
- Return a normalized auth result object.
- Do not wire routes yet except in tests or isolated service tests.

### Phase 1C-2: Feature Flag Switch

- Add `ACCOUNT_AUTH_V2_ENABLED` helper with disabled default.
- In `/login`, branch to Auth V2 only when enabled.
- In `/auth/telegram`, branch to Telegram Auth V2 only when enabled, while preserving invite behavior.
- Add rollback tests.

### Phase 1C-3: Password Login Adapter

- Convert account auth result into existing session fields.
- Preserve redirects.
- Confirm student, teacher, system admin, and business roles.
- Reject disabled, pending, and unknown roles safely.

### Phase 1C-4: Telegram Adapter

- Lookup active `account_telegram_links`.
- Load account/profile.
- Set existing session fields.
- Keep parent invite linking working.
- Preserve Mini App JSON response shape.

### Phase 1C-5: Tests

- Add unit tests for account lookup/status/profile handling.
- Add route tests for flag off and flag on.
- Add Telegram route tests.
- Keep existing dashboard import/start tests.

### Phase 1C-6: Local Enablement Only

- Enable `ACCOUNT_AUTH_V2_ENABLED=1` locally only.
- Test manual logins:
  - student MSI code
  - teacher `TCH0001`
  - system admin
  - parent Telegram
  - CEO/HR/Support/Academic Director when seed accounts exist
- Do not enable in production until review and explicit approval.

## Phase 1C Acceptance Criteria

- With `ACCOUNT_AUTH_V2_ENABLED=0`, legacy auth behavior is unchanged.
- With `ACCOUNT_AUTH_V2_ENABLED=1`, supported users authenticate through `msi_v2.accounts`.
- Legacy tables remain present and untouched.
- Existing dashboards still render or redirect as they do now.
- Rollback is a flag change, not a database rollback.
- No payment/access engine, workspace rebuild, or frontend redesign is included.
