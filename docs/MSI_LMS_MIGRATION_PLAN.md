# MSI LMS Portal Migration Plan

Status: planning document. Do not treat this as implemented code.

## Branch Strategy

- Production branch: `main`.
- Rewrite branch: `FastAPI-Run-System`.

No rewrite work should be merged into `main` until data, auth, workspaces, and payment/access behavior are verified.

## Migration Principles

- PostgreSQL is the source of truth.
- Excel and Google Sheets are import/export sources only.
- Do not delete database values without explicit approval.
- Use backups and migration reports.
- Prefer incremental cutover over a big-bang rewrite.
- Keep academic dashboards working during refactor.

## Current Migration Status

Excel academic statistics migration is complete and verified.

Imported data is now in PostgreSQL tables:

- `lesson_sessions`
- `attendance_records`
- `homework_scores`
- `exam_results`

`MONLINE` was included.

Blank Excel cells are skipped by default.

Duplicate exam keys are not cleaned yet. They should be investigated later with a report.

## Phase 0: Freeze Current Baseline

Goal: preserve the verified state.

Actions:

- Keep migration report under `migration_reports/`.
- Keep backup directory local and ignored.
- Record current row counts.
- Add tests around current dashboard outputs before refactoring those paths.

Exit criteria:

- Current academic dashboards can be loaded.
- Validation query results are recorded.
- Duplicate exam keys are documented as known issue, not fixed.

## Phase 1: Documentation And Domain Boundaries

Goal: agree on the target design before code changes.

Actions:

- Finalize architecture docs.
- Confirm role boundaries.
- Confirm payment/access policy behavior.
- Confirm target account model.
- Confirm parent linking lifecycle.

Exit criteria:

- Architecture docs accepted.
- Questions needing human confirmation answered.

## Phase 2: Account And Role Foundation

Goal: replace mixed `admin` role usage with explicit target roles.

Actions:

- Introduce target account model.
- Map current `admin` code role to documented `system_admin` transition path.
- Preserve existing staff/teacher/student/parent access.
- Enforce one user, one role.
- Add audit events for sensitive actions.

Teacher requirements:

- `TCH0001` login format.
- One account per teacher.
- Teacher can teach multiple subjects.

Student requirements:

- MSI code plus password.
- Student code globally unique.

Parent requirements:

- Telegram-first.
- Password login deferred.

Exit criteria:

- All real LMS roles can log in.
- System Admin is separate in documentation and route planning.
- No role depends on admin preview mode.

## Phase 3: Domain Repository Layer

Goal: move business persistence behind domain-owned repositories.

Actions:

- Create repository boundaries for identity, people, academics, payments, support, resources, HR, and reports.
- Stop putting complex SQL in route functions.
- Keep PostgreSQL as the only runtime data source.
- Keep Excel import scripts isolated under imports.

Exit criteria:

- Workspaces call services.
- Services call repositories.
- Bot and web do not import each other.

## Phase 4: Real Role Workspaces

Goal: replace admin preview modes with real workspaces.

Priority:

1. CEO
2. Academic Director
3. Customer Support
4. HR Manager
5. Teacher
6. Student
7. Parent
8. System Admin

Workspace rules:

- CEO: broad visibility and audited drilldown.
- Academic Director: full academic access for v1.
- Customer Support: B2C support only.
- HR Manager: hiring and teacher development.
- Teacher: assigned groups and teaching work.
- Student: own data.
- Parent: linked children only.
- System Admin: internal operations only.

Exit criteria:

- Each workspace has own route boundary.
- Role guards match role purpose.
- Admin preview mode is no longer the production role mechanism.

## Phase 5: Payment And Access Policy

Goal: replace loose payment rows and hardcoded blocking with policy.

Actions:

- Introduce invoices.
- Introduce payment agreements.
- Introduce payment warnings.
- Introduce access restrictions.
- Define B2C warning workflow.
- Define B2B CEO escalation workflow.
- Add policy service that routes consult.

Rules:

- Do not hardcode blocking directly in routes.
- Do not automatically block a whole school for B2B unpaid contract.
- Customer Support handles B2C payment follow-up.
- B2B unpaid school contract escalates to CEO only.

Exit criteria:

- Access decisions are stored and audited.
- Route guards read policy decisions.
- Support can create warnings.
- CEO receives B2B escalation.

## Phase 6: Parent Telegram Linking Hardening

Goal: make parent linking a shared domain service.

Actions:

- Move parent invite/link rules out of route/bot-specific code.
- Use signed, expiring invite payloads.
- Use Telegram HMAC validation.
- Store invite use and parent-child link changes.
- Support multiple children across schools.

Exit criteria:

- Bot and web use the same parent-link service.
- Parent can see only linked children.
- Link/unlink actions are audited.

## Phase 7: Cleanup And Compatibility Removal

Goal: remove temporary compatibility safely.

Actions:

- Remove live Excel/Google Sheets paths.
- Remove admin preview production dependencies.
- Remove duplicate permission system.
- Remove plaintext password compatibility.
- Remove direct bot-backend imports.
- Review legacy columns.

Exit criteria:

- Tests pass.
- Data reports pass.
- No production route relies on removed compatibility.

## Verification Checklist

Backend:

- Import app.
- Run route guard tests.
- Run domain service tests.
- Run payment/access policy tests.
- Run parent linking tests.

Frontend:

- Typecheck.
- Build.
- Verify each workspace page.
- Verify mobile Telegram layout.

Database:

- Orphan checks.
- Duplicate checks.
- Counts by school.
- Counts by subject.
- Counts by source import.
- Payment/access policy consistency checks.

Bot:

- `/start`.
- parent invite start parameter.
- `/whoami`.
- unlink flow.

## Known Risks

- Current payment code and schema disagree about what `payments.student_id` means.
- Current role shell still uses `admin` heavily.
- Student auth rows do not cover all students.
- Bot imports backend identity modules directly.
- Duplicate exam keys exist.
- CEO drilldown needs audit logging to avoid invisible over-access.

## Deferred Items

- Parent password login.
- AI modules.
- Google Slides modules.
- Adaptive learning.
- School coordinator role.
- Duplicate exam cleanup.
