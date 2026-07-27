# MSI LMS Portal Documentation

This directory contains product history, migration reports, and the current engineering documentation for MSI LMS Portal.

## Current Source of Truth

Read these first. They describe the implemented rewrite rather than an earlier target design:

1. [Current Architecture](./CURRENT_ARCHITECTURE.md)
2. [Authentication and Roles](./ENGINEERING_AUTH_AND_ROLES.md)
3. [Database Architecture](./ENGINEERING_DATABASE.md)
4. [Engineering Architecture](./ENGINEERING_ARCHITECTURE.md)
5. [Module Map](./ENGINEERING_MODULE_MAP.md)
6. [Route Map](./ENGINEERING_ROUTE_MAP.md)
7. [Telegram Integration](./ENGINEERING_TELEGRAM_FLOW.md)

The physical PostgreSQL schema remains `msi_v2`; use the current Alembic head in `database/alembic/versions`.

## Current Project Facts

- Production branch `main` is read-only during rewrite work.
- PostgreSQL is the canonical runtime data store.
- `msi_v2.accounts` is the sole password authority.
- Runtime SQL belongs to an owning domain repository under `backend/modules`.
- Runtime DDL is prohibited; `database/alembic` owns schema changes.
- Google Sheets and Excel are not LMS integrations.
- Telegram authentication and Mini App parent linking remain active web integrations.
- `tgbot` owns the portal-entry command; durable outbound work is owned by the PostgreSQL worker.
- The current tree includes a read-only Teacher workspace; Teacher remains staff data managed by authorized roles. The former System Admin and Internal Operations surfaces were removed.

## Supporting Engineering Docs

- [Engineering Overview](./ENGINEERING_OVERVIEW.md)
- [Engineering Architecture](./ENGINEERING_ARCHITECTURE.md)
- [Engineering Deployment](./ENGINEERING_DEPLOYMENT.md)
- [Engineering Testing](./ENGINEERING_TESTING.md)
- [Payment Access Policy](./ENGINEERING_PAYMENT_ACCESS_POLICY.md)
- [Database Folder Migration Status](./DATABASE_FOLDER_MIGRATION_STATUS.md)
- [Glossary](./GLOSSARY.md)

## Product and Leadership Docs

- [CEO Overview](./CEO_OVERVIEW.md)
- [CEO Product Vision](./CEO_PRODUCT_VISION.md)
- [CEO Roadmap](./CEO_ROADMAP.md)
- [CEO Risks and Decisions](./CEO_RISKS_AND_DECISIONS.md)

## Historical Material

Files named as blueprints, phase plans, target schemas, or dated cleanup reports record earlier decisions and migration states. They are useful history but can mention modules or wrappers that have since been deleted. The current-source list above takes precedence.

Historical phase plans are under [docs/archive](./archive/).

## Documentation Rules

- Do not include credentials, connection strings, tokens, student names, phone numbers, Telegram IDs, grades, or other row-level private data.
- Distinguish implemented behavior from a proposed future design.
- Keep production `main` read-only unless an explicitly approved release process says otherwise.
