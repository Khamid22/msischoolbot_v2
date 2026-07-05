# MSI LMS Portal Backend Refactor and Cleanup Plan

Status: planning only. Do not move, rename, delete, or refactor files from this document without a separate approved implementation phase.

Current checkpoint:
- Phase 1C Auth V2 is complete in local/dev.
- `ACCOUNT_AUTH_V2_ENABLED=0` keeps legacy auth working.
- `ACCOUNT_AUTH_V2_ENABLED=1` works for password login and Telegram login.
- Final smoke tests passed.
- `python3 -m pytest`: 100 passed, 1 warning.
- Git status was clean before this document was created.

## 1. Current Backend Structure Overview

Current backend root is `backend/`. Keep it as the main app folder for now.

Current structure:

```text
backend/
  api/                    Shared API response/schema helpers.
  domains/                Domain services for academics, payments, resources, support, etc.
  identity/               Current identity/auth/service helpers, including Auth V2 services.
  roles/                  Role workspace routes and role-specific services.
  routes/                 Shared API routes such as system/auth status.
  security/               Role dependencies and permission helpers.
  static/                 Built frontend assets, PWA files, Telegram helper JS.
  utils/                  Session, request context, guards, Telegram initData, responses, rate limiting.
  main.py                 Backend app entrypoint import.
  render.py               React/page rendering glue.
  server.py               FastAPI app bootstrap, middleware, route registration.
  js_bundles.py           Legacy/static Telegram bundle generation support.
```

Important adjacent folders:
- `database/`: PostgreSQL connection layer, query modules, Alembic migrations, schema SQL.
- `scripts/`: one-time and operational scripts.
- `tgbot/`: Telegram bot helpers/settings.
- `frontend/`: React/Vite source, not part of Phase 1D.
- `backend/static/react/`: built frontend output, not source.

## 2. Target Backend Structure

Target structure under the existing `backend/` folder:

```text
backend/
  api/
    v1/
      auth/
      system/
      academic/
      payments/
      resources/
      support/
      workspaces/
        admin/
        ceo/
        academic_director/
        customer_support/
        hr_manager/
        teacher/
        student/
        parent/
  core/
    app.py
    config.py
    database.py
    security.py
    sessions.py
    permissions.py
    rate_limits.py
  domains/
    identity/
    organization/
    people/
    academic/
    learning_delivery/
    assessment/
    resources/
    payments/
    support/
    communication/
    analytics/
  integrations/
    telegram/
    excel/
    storage/
    railway/
  utils/
```

Design intent:
- `api/v1/` owns HTTP routes, request parsing, response shape, and route dependencies.
- `core/` owns app bootstrap, settings, database connection access, sessions, security primitives, and cross-cutting middleware.
- `domains/` owns business logic and database-facing services.
- `integrations/` owns external systems: Telegram, Excel import/export, object storage, deployment/runtime hooks.
- `utils/` remains for small pure helpers only; anything with domain meaning should move into a domain or integration package later.

## 3. Mapping of Current Files to Future Locations

This is a future map only. Do not move yet.

