# MSI LMS Portal - Codex Instructions

## Project Name

MSI LMS Portal

## Product Vision

MSI LMS Portal is a PostgreSQL-first, multi-school, multi-role IGCSE LMS platform.

The system supports:

- Schools
- Students
- Teachers
- Parents
- CEO
- HR Manager
- Customer Support
- Academic Director
- Head of Department
- Internal System Admin

## Current Important Decisions

- Production branch is `main`.
- Rewrite/planning branch is `FastAPI-Run-System`.
- Treat production `main` as read-only during rewrite work unless the user explicitly approves a release action.
- PostgreSQL is the source of truth.
- Google Sheets is retired as a live runtime dependency. Excel is used only through explicit import/reconciliation tooling.
- `msi_v2.accounts` is the sole password authority; role tables must not provide fallback password hashes.
- PostgreSQL DDL is Alembic-only. Use the current repository migration head; do not hard-code a historical revision in runtime code.
- Runtime SQL belongs to the owning `repository.py` under `backend/modules`; application, workspace, adapter, and service modules contain no SQL.
- Current schools: School 5 and Sehriyo.
- More schools will be added later.
- One user has exactly one role.
- `system_admin` is internal operator/superuser, not an LMS business role.
- Real LMS roles are:
  - `ceo`
  - `hr_manager`
  - `customer_support`
  - `student`
  - `teacher`
  - `parent`
  - `academic_director`
  - `head_of_department`
- Teacher login format is `TCH0001`, `TCH0002`, etc. The current read-only Teacher workspace is preserved; teacher records remain managed by authorized staff.
- Students login with MSI code + password.
- Login-equals-password credentials must force self-service password change before workspace access.
- Parents are Telegram-first in the first rebuild.
- Telegram auth resolves canonical accounts; inbound bot handlers are currently empty.
- Customer Support is B2C support: parents, payments, warnings, follow-up, support tickets.
- B2B unpaid school contract issues escalate to CEO only.
- Academic Director has full academic access.
- CEO has broad visibility across company operations.
- AI, Google Slides, and adaptive learning are future modules, not current implementation.

## Coding Rules

- Do not implement unless explicitly asked.
- Do not push unless explicitly asked.
- Do not expose secrets or private student data in docs.
- Do not commit backups, CSV dumps, `.env`, tokens, or private migration data.
- Separate planning docs from implementation.
- Keep architecture docs honest: distinguish current implementation from target architecture.

## Documentation Rules

When asked to document:

- Create CEO-friendly documentation separately from engineer-facing documentation.
- Use clear diagrams.
- Include current state, target state, risks, and migration phases.
- Do not invent features that do not exist.
- Mark future features clearly as planned/future.
