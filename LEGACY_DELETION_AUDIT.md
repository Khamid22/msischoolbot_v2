# Legacy Deletion Audit

Date: 2026-07-07

Scope: source, tests, and documentation. Generated React build chunks under `backend/static/react/**`, `frontend/node_modules/**`, and Python cache folders were excluded from proof searches.

This is an audit only. No runtime code, database schema, or feature behavior was changed.

## Search Terms

Searched for:

- `/admin/teacher-academy`
- `render_admin_page`
- `admin-home`
- `teacher_academy_service`
- `backend.roles.admin.services.teacher_academy_service`
- `AdminSidebar`
- `previewRole`
- `devPreviewEnabled`
- `ADMIN_PREVIEW_ROLES`
- `account_auth_v2`
- `Account Authentication`
- `v2`
- `legacy_source`
- `legacy_login`
- `legacy_source_table`
- `msi_staff`
- `msi_v2`
- `old`
- `legacy`
- `compat`
- `compatibility`
- `fallback`
- `deprecated`
- `Training`
- `training`
- `Google Sheets`
- `sheets`
- `gspread`
- `worksheet`
- `xlsx`
- `csv`
- `sync_gradebooks`
- `migrate_legacy`
- `rebuild_database_v2`

## Summary

| Classification | Summary |
| --- | --- |
| SAFE_DELETE_NOW | Old Teacher Academy admin mutation route dependency and stale references to the deleted admin service wrapper can be removed or kept only as audit history. The runtime dependency has already been removed in the current working tree. |
| KEEP_FOR_NOW | Authentication v2 modules, `msi_v2` SQL, `msi_staff`, legacy linking columns, the active admin shell, student/parent fallbacks, HR lesson-practice training flow, resource worksheet labels, and Excel/CSV import or upload support are still active. |
| REPLACE_THEN_DELETE | Admin preview role plumbing, `account_auth_v2` naming, hard-coded `msi_v2` schema references, `adminTeacherAcademy` bootstrap prop naming, and stale phase/migration wording should be replaced through planned compatibility wrappers or migrations before deletion. |
| UNKNOWN | Historical planning reports, external Railway database references, and optional spreadsheet upload policy need manual product/ops review before deletion. |

## SAFE_DELETE_NOW

| Path/function/component | Current purpose | Replacement | Proof/reference search | Risk if deleted | Recommendation |
| --- | --- | --- | --- | --- | --- |
| `backend/roles/admin/services/teacher_academy_service.py` | Former admin service wrapper for Teacher Academy domain calls. It is deleted in the current working tree. | `backend/domains/teacher_academy/service.py` and `backend/domains/teacher_academy/queries.py`; AD/HOD route APIs call the domain layer. | `tests/test_database_restructure_db1.py` asserts the file does not exist and that page service does not import it. `rg "backend.roles.admin.services.teacher_academy_service"` finds docs/tests only. | If deleted before all imports move, admin Teacher Academy page or route imports would crash. Current tests cover removal. | SAFE_DELETE_NOW, already removed. Keep the negative tests. |
| Old `/admin/teacher-academy` mutation endpoints | Former admin mutation endpoints for creating, scheduling, assessing, status changes, promotion, and delete. | AD routes in `backend/roles/academic_director/routes.py`, HOD routes in `backend/roles/head_of_department/routes.py`, and shared API helpers in `backend/roles/common/teacher_academy_api.py`. | `tests/test_teacher_academy_tomorrow_ready.py` checks these route paths are not registered. `tests/test_teacher_academy_clean_api_routes.py` checks frontend admin route helpers are absent. Runtime `rg "/admin/teacher-academy"` finds only docs/tests. | If old clients still post there, they will get 404. That is intentional after the role separation. | SAFE_DELETE_NOW for runtime route dependency; leave or update docs as needed. |
| `routes.adminTeacherAcademy...` frontend action helpers | Former frontend route helper names for admin Teacher Academy mutations. | `routes.academicDirectorTeacherAcademy*` and `routes.headOfDepartmentTeacherAcademy*` style role routes; read-only admin listing uses bootstrap data. | `tests/test_teacher_academy_clean_api_routes.py` asserts no `routes.adminTeacherAcademy` helper remains in `frontend/src/shared/lib/routes.ts` or the Teacher Academy panel. | If a stale button still calls these helpers, actions would fail. Tests guard this. | SAFE_DELETE_NOW, already removed. |
| Stale Teacher Academy admin route references in active cleanup docs | Audit/planning docs still mention the old admin route/service as something that existed or should be removed. | `TEACHER_ACADEMY_LEGACY_DELETION_PLAN.md` is the current source of removal notes; final architecture docs should describe AD/HOD ownership. | Matches in `CLEAN_NAMING_MIGRATION_PLAN.md`, `DATABASE_RESTRUCTURE_PHASE_DB1_REPORT.md`, `DATABASE_CLEANUP_REPORT.md`, `docs/ENGINEERING_ROUTE_MAP.md`, and `TEACHER_ACADEMY_LEGACY_DELETION_PLAN.md`. | No runtime break. The risk is confusing future cleanup by pointing to already-deleted code. | SAFE_DELETE_NOW for stale statements, or archive the reports if historical detail is wanted. |
| Historical references to deleted database rebuild/migration scripts | Mentions of `database/rebuild_database_v2.sql`, `scripts/migrate_legacy_identity_to_accounts.py`, and `scripts/sync_gradebooks_from_excel.py`. The files are not present in the current tree. | Current database docs and domain services. Any real migration needs a reviewed migration plan. | `rg "sync_gradebooks|migrate_legacy|rebuild_database_v2"` finds report references only for the rebuild file and no live script path. | No runtime break if references are removed. Risk is only losing historical breadcrumbs. | SAFE_DELETE_NOW for stale report references if the docs are being cleaned. |