| Current path | Future location | Notes |
| --- | --- | --- |
| `backend/server.py` | `backend/core/app.py` or `backend/core/bootstrap.py` | Split app creation, middleware, route registration, and error handlers first. |
| `backend/main.py` | Stay for now | Entry import used by deployment. Later can import from `backend.core.app`. |
| `backend/routes/system.py` | `backend/api/v1/system/routes.py` and `backend/api/v1/auth/session.py` | `/api/v1/auth/me` likely belongs under auth/session. |
| `backend/api/responses.py` | `backend/api/v1/shared/responses.py` | Keep response contract stable before moving. |
| `backend/api/schemas.py` | `backend/api/v1/shared/schemas.py` | Same as above. |
| `backend/security/*` | `backend/core/security.py`, `backend/core/permissions.py`, or `backend/api/v1/dependencies.py` | Do after Auth V2 cutover and role compatibility removal. |
| `backend/utils/session.py` | `backend/core/sessions.py` | Must wait because many legacy routes depend on exact session keys. |
| `backend/utils/context.py` | `backend/core/request_context.py` | Temporary Flask-style compatibility proxy. Move only after route refactor. |
| `backend/utils/telegram_auth.py` | `backend/integrations/telegram/init_data.py` | HMAC verification should become the Telegram integration boundary. |
| `backend/identity/account_auth_v2.py` | `backend/domains/identity/account_auth.py` later | Rename only after legacy auth is removed. |
| `backend/identity/account_telegram_auth_v2.py` | `backend/domains/identity/telegram_account_auth.py` later | Rename only after Telegram Auth V2 is the only path. |
| `backend/identity/credentials.py` | `backend/domains/identity/legacy_credentials.py` later | Legacy password auth compatibility. |
| `backend/identity/account_service.py` | Split into identity domain services | Mixed legacy account, Telegram, and activity concerns. |
| `backend/identity/parent_invites.py` | `backend/domains/identity/parent_invites.py` or `backend/domains/people/parent_invites.py` | Keep invite behavior stable. |
| `backend/domains/academics/postgres_service.py` | `backend/domains/academic/structure_service.py` plus smaller services | Rename away from implementation detail after split. |
| `backend/domains/academics/internal_dashboard_service.py` | `backend/domains/analytics/academic_dashboard_service.py` | Current output preserves old Sheets-style shapes. |
| `backend/domains/academics/rating_service.py` | `backend/domains/assessment/rating_service.py` | Academic progress/assessment domain. |
| `backend/domains/payments/service.py` | `backend/domains/payments/service.py` | Keep, then split invoices/warnings/restrictions later. |
| `backend/domains/communication/chat_service.py` | `backend/domains/communication/chat_service.py` | Keep. |
| `backend/domains/complaints/service.py` | `backend/domains/support/ticket_service.py` later | Rename “complaints” to support tickets after UI/API agreement. |
| `backend/domains/resources/service.py` | `backend/domains/resources/service.py` | Keep, then split metadata/storage concerns. |
| `backend/roles/*/routes.py` | `backend/api/v1/workspaces/<role>/routes.py` | Move after route tests cover every workspace. |
| `backend/roles/admin/routes/*` | `backend/api/v1/workspaces/system_admin/*` or domain API modules | Current `admin` includes business operations and system operations. Split carefully. |
| `backend/roles/admin/services/*` | Domain packages by business area | Most are domain services living under an admin workspace. |
| `backend/roles/student/routes/*` | `backend/api/v1/workspaces/student/*` | Keep compatibility with dashboard/public ids. |
| `backend/roles/student/services/*` | `backend/domains/learning_delivery`, `assessment`, `resources` | Split by domain, not by role. |
| `backend/render.py` | `backend/core/rendering.py` or `backend/api/rendering.py` | Wait until frontend deployment shape is decided. |
| `backend/js_bundles.py` | `backend/integrations/telegram/static_bundles.py` or archive later | Legacy helper bundle generation. |
| `backend/static/*` | Stay for now | Built assets and PWA files are deployment outputs, not backend domain code. |

## 4. Files That Must Stay Where They Are For Now

- `backend/server.py`: app bootstrap and route registration are import-sensitive.
- `backend/main.py`: deployment entrypoint.
- `backend/domains/identity/routes.py`: owns `/login` and `/auth/telegram`; do not disturb until Auth V2 is stable in production.
- `backend/identity/account_auth_v2.py`: new Auth V2 password service, still feature-flagged.
- `backend/identity/account_telegram_auth_v2.py`: new Auth V2 Telegram service, still feature-flagged.
- `backend/identity/credentials.py`: legacy password auth fallback.
- `backend/utils/session.py`: existing route/session compatibility.
- `backend/utils/context.py`: request/session proxy used across current route modules.
- `backend/utils/telegram_auth.py`: verified Telegram initData logic.
- `backend/security/*`: currently used by `/api/v1/auth/me` and route guards.
- `database/alembic/versions/*`: migration history must never be renamed or deleted.
- `scripts/migrate_legacy_identity_to_accounts.py`: rollback/debug/reproducibility script until production migration is complete and approved.
- `scripts/sync_gradebooks_from_excel.py`: Excel-to-PostgreSQL import reproducibility script until migration is signed off.

## 5. Files That Can Move Later

Move only after tests prove imports and routes are stable.

- `backend/routes/system.py` to `backend/api/v1/system/routes.py`.
- `backend/api/responses.py` and `backend/api/schemas.py` under `backend/api/v1/shared/`.
- `backend/security/roles.py` and `backend/identity/roles.py` can be consolidated later.
- `backend/domains/announcements/service.py`, `office_hours/service.py`, `payments/service.py`, `resources/service.py` can remain domain services but may move into clearer domain block names.
- `backend/roles/ceo/routes.py`, `hr_manager/routes.py`, `customer_support/routes.py`, `academic_director/routes.py`, `teacher/routes.py`, `parent/routes.py`, and `student/routes/*` can move into `backend/api/v1/workspaces/`.
- `backend/roles/admin/routes/*` can move only after `system_admin` and LMS business roles are separated.
- `backend/static/js/telegram/*` can move under `backend/integrations/telegram/static/` later if the static pipeline supports it.

