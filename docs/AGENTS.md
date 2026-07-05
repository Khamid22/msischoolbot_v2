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
- Internal System Admin

## Current Important Decisions

- Production branch is `main`.
- Rewrite/planning branch is `FastAPI-Run-System`.
- PostgreSQL is the source of truth.
- Excel/Google Sheets are import/export sources only, not live runtime dependencies.
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
- Teacher login format should be `TCH0001`, `TCH0002`, etc.
- Students login with MSI code + password.
- Parents are Telegram-first in the first rebuild.
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
