# Admin Preview Cleanup Report

Date: 2026-07-07

Scope: Legacy Deletion Phase 2. This pass isolates admin preview behavior so stale preview storage cannot affect real Academic Director, HOD, Teacher, Student, or Parent workspaces.

No database schema changes were made. `/admin` remains available for system/admin users.

## What Changed

| Area | Change | Why |
| --- | --- | --- |
| `backend/roles/admin/routes/admin_page.py` | `preview_enabled` now requires `current_auth_role() == "admin"` and `_dev_preview_enabled()`. | Prevents preview props from ever being enabled for non-admin renders, even if a compatibility path reaches the admin renderer. |
| `frontend/src/roles/admin/hooks/useAdminState.ts` | Preview mode now requires both `props.devPreviewEnabled` and an admin/system-admin role. | Stale `devPreviewRole` or `msi_admin_mode` values cannot change visible tabs unless the server explicitly enables preview for admin. |
| `frontend/src/roles/admin/hooks/useAdminState.ts` | Admin tab URLs omit `mode` when preview is not allowed. | Real sessions do not preserve or reintroduce preview query parameters. |
| `frontend/src/shared/lib/staleUiState.ts` | Added `clearRolePreviewStorage()` for unconditional cleanup. | Login/logout/bootstrap can clear stale preview keys even for admin users when preview is disabled. |
| `frontend/src/roles/admin/pages/Admin.tsx` | Preview selector now checks both `devPreviewEnabled` and true admin/system-admin role. | The preview UI cannot appear just because a prop leaks into a non-admin render. |

## Preview Behavior Kept

Preview is still available only for true `/admin` sessions when the development preview guard allows it:

- current auth role is `admin`
- rendered page is `admin-home`
- non-production default preview is allowed, unless `ADMIN_PREVIEW_ROLES=0`
- production default preview is disabled, unless intentionally forced with `ADMIN_PREVIEW_ROLES=1`

This preserves system/admin QA behavior without making preview a role workspace substitute.

## Preview Behavior Removed or Blocked

- Stale `devPreviewRole` / `msi_admin_mode` storage no longer drives tabs when `devPreviewEnabled` is false.
- Production/admin sessions no longer honor `?mode=student` unless preview is explicitly enabled.
- AD/HOD routes do not import or receive `previewRole` or `devPreviewEnabled`.
- Teacher cabinet source does not contain admin preview props or preview storage keys.
- Real role pages continue to clear stale preview storage at app bootstrap.

## Remaining References and Why

| Reference | Why it remains |
| --- | --- |
| `ADMIN_PREVIEW_ROLES` | Deployment/admin-only switch for intentionally enabling `/admin` preview. Default production guidance remains disabled. |
| `previewRole`, `devPreviewEnabled` | Admin-home props only. They are not emitted by AD/HOD routes and are ignored unless admin preview is server-enabled. |
| `devPreviewRole`, `msi_admin_mode` | Storage keys kept only so the cleaner can remove stale values and admin preview can persist when intentionally enabled. |
| `msi_teacher_preview_key`, `msi_teacher_preview_id` | Admin preview helper for the admin Teacher mode only; real Teacher cabinet does not read it. |

## Tests Added or Updated

- AD/HOD pages do not show Student mode.
- AD/HOD route source does not include `previewRole` or `devPreviewEnabled`.
- Teacher cabinet source does not include admin preview props or preview storage keys.
- `/admin?mode=student` in production emits `devPreviewEnabled: false` and stays in admin mode.
- `/admin?mode=student` with `ADMIN_PREVIEW_ROLES=1` keeps admin preview intentionally available.
- Source tests assert admin preview requires `Boolean(props.devPreviewEnabled) && canUseAdminPreviewForRole(realRole)`.

Focused verification:

```bash
python3 -m pytest tests/test_academic_director_sidebar_ui.py tests/test_phase2a_system_admin_workspace_cards.py tests/test_teacher_mobile_ux_source.py
```

Result: passed, `45 passed`.

## Required Full Verification

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```

Results:

- `python3 -m pytest`: passed, `310 passed, 11 warnings`.
- `npm --prefix frontend run check-types`: passed.
- `npm --prefix frontend run build`: passed.
- `git diff --check`: passed.