## 6. Files That Should Be Split Later

Split candidates by size and responsibility:

| File | Current size observed | Split direction |
| --- | ---: | --- |
| `backend/roles/admin/services/insights_service.py` | about 977 lines | Analytics queries, summary builders, formatting. |
| `backend/roles/admin/services/academic_service.py` | about 928 lines | Group management, enrollment, gradebook reads, lesson/exam operations. |
| `backend/domains/academics/internal_dashboard_service.py` | about 884 lines | Student dashboard data, admin dashboard data, report builders. |
| `backend/roles/student/services/dashboard_service.py` | about 862 lines | Payload assembly, assessment summaries, resources, UI adapters. |
| `backend/roles/admin/services/teacher_academy_service.py` | about 861 lines | Teacher profiles, hiring/candidates, academy data, schedules. |
| `backend/roles/admin/services/r2_storage_service.py` | about 852 lines | Storage API, file validation, video processing, upload progress. |
| `backend/domains/academics/postgres_service.py` | about 774 lines | Academic structure, student creation, group enrollment, legacy id minting. |
| `backend/domains/resources/service.py` | about 733 lines | Resource metadata, upload/storage, filtering, access. |
| `backend/domains/academics/rating_service.py` | about 664 lines | Rating calculation, data loading, rendering helpers. |
| `backend/roles/parent/routes.py` | about 588 lines | Parent page, API endpoints, linked students, support/payment data. |
| `backend/domains/identity/routes.py` | about 568 lines | Login page, password auth, Telegram auth, handoff, home redirects. |
| `backend/roles/admin/routes/teacher_routes.py` | about 537 lines | Teacher CRUD, routes, service orchestration. |
| `backend/utils/session.py` | about 401 lines | Current session readers/writers and legacy route helpers. |

Split rule: first add tests around behavior, then split route parsing from domain services, then move files. Do not split just to reduce line count if ownership remains unclear.

## 7. Legacy Compatibility That Must Stay Temporarily

- `ACCOUNT_AUTH_V2_ENABLED` branch in `/login`.
- `ACCOUNT_AUTH_V2_ENABLED` branch in `/auth/telegram`.
- Legacy `verify_student_credentials`, `verify_teacher_credentials`, and `verify_admin_credentials`.
- Legacy Telegram lookup order when the feature flag is off.
- Parent invite `start_param` behavior before Auth V2 Telegram lookup.
- `system_admin` session compatibility with `auth_role="admin"` for `/admin`.
- `admin_id`, `admin_role`, `admin_is_owner`, `admin_last_panel`, `admin_last_school`.
- `student_db_id` meaning old `legacy_student_row_id`.
- `student_enrollment_id` meaning current dashboard/public id.
- `legacy_*` ids in PostgreSQL and code paths that resolve them.
- Old request/session proxy in `backend/utils/context.py`.
- `backend/static/js/telegram-*` helper assets until Telegram Mini App startup is fully verified after refactor.

## 8. Possible Archive/Delete Candidates Later

Do not delete now.

| Candidate | Proposed action later | Reason | Risk |
| --- | --- | --- | --- |
| `__pycache__/` folders and `*.pyc` files | Delete later and ensure ignored | Generated runtime artifacts. | Low if untracked/not relied on. |
| `backups/` local dump/CSV files | Keep private locally; never commit | Backup data may contain private records. | High if deleted before verified external backup. |
| Non-redacted migration reports | Keep private, untracked | May contain private data or local paths. | High if committed; medium if deleted before audit complete. |
| `scripts/sync_gradebooks_from_excel.py` | Move to `scripts/completed_migrations/` after production signoff | One-time Excel import, but needed for reproducibility. | Medium. |
| `scripts/migrate_legacy_identity_to_accounts.py` | Move to `scripts/completed_migrations/` after production signoff | One-time identity migration, but useful for rollback/debug. | Medium-high. |
| `database/rebuild_database_v2.sql` | Archive later after Alembic baseline is trusted | Rebuild SQL is not the preferred migration path now. | Medium-high. |
| `docs/DATABASE_REBUILD_BLUEPRINT.md` and `docs/DATABASE_REBUILD_EXECUTION_PLAN.md` | Archive later after architecture docs supersede them | Older rebuild planning docs. | Low-medium. |
| `backend/js_bundles.py` | Archive/delete only after static Telegram flow is replaced | Legacy helper bundle generation. | Medium. |
| Legacy credential helpers | Delete only after Auth V2 production cutover | Needed for feature-flag rollback. | High. |

