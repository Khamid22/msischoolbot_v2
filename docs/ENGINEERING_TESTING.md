# Engineering Testing

Audience: engineers verifying the LMS rewrite.

## Release-level Checks

```bash
python3 -m compileall -q backend database tgbot scripts main.py
python3 -m pytest
npm --prefix frontend run test:logic
npm --prefix frontend run test:schedule
npm --prefix frontend run test:teacher-nav
npm --prefix frontend run test:shared-ui
npm --prefix frontend run test:academic
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```

Use focused tests while editing, then run the full suite before release.

## Architecture Contracts

Tests and source audits should protect:

- no imports from deleted `database.queries`, `database.cross_queries`, or identity facades;
- no runtime DDL outside Alembic;
- `/api/v1` route ownership and the checked-in route snapshot;
- canonical `accounts` password authentication;
- canonical `students.id` authorization;
- domain-owned SQL and transaction boundaries.

## Identity Coverage

Verify:

- login for every password-enabled role;
- initial login-equals-password forced-change flow;
- current-password, confirmation, and minimum-length failures;
- self-service change increments `session_version` and audits the event;
- administrator reset invalidates old sessions and forces another change;
- disabled/role-changed/version-mismatched accounts lose access;
- owner startup seeding does not overwrite an independent password;
- Telegram HMAC and replay-window validation;
- Telegram links resolve the same canonical account/profile as password login;
- parent invite expiry, single use, hashing, concurrency, and child access.

## Authorization Coverage

Verify role and object policy independently:

- student APIs use the signed-in canonical student, not a caller-supplied ID;
- parent dashboards require an active child link;
- teacher actions require assignment;
- HOD actions require subject scope;
- chat messages require room membership;
- academic group moves stay within school and subject program;
- payments resolve a canonical student;
- office hours enforce future time, interval, overlap, capacity, ownership, and one active booking.

## Migration Verification

Do not validate identity/integrity migrations directly against production.

1. create a disposable database or clone of representative pre-`0005` data;
2. run `python -m alembic upgrade head`;
3. verify `python -m alembic current` equals `python -m alembic heads`;
4. inspect account/profile backfill and invite state with sanitized aggregate checks;
5. run identity, parent invite, office-hour, and academic integrity tests;
6. smoke-import the FastAPI app.

`0006_secure_parent_invites` is intentionally irreversible; test restoration from backup or invite regeneration rather than a downgrade.

## Workbook Reconciliation

Use the explicit reconciliation tool in report/dry-run mode before any writer:

```bash
python3 scripts/reconcile_academic_workbooks.py --help
```

Review ambiguous identities, group/enrollment resolution, lesson/date/source ordering, attendance, homework, exams, and student-wide coins. Parsing successfully or matching aggregate counts does not prove parity. Never invent a date/time or silently merge uncertain students to make the report pass.

## Frontend and Browser Verification

In addition to automated tests, verify at representative phone, tablet, laptop, and desktop widths:

- role navigation, drawers, dialogs, menus, buttons, pagination, tables, cards, and charts;
- keyboard focus order, Escape/close behavior, and visible focus;
- 200% zoom and minimum touch targets;
- reduced-motion mode;
- Telegram safe areas and viewport resizing;
- valid zero metrics and empty/error/loading states;
- `Asia/Tashkent` date/week and office-hour behavior from a different browser timezone;
- no console errors or failed API requests in primary role flows.

## Telegram Verification

Current Telegram tests cover web/Mini App integration: initData verification, canonical account resolution, start-parameter handling, invite claim, and linked-child access.

Do not require `/start`, `/whoami`, or callback smoke tests yet: the inbound `tgbot` router registry is intentionally empty. Add bot command tests when product-approved handlers are implemented.

## Documentation Privacy

Before publishing reports, scan for database URLs, secrets, hashes, invite codes, names, phone numbers, Telegram IDs, raw grades, source workbook rows, dumps, and backups. Commit only sanitized architecture and test evidence.
