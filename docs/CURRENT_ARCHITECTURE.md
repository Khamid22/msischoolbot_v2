# Current Architecture

Date: 2026-07-26

Branch: `FastAPI-Run-System`

Production reference: `main` (read-only)

## System Shape

MSI School is a product-domain modular monolith. PostgreSQL is the sole LMS source of truth; FastAPI composes role-specific adapters; React workspaces compose domain features.

```text
React workspace
  -> FastAPI workspace adapter
    -> command/query or compatibility facade
      -> owning repository
        -> PostgreSQL (msi_v2)

FastAPI / Telegram command
  -> UnitOfWork
    -> module command and repositories
      -> domain write + outbox job in one transaction

Durable worker
  -> FOR UPDATE SKIP LOCKED claim
    -> typed module job handler
      -> retry, completion, or dead-job state
```

Alembic is the only DDL owner. The current migration head is
`0044_student_identifier_sequence`.

## Backend Layout

```text
backend/
├── application/                 FastAPI composition and system endpoints
├── core/
│   ├── access/                  roles, permissions, API users, page guards
│   ├── api/                     shared JSON schemas and responses
│   ├── runtime/                 config, observability, performance, limits
│   ├── web/                     rendering, requests, assets, HTML responses
│   ├── jobs.py                  typed worker handler contracts
│   ├── unit_of_work.py          explicit read/write transactions
│   └── database.py              PostgreSQL connection/pool infrastructure
├── modules/
│   ├── people/
│   │   ├── ceo/                 orchestration, contracts, workspace/
│   │   ├── academic_director/   orchestration, contracts, workspace/
│   │   ├── head_of_department/  orchestration, contracts, workspace/
│   │   ├── hr_manager/          orchestration, contracts, workspace/
│   │   ├── customer_support/    orchestration, contracts, workspace/
│   │   ├── teacher/             orchestration, contracts, workspace/
│   │   ├── student/             orchestration, contracts, workspace/
│   │   └── parent/              orchestration, contracts, workspace/
│   ├── domains/
│   │   ├── identity/            accounts, passwords, account linking
│   │   ├── organization/        schools, subjects, classes
│   │   ├── student_records/
│   │   ├── parent_relationships/
│   │   ├── teacher_records/
│   │   ├── academics/           curriculum, groups, timetable, gradebook
│   │   ├── recruitment/
│   │   ├── teacher_academy/
│   │   ├── finance/
│   │   ├── support_cases/
│   │   ├── communications/
│   │   └── reporting/
│   ├── jobs/                    outbox commands, queries, repository, leases
└── platform/                    Redis, storage, Telegram integration
```

Each `people/<person>/workspace/` calls its surrounding person contract. Person
modules own actor-specific orchestration and default scopes, while reusable
domains own rules and SQL. Person modules cannot import one another. Every SQL
statement under `backend/modules` is in a domain or jobs repository.

Customer Support is additionally divided into `dashboard`, `parents`,
`teachers`, and `tickets`. Each section has its own capability and domain
allowlist in `people/customer_support/module.py`. Dashboard projections live in
`reporting/customer_support`, ticket persistence lives in
`support_cases/tickets`, and parent/teacher data is accessed through the public
contracts of its owning domain.

Identity owns password and session helpers. Core is product-agnostic infrastructure. Role workspaces are the only role-facing transport adapters.

## Frontend Layout

```text
frontend/src/
├── app/                         bootstrap and lazy page registry
├── features/
│   ├── identity/
│   ├── people/
│   ├── academics/
│   ├── teacher-academy/
│   ├── support/
│   ├── finance/
│   ├── communications/
│   └── reporting/
├── workspaces/                  role-specific composition
└── shared/                      cross-domain UI, API, and utilities only
```

The old generic `features/management` owner is removed. Workspace adapters import domain features directly. Gradebook and timetable calculations/types are separated from their rendering modules.

## Workspace Note

The current working tree includes a read-only Teacher workspace. Teacher is still managed through People/Teacher Academy records and has no academic mutation permissions. The former System Admin role and Internal Operations workspace were removed in migration `0028`.

## Compatibility Boundaries

- Public REST paths and response shapes remain stable.
- Legacy enrollment/group identifiers are resolved only at compatibility boundaries.
- Attendance, homework, exams, timetable exceptions, and closure history retain their existing IDs.
- `Asia/Tashkent` remains the school calendar timezone.
- There is no runtime Excel or Google Sheets integration.
- Teacher Recruitment is active under `/api/v1/recruitment` and role-scoped pages. Legacy candidate events remain read-only and are copied into the audit timeline.
- Recruitment acceptance into Teacher Academy delegates Teacher account provisioning to `modules/domains/teacher_academy`; Recruitment does not own account persistence.
- Durable background delivery runs as a separate `python main.py worker` process and is not
  started by FastAPI. Recruitment browser reminders retain their compatibility flow; new
  notification handlers use the PostgreSQL outbox.

## Verification

```bash
APP_ENV=test APP_SECRET_KEY=test-secret .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q backend database tgbot scripts main.py
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```