## 9. Naming Cleanup

Classification meanings:
- Keep as-is: name is acceptable or externally meaningful right now.
- Rename later: name should improve after behavior is stable.
- Archive later: keep outside active runtime path after signoff.
- Delete later: remove after deletion rules pass.
- Needs manual decision: product or deployment decision needed first.

| Item | Current issue | Classification | Suggested MSI LMS Portal name/action |
| --- | --- | --- | --- |
| `backend/identity/account_auth_v2.py` | `v2` is temporary phase naming. | Rename later | `backend/domains/identity/account_auth.py` after legacy auth removal. |
| `backend/identity/account_telegram_auth_v2.py` | `v2` is temporary phase naming. | Rename later | `backend/domains/identity/telegram_account_auth.py`. |
| `tests/test_phase1c_*` | Phase-specific tests are useful during rollout. | Keep as-is now | Rename to `test_account_auth.py`, `test_telegram_account_auth.py` after Phase 1 closes. |
| `database/rebuild_database_v2.sql` | Rebuild/v2 naming is temporary and not Alembic-first. | Archive later | `database/archive/msi_lms_initial_schema_rebuild.sql` if retained. |
| `database/alembic/versions/0001_msi_v2_baseline.py` | `msi_v2` is actual schema namespace. | Keep as-is | Never rename Alembic history. |
| `msi_v2` schema references | Current PostgreSQL schema name. | Keep as-is | Renaming DB schema is a separate production migration decision. |
| `docs/PHASE_1C_AUTH_V2_PLAN.md` | Phase-specific doc. | Keep as-is now | Archive under `docs/archive/phase_plans/` after Phase 1 is complete. |
| `docs/PHASE_1_ACCOUNTS_IMPLEMENTATION_PLAN.md` | Phase-specific doc. | Keep as-is now | Archive later after production cutover. |
| `docs/DATABASE_REBUILD_BLUEPRINT.md` | Rebuild wording may be superseded. | Archive later | `docs/archive/database/MSI_LMS_SCHEMA_REBUILD_BLUEPRINT.md`. |
| `docs/DATABASE_REBUILD_EXECUTION_PLAN.md` | Rebuild wording may be superseded. | Archive later | `docs/archive/database/MSI_LMS_SCHEMA_REBUILD_EXECUTION_PLAN.md`. |
| Branch `FastAPI-Run-System` | Branch name is historical/planning branch. | Keep as-is now | Future implementation branches: `feature/auth-v2-cutover`, `refactor/backend-structure`. |
| Branch `fix-resource-order-old-to-new` | Contains `old-to-new`. | Needs manual decision | Close/archive if merged; use issue-linked branch names later. |
| Branch `debug-last-seen` | Debug branch. | Needs manual decision | Close if obsolete after activity smoke tests. |
| Branch `test` and `origin/test` | Ambiguous branch name. | Needs manual decision | Delete remote/local if obsolete and no open work depends on it. |
| Branch `fastapi-full-migration` | Historical migration name. | Needs manual decision | Keep until branch history is reviewed. |
| Branch `internal-system-migration` | Historical migration name. | Needs manual decision | Keep until branch history is reviewed. |
| Branch `worktree-agent-*` | Temporary worktree branch names. | Needs manual decision | Delete only after confirming no active worktree depends on them. |
| `backend/domains/academics/postgres_service.py` | Implementation detail in domain file name. | Rename later | `academic_structure_service.py` or split into `schools.py`, `groups.py`, `enrollments.py`. |
| `backend/domains/academics/internal_dashboard_service.py` | “internal” is vague. | Rename later | `academic_dashboard_service.py` or `progress_report_service.py`. |
| `backend/domains/complaints/service.py` | Product language should be support tickets. | Rename later | `backend/domains/support/ticket_service.py`. |
| `backend/roles/admin/*` | `admin` is internal operator, but current routes also contain business operations. | Rename/split later | `system_admin` workspace plus domain APIs for academic/support/payments. |
| `backend/roles/owner/` | Owner is legacy/admin-ish naming. | Needs manual decision | Remove or merge into `system_admin` after import check. |
| `backend/utils/demo_auth.py` | Demo auth should not live in generic utils long term. | Rename/move later | `backend/core/dev_auth.py` or `backend/integrations/demo/dev_auth.py`. |
| `backend/utils/context.py` | Flask-style compatibility proxy. | Rename later | `backend/core/request_context.py` after route migration. |
| Comments saying “old Sheets-style”, “legacy”, or “temporary compatibility” | Accurate now but should not survive final architecture. | Keep as-is now | Convert to normal domain language after compatibility removal. |
| `backups/msi_v2_pre_excel_*` | Backup naming is operational/private. | Keep private | Never commit; retain until external backup and migration signoff. |
| `migration_reports/phase1_accounts_*` | Phase/migration naming is expected. | Keep redacted reports | Archive reports after production signoff; keep redacted docs only. |
| `__pycache__/*cpython-313 2.pyc` | Generated duplicate/copy-like artifacts. | Delete later | Clean generated caches when safe. |