## KEEP_FOR_NOW

| Path/function/component | Current purpose | Replacement | Proof/reference search | Risk if deleted | Recommendation |
| --- | --- | --- | --- | --- | --- |
| `backend/roles/admin/routes/admin_page.py::render_admin_page` | Active renderer for `/admin`, admin subroutes, and some compatibility redirects. | Future role-specific render helpers may reduce use, but `/admin` still needs this today. | `backend/server.py` registers admin routes and passes `render_admin_page` to student route registration. Admin route modules still call it. Tests assert AD/HOD do not use `admin-home` while admin still does. | Removing it breaks system/admin login and admin forms. | KEEP_FOR_NOW. |
| React page key `admin-home` | Active bootstrap page key for the admin workspace. | None yet. Future cleanup could rename page keys with a compatibility alias. | `frontend/src/app/App.tsx` maps `admin-home` to `@/roles/admin/pages/Admin`; backend `render_admin_page` emits it. | Removing it breaks admin page hydration. | KEEP_FOR_NOW. |
| `frontend/src/roles/admin/pages/Admin.tsx::AdminSidebar` | Active sidebar for the system/admin console only. | Shared `RoleWorkspaceShell` covers AD/HOD/teacher style shells, not the current admin workspace. | AD/HOD tests assert `AdminSidebar` is absent from their pages. Admin page imports/renders it. | Removing it breaks admin navigation. | KEEP_FOR_NOW. |
| `backend/identity/account_auth_v2.py` and `backend/identity/account_telegram_auth_v2.py` | Active password and Telegram account authentication implementations. | Planned clean identity names such as `backend/identity/auth.py` and `backend/identity/telegram_auth.py`, with wrappers during migration. | Identity routes import these modules. Phase 1C tests import and exercise them. | Removing or renaming directly breaks login for staff, teachers, students, parents, and Telegram linking. | KEEP_FOR_NOW until replacement wrappers and tests are in place. |
| `Account Authentication` references in tests/plans | Names the current auth implementation generation. | User-facing docs can say `Authentication`; code/test module rename needs wrapper plan. | Found in auth tests and phase docs. | Removing names without code rename gives no runtime value and can hide active auth coverage. | KEEP_FOR_NOW in code/test names until identity rename phase. |
| `msi_v2` runtime SQL references | Current Railway/Postgres schema used by active app services. | Target schema `lms`, only after migration plan, backup, local test, Railway cutover, and rollback plan. | Broad search finds active SQL across identity, admin services, AD/HOD services, academics, announcements, teacher, student, parent, and workspace count services. | Direct rename/deletion breaks nearly every data-backed route. | KEEP_FOR_NOW. Database migration required. |
| `msi_staff` | Active staff/source table used by authentication, staff registration, and workspace logic. | Future identity/staff domain tables after migration. | Found in identity tests, staff registration services, demo auth, docs. | Removing breaks AD/HOD/admin login and staff profile resolution. | KEEP_FOR_NOW. |
| `legacy_source_table`, `legacy_source_id`, `legacy_login` | Compatibility columns linking accounts/profiles to existing rows and public IDs. | Future normalized account/profile relationships, with migration. | Found in account auth tests and identity/profile query code. | Removing breaks account resolution and role workspace linking. | KEEP_FOR_NOW. Database/data migration required. |
| Student/parent/admin fallback and compatibility branches | Preserve existing auth/session/dashboard behavior across migrated account shapes. | Cleaner account/session domain after Auth naming migration and data backfill. | Matches in `backend/domains/identity/routes.py`, `backend/utils/session.py`, parent/student services, and tests. | Removing prematurely breaks student dashboard, parent flow, or old sessions. | KEEP_FOR_NOW. |
| HR/candidate `training` flow | Active admin HR lesson-practice flow for candidates, separate from Teacher Academy. | If product naming changes, rename source/user-facing labels in a dedicated pass. | `frontend/src/roles/admin/panels/TeachersPanel.tsx`, `TrainingEvaluationModal.tsx`, `teachers/shared.ts`, and `backend/roles/admin/services/teacher_candidate_service.py` use training status/event keys. | Deleting it removes candidate evaluation behavior. | KEEP_FOR_NOW. |
| Teacher Academy internal status values such as `in_training` and `training_simulation` | Existing stored/status values for Academy progress/session type. | Future enum migration or label mapping. | `TeacherAcademyPanel.tsx` maps visible labels to `In Academy` / `Academy simulation` while keeping stored keys. | Changing keys without migration breaks filtering and submissions. | KEEP_FOR_NOW. |
| Resource `worksheet` category | Active resource type, not a Google Sheets dependency. | None needed. | `database/queries/resource_queries.py` seeds `Worksheet`; resource UI examples mention worksheets. | Deleting it removes a valid learning resource type. | KEEP_FOR_NOW. |
| `.xlsx`/`.csv` import and upload support | Import/export and resource upload support. Not a live Google Sheets source of truth. | None unless product decides to forbid these file types. | `database/academics/curriculum.py` imports SOW xlsx files with `openpyxl`; `r2_storage_service.py` allows xls/xlsx/csv uploads. Docs state Excel/Google Sheets are import/export only. | Removing could break curriculum import and uploaded resources. | KEEP_FOR_NOW. |

