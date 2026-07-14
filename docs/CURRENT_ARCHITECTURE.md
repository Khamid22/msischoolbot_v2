# Current Architecture

Date: 2026-07-14

Branch: `FastAPI-Run-System`

Production reference: `main` (read-only)

## System Shape

MSI School is a product-domain modular monolith. PostgreSQL is the sole LMS source of truth; FastAPI composes role-specific adapters; React workspaces compose domain features.

```text
React workspace
  -> FastAPI workspace/internal adapter
    -> domain service or public read contract
      -> owning repository
        -> PostgreSQL (msi_v2)
```

Alembic is the only DDL owner. Migration `0013_teacher_recruitment_mvp.py` preserves historical candidates and adds the normalized recruitment workflow.

## Backend Layout

```text
backend/
├── application/                 FastAPI composition and system endpoints
├── core/
│   ├── access/                  roles, permissions, API users, page guards
│   ├── api/                     shared JSON schemas and responses
│   ├── runtime/                 config, observability, performance, limits
│   ├── web/                     rendering, requests, assets, HTML responses
│   └── database.py              PostgreSQL connection/pool infrastructure
├── modules/
│   ├── identity/                accounts, passwords, Telegram account linking
│   ├── organization/            schools, subjects, classes
│   ├── people/
│   │   ├── students/            student records and student read models
│   │   ├── parents/             parent records and child access
│   │   ├── teachers/            teacher records and management contracts
│   │   └── staff/               managed staff registration and credentials
│   ├── academics/
│   │   ├── curriculum/          programs and scheme of work
│   │   ├── groups/              groups and enrollment
│   │   ├── timetable/           schedules, sessions, reflow, office hours
│   │   ├── lessons/             lesson overrides and one-off changes
│   │   ├── attendance/          attendance records
│   │   ├── gradebook/           homework, rewards, gradebook, trends
│   │   ├── assessments/         exam results
│   │   ├── calendar/            school/group closures and teaching dates
│   │   └── resources/           learning resources and comments
│   ├── teacher_academy/         training, evaluation, progression
│   ├── support/                 complaints and support cases
│   ├── finance/                 payments
│   ├── communications/          chat and announcements
│   └── reporting/               cross-domain read models
├── workspaces/                  role-specific HTTP/page adapters
├── internal_operations/         protected System Admin adapters
│   ├── pages/                    page routes, bootstrap context, options
│   ├── academics/                focused academic route adapters
│   ├── people/                   student and parent adapters
│   ├── staffing/                 active-teacher form adapters
│   ├── resources/                learning-resource adapters
│   ├── finance/                  payment adapters
│   └── support/                  complaint adapters
└── platform/                    Redis, storage, Telegram integration
```

Every SQL statement under `backend/modules` is in a repository module. Services own validation, policy, calculations, transactions, and response assembly. Cross-domain reads use public contracts; a domain never imports another domain's repository.

Identity owns password and session helpers. Core is product-agnostic infrastructure, while Internal Operations is an outer transport adapter: modules and role workspaces never import it.

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
├── internal_operations/         protected System Admin composition
└── shared/                      cross-domain UI, API, and utilities only
```

The old generic `features/management` owner is removed. Workspace adapters import domain features directly. Gradebook and timetable calculations/types are separated from their rendering modules.

## Workspace Note

The current working tree includes a pre-existing read-only Teacher workspace restoration. It remains preserved by this refactor; Teacher is still managed through People/Teacher Academy records and has no academic mutation permissions. System Admin remains isolated at `/internal/operations`.

## Compatibility Boundaries

- Public REST paths and response shapes remain stable.
- Legacy enrollment/group identifiers are resolved only at compatibility boundaries.
- Attendance, homework, exams, timetable exceptions, and closure history retain their existing IDs.
- `Asia/Tashkent` remains the school calendar timezone.
- There is no runtime Excel or Google Sheets integration.
- Teacher Recruitment is active under `/api/v1/recruitment` and role-scoped pages. Legacy candidate events remain read-only and are copied into the audit timeline.

## Verification

```bash
APP_ENV=test APP_SECRET_KEY=test-secret .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q backend database tgbot scripts main.py
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```