Professional naming conventions going forward:
- Prefer product language: `MSI LMS Portal`, `system_admin`, `support_ticket`, `parent_invite`, `account_auth`.
- Avoid `new`, `old`, `final`, `fixed`, `copy`, `test2`.
- Use phase names only in docs/tests while a phase is actively being rolled out.
- Use `legacy_` only when the code genuinely preserves old behavior for rollback or migration traceability.

## 10. Already-run Scripts

| File path | Purpose | Already run? | Still needed for production? | Recommended action | Deletion risk |
| --- | --- | --- | --- | --- | --- |
| `scripts/sync_gradebooks_from_excel.py` | Imports one-time Excel academic statistics into PostgreSQL, normalizing School 5 and Sehriyo gradebooks. | Yes, local/dev migration verified. | Yes until production import is complete, reports are reviewed, and rollback evidence exists. | Keep now. Later move to `scripts/completed_migrations/excel_gradebook_import.py` or archive. | Medium-high. |
| `scripts/migrate_legacy_identity_to_accounts.py` | Migrates legacy students/teachers/parents/staff into shared account/profile/link tables. | Yes, local/dev dry-run and apply verified. | Yes until production identity migration is complete and Auth V2 is stable. | Keep now. Later move to `scripts/completed_migrations/shared_accounts_migration.py`. | High. |
| `scripts/railway_start.sh` | Production/Railway startup wrapper that applies Alembic then starts app. | Used at deploy/startup, not one-time. | Yes while Railway deployment uses it. | Keep as operational script. | High. |
| `database/rebuild_database_v2.sql` | Historical clean schema rebuild SQL. | Likely already used before Alembic baseline; not current preferred migration path. | Possibly for reference only. | Archive later after confirming Alembic covers required schema. | Medium-high. |
| `database/alembic/versions/0001_msi_v2_baseline.py` | Alembic baseline migration. | Applied in dev/local. | Yes forever as migration history. | Keep forever. | Critical. |
| `database/alembic/versions/0002_lesson_session_source_metadata.py` | Adds source metadata for lesson sessions. | Applied in dev/local. | Yes forever as migration history. | Keep forever. | Critical. |
| `database/alembic/versions/0003_shared_accounts_foundation.py` | Creates shared account foundation tables. | Applied in dev/local. | Yes forever as migration history. | Keep forever. | Critical. |
| `migration_reports/excel_to_postgres_migration_verification_2026-07-05.md` | Excel migration verification report. | Yes. | Needed for audit/review. | Keep redacted/safe reports; do not commit private details. | Medium. |
| `migration_reports/phase1_accounts_apply_20260705.redacted.md` | Redacted identity apply report. | Yes. | Useful for review. | Keep committed if sanitized. | Low. |
| `migration_reports/phase1_accounts_dry_run_20260705_102923.redacted.md` | Redacted identity dry-run report. | Yes. | Useful for review. | Keep committed if sanitized. | Low. |
| `migration_reports/phase1_accounts_dry_run_20260705_102923.md` | Private dry-run details. | Yes. | Local audit only. | Keep private/untracked or remove only after approved backup/signoff. | Medium-high. |
| `migration_reports/phase1_accounts_dry_run_20260705_102923.json` | Private machine-readable dry-run details. | Yes. | Local audit only. | Keep private/untracked or remove only after approved backup/signoff. | Medium-high. |
| `backups/msi_v2_pre_excel_20260703_190041.dump` and CSV backup folder | Local pre-migration backup. | Yes. | Needed until external backup exists and migration is accepted. | Keep private; do not commit. | High. |