## REPLACE_THEN_DELETE

| Path/function/component | Current purpose | Replacement | Proof/reference search | Risk if deleted | Recommendation |
| --- | --- | --- | --- | --- | --- |
| `ADMIN_PREVIEW_ROLES`, `previewRole`, `devPreviewEnabled`, `devPreviewRole`, `msi_admin_mode` | Development/admin preview mode for rendering role workspaces from admin. | Explicit dev-only preview entrypoint, or remove entirely after product confirms it is no longer needed. | Found in `backend/roles/admin/routes/admin_page.py`, `frontend/src/roles/admin/hooks/useAdminState.ts`, `frontend/src/roles/admin/shared.ts`, and deployment docs. | Removing directly may break admin QA workflows and tests around preview state. | REPLACE_THEN_DELETE. Disable in production stays correct; later remove with focused tests. |
| `account_auth_v2` import path and helper names | Active auth implementation with migration-era naming. | Create clean modules (`auth.py`, `accounts.py`, `sessions.py`, and Telegram auth module), re-export old paths temporarily, then update imports/tests. | `backend/domains/identity/routes.py` imports v2 modules and has helper names like `set_account_auth_v2_session`. Auth tests import `backend.identity.account_auth_v2`. | Direct deletion breaks all login paths. | REPLACE_THEN_DELETE with compatibility wrapper. |
| `msi_v2` schema name in SQL | Active physical schema name. | Configurable schema abstraction, then Railway-safe migration from `msi_v2` to `lms`. | Runtime SQL search shows hard-coded `msi_v2` throughout backend services. | Direct rename breaks app queries and migrations. | REPLACE_THEN_DELETE only after database migration plan. |
| `legacy_source_*` and `legacy_login` column names | Active compatibility fields in account/profile rows. | Normalize relationships after data migration, then keep views/wrappers through cutover. | Identity tests and account/profile queries still expect these fields. | Removing breaks account to role record mapping. | REPLACE_THEN_DELETE only after data migration. |
| `adminTeacherAcademy` bootstrap prop name | Frontend/backend prop shape for Teacher Academy rows in admin, AD, and HOD pages. It no longer means admin mutation ownership. | Rename to `academyTeachers` or role-neutral `teacherAcademyRows`, with temporary frontend fallback for old prop. | Found in AD/HOD TeacherAcademy page props, admin state, admin page context, and tests. | Direct rename without dual-read breaks page props. | REPLACE_THEN_DELETE. |
| Stale phase/migration docs using `v2`, `Account Authentication`, `old`, `legacy`, and `compatibility` language | Historical planning and audit language. | Current architecture docs that describe the clean model and preserve migration history separately. | Broad search finds many matches in `docs/PHASE_*`, `CLEAN_NAMING_MIGRATION_PLAN.md`, and repair reports. | Low runtime risk, but deleting docs could lose decisions. | REPLACE_THEN_DELETE or archive after owner review. |
| `render_admin_page` passed to non-admin page registration | Student route registration still receives the admin renderer for compatibility redirects. | Role-specific redirect/render helpers from identity/student modules. | `backend/server.py` passes it to `register_student_page_routes`; AD/HOD tests prove AD/HOD no longer receive it. | Removing directly can break compatibility redirects. | REPLACE_THEN_DELETE in a route separation pass. |
| `Training` source/component names where the visible product is Teacher Academy | Some source names and status keys are historical or generic. | Central label maps and domain-specific names, preserving DB/status keys until migrated. | Matches in Teacher Academy and HR candidate files; visible Academy labels have already replaced several user-facing strings. | Blind rename can break enum/status submissions. | REPLACE_THEN_DELETE when scoped to UI labels or enum migration. |

