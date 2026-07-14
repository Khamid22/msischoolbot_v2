# MSI LMS Portal Architecture

Status: planning document. Do not treat this as implemented code.

Project name: MSI LMS Portal.

Production branch: `main`.

Rewrite branch: `FastAPI-Run-System`.

## Core Decisions

- PostgreSQL is the only source of truth.
- Excel and Google Sheets are import/export sources only.
- Current schools are School 5 and Sehriyo.
- More schools must be supported later without redesigning the system.
- Admin is an internal system operator, not an LMS business role.
- Documentation uses `system_admin`; current code may temporarily still use `admin`.
- One user has one role.
- Real LMS roles are `ceo`, `customer_support`, `student`, `teacher`, `parent`, `academic_director`, and `head_of_department`.
- AI, Google Slides, and adaptive learning are future modules and are outside the first rebuild.

## Current Architecture Inventory

The current branch has four runtime areas:

- `backend/`: FastAPI app, route registration, role routes, domain services, identity helpers, static rendering.
- `frontend/`: Vite React frontend with backend-rendered bootstrap payloads.
- `database/`: PostgreSQL connection, Alembic migrations, raw SQL query modules, academic canonical helpers.
- `tgbot/`: aiogram Telegram bot handlers and keyboards.

Current runtime source of truth is PostgreSQL schema `msi_v2`.

The current code already has useful structure, but boundaries are not clean yet:

- `backend/roles/admin` is the mature workspace, but it mixes several LMS business responsibilities.
- CEO, customer support, and academic director pages exist mostly as shell pages.
- `tgbot` imports `backend.identity`, which couples the bot to the web backend.
- Two permission systems exist: `backend/identity/permissions.py` and `backend/security/permissions.py`.
- The docs describe a future `shared/` and `web/` split, but the actual branch still uses `backend/`, `frontend/`, and `database/`.

## Target Architecture

The target architecture is PostgreSQL-first and domain-first:

```text
frontend -> backend api/workspaces -> domain services -> repositories -> PostgreSQL
tgbot    -> integration adapters     -> domain services -> repositories -> PostgreSQL
imports  -> import services          -> repositories -> PostgreSQL
```

The bot, web backend, and import scripts should not import each other directly.
They should share domain services and repository APIs.

## Target Layers

### Presentation Layer

- React web portal.
- Telegram Mini App surfaces.
- Telegram bot command/callback handlers.

This layer renders data and sends user actions. It should not own business rules.

### Workspace Layer

Workspace modules answer: "What can this role do?"

Examples:

- CEO workspace.
- Academic Director workspace.
- Customer Support workspace.
- Teacher workspace.
- Parent workspace.
- Student workspace.
- System Admin workspace.

### Domain Layer

Domain modules answer: "What business area owns this rule?"

Examples:

- Payments.
- Academic structure.
- Learning delivery.
- Parent linking.
- Support tickets.
- Teacher Academy.

### Repository Layer

Repositories own SQL and persistence details.

Rules:

- No SQL in React.
- No SQL inside Telegram handlers.
- Avoid SQL directly in route functions.
- Use PostgreSQL constraints for identity, uniqueness, and referential integrity.

### Database Layer

PostgreSQL stores canonical application state.

Excel imports, Google Sheets exports, Telegram, and future AI modules are external sources or adapters, not sources of truth.

## Current Academic Data Flow

The Excel academic statistics migration is complete and verified.

Runtime academic data now flows from PostgreSQL:

```text
msi_v2.subjects
msi_v2.subject_programs
msi_v2.subject_program_items
msi_v2.groups
msi_v2.group_students
msi_v2.lesson_sessions
msi_v2.attendance_records
msi_v2.homework_scores
msi_v2.exam_results
```

Excel is now only an import source.

## What To Keep

- PostgreSQL `msi_v2` as the working academic data source.
- Existing Alembic setup.
- Academic canonical helpers for school, subject, text, and date normalization.
- Parent invite concept.
- Telegram HMAC validation.
- Session and same-origin protection ideas.
- Existing React shared UI primitives where they fit the final design system.
- Migration reports and validation discipline.

## What To Delete

Delete after replacement and verification:

- Any live Excel or Google Sheets runtime dependency.
- Admin preview modes as a substitute for real role workspaces.
- Plaintext password storage fields.
- Duplicate permission systems.
- Direct bot imports from backend web modules.
- Dead compatibility helpers once no route uses them.

Do not delete rows or columns casually. Destructive cleanup requires a backup, report, and explicit approval.

## What To Rewrite

- Identity and account model.
- Role authorization and workspace routing.
- Teacher account provisioning to `TCH0001` format.
- Payment and access-control engine.
- Parent Telegram linking as a shared domain service.
- CEO, customer support, and academic director workspaces.
- SQL ownership into domain repositories.

## Target Folder Structure

Proposed target:

```text
backend/
  app/
    core/
      config.py
      db.py
      sessions.py
      security.py
      audit.py
      errors.py
    api/
      v1/
    domains/
      organization/
      people/
      staff_hiring/
      academic_structure/
      learning_delivery/
      assessment_progress/
      learning_resources/
      operations/
      communication_support/
      analytics_reports/
    workspaces/
      ceo/
      customer_support/
      academic_director/
      teacher/
      student/
      parent/
      system_admin/
    integrations/
      telegram/
      excel_import/
      storage/

database/
  alembic/
  repositories/

frontend/
  src/
    app/
    design-system/
    roles/
    shared/

tgbot/
  handlers/
  keyboards/
  services/

scripts/
  imports/
  reports/
```

The exact folder move can happen later. The important first step is ownership:
routes call workspace services, workspace services call domains, domains call repositories.

## Non-Goals For First Rebuild

- AI tutoring.
- Google Slides generation.
- Adaptive learning engine.
- School coordinator role.
- Parent password login.
- Automatic whole-school blocking for unpaid B2B contracts.
- Cleaning duplicate exam keys.

Duplicate exam keys should be investigated later with a dedicated report.