## 11. Do Not Delete Yet

- Alembic migrations.
- Legacy auth code.
- Old session compatibility helpers.
- Admin compatibility logic.
- Old Telegram auth logic.
- One-time migration scripts until production is migrated and verified.
- Redacted reports.
- Rollback-related code.
- Local/private backup artifacts until a production-grade backup exists elsewhere.
- `legacy_*` database columns or code paths.
- `database/rebuild_database_v2.sql` until its role is decided.
- Built frontend assets under `backend/static/react/` until the deployment pipeline is reviewed.

## 12. Deletion Rules

1. No deleting before Auth V2 is stable.
2. No deleting before production backup exists.
3. No deleting Alembic migration history.
4. No deleting scripts needed to reproduce migration.
5. No deleting legacy auth until `ACCOUNT_AUTH_V2_ENABLED=1` is stable and approved.
6. Before deleting any file, check imports/usages.
7. Every deletion must have a rollback commit or Git tag.

Additional local rule:
- Any deletion PR should include `rg` import evidence, route/test evidence, and a named rollback tag such as `pre-delete-legacy-auth-YYYYMMDD`.

## 13. Safe Refactor Order

Phase 1D-0: freeze behavior.
- Keep `ACCOUNT_AUTH_V2_ENABLED=0/1` smoke tests.
- Keep route snapshot tests.
- Add no movement yet.

Phase 1D-1: create empty package structure only.
- Add `backend/api/v1/`, `backend/core/`, and `backend/integrations/` with `__init__.py`.
- Do not move imports yet.

Phase 1D-2: extract pure helpers.
- Move or duplicate only pure response/schema helpers after import adapters are in place.
- Keep old import paths re-exporting new helpers temporarily.

Phase 1D-3: move system API routes.
- Move `/api/v1/system/status` and `/api/v1/auth/me` with route snapshot protection.
- Keep old response JSON shape.

Phase 1D-4: consolidate role and permission helpers.
- Decide final home for `backend/identity/roles.py` and `backend/security/roles.py`.
- Keep `system_admin` compatibility unchanged.

Phase 1D-5: split identity routes.
- Separate password login, Telegram auth, parent invites, and admin handoff.
- Do this only after Auth V2 is stable and approved.

Phase 1D-6: move workspace routes.
- Move role workspace routes one role at a time.
- Start with smaller roles: CEO, HR, Customer Support, Academic Director.
- Move admin/student/parent last because they contain more compatibility logic.

Phase 1D-7: split large domain services.
- Split by domain ownership, not by line count.
- Keep SQL behavior unchanged and add regression tests around counts/response shapes.

Phase 1D-8: archive one-time scripts and old docs.
- Only after production migration signoff.
- Archive, do not delete, unless deletion rules are satisfied.

## 14. Risks

- Import churn can break route registration because `backend/server.py` bootstraps the whole app.
- Session key changes can break dashboards even if login succeeds.
- `system_admin` currently depends on legacy `admin` compatibility.
- Student dashboard routes depend on `legacy_student_row_id` and public dashboard ids.
- Teacher workspace may still depend on `teacher_staff_id`.
- Parent Telegram flow depends on invite precedence before account lookup.
- Moving `backend/utils/context.py` too early can break many Flask-style route modules.
- Moving built static files can break deployment or Mini App startup.
- Deleting one-time scripts can make production migration hard to reproduce.
- Branch/document cleanup can remove useful audit context before the CEO/senior engineer review is complete.

## 15. Acceptance Criteria Before Any Real Refactor

Before moving or renaming any runtime file:
- Git status is clean.
- Production or staging backup plan is confirmed.
- Current route snapshot is saved.
- `python3 -m pytest` passes.
- Phase 1C smoke passes with `ACCOUNT_AUTH_V2_ENABLED=0`.
- Phase 1C smoke passes with `ACCOUNT_AUTH_V2_ENABLED=1`.
- `/login`, `/auth/telegram`, and parent invite flows are explicitly checked.
- `/api/v1/auth/me` returns expected role/session compatibility data.
- No frontend source changes are required.
- No database destructive operation is included.
- Import usage is checked with `rg`.
- A rollback tag/commit plan exists.
- Refactor is scoped to one package or route family at a time.

Before deleting or archiving any file:
- Confirm whether it is imported or executed in deployment.
- Confirm whether it is needed for rollback or migration reproduction.
- Confirm whether it contains private data and should stay untracked.
- Confirm owner approval.