## UNKNOWN

| Path/function/component | Current purpose | Replacement | Proof/reference search | Risk if deleted | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Historical reports: `DATABASE_CLEANUP_REPORT.md`, `DATABASE_RESTRUCTURE_PHASE_DB1_REPORT.md`, `UI_UX_REPAIR_REPORT.md`, phase plan docs | Preserve audit history and prior decisions, but include stale migration-era terms. | Archive folder, changelog, or updated current architecture docs. | Many legacy terms appear only in these docs. | Low runtime risk; product/process risk if audit trail is needed. | UNKNOWN pending documentation policy. |
| External Railway DB/schema references | May exist outside the repository in env vars, backups, or manual SQL. | Railway migration runbook and backup/rollback plan. | Repo search cannot prove external references. | Deleting or renaming without ops review can break production. | UNKNOWN until Railway/environment audit. |
| Spreadsheet upload policy | `.xls`, `.xlsx`, and `.csv` uploads may be allowed intentionally for resources. | Product decision: keep as resource uploads or restrict file types. | Runtime upload service allows these extensions. Docs state import/export only, not source of truth. | Removing can block valid academic resources. | UNKNOWN as a product policy item; not legacy by default. |
| `gspread` and live Google Sheets clients | No live runtime dependency found in current source search, but external scripts or env may exist outside repo. | None if confirmed absent. | `rg "gspread"` produced no active source match in searched paths. Docs say Google Sheets is import/export only. | Low runtime repo risk; unknown external automation risk. | UNKNOWN until external automation is checked. |

## Recommended Deletion Order

1. Finish committing the current Teacher Academy admin route deletion batch only after review.
2. Clean or archive stale docs that still describe deleted Teacher Academy admin routes or the deleted admin service wrapper.
3. Replace `adminTeacherAcademy` prop naming with a dual-read frontend/backend transition, then remove the old prop.
4. Replace admin preview role plumbing only after deciding whether it remains a development tool.
5. Rename `account_auth_v2` through compatibility wrappers and login coverage.
6. Introduce configurable schema naming while still pointing to `msi_v2`.
7. Plan and execute the `msi_v2` to `lms` database migration separately, with backup and rollback.
8. Remove compatibility columns and fallback branches only after data migration and one or more verified deploy cycles.

## Verification Commands

Required commands for this audit:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```

## Audit Conclusion

The only clearly safe runtime deletion area found is the old Teacher Academy admin mutation dependency, and the current working tree already removes that dependency while keeping negative tests. Most other legacy-looking names are still active compatibility surfaces, database schema names, auth module names, valid resource labels, or HR candidate practice workflow code. They should be replaced in planned phases, not deleted in this audit.
