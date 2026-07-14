# Engineering Overview

Audience: engineers joining or reviewing the MSI LMS rewrite.

## Current System

MSI LMS is a PostgreSQL-first, multi-role web portal. FastAPI owns HTTP/security orchestration, React owns role UI, domain modules own business rules and SQL, and Alembic owns DDL.

```mermaid
flowchart LR
    React[React/Vite]
    Telegram[Telegram Mini App]
    FastAPI[FastAPI]
    Modules[Independent business modules]
    DB[(PostgreSQL msi_v2)]
    Bot[aiogram worker shell]

    React --> FastAPI
    Telegram --> FastAPI
    FastAPI --> Modules --> DB
    Bot -. no inbound routers .-> Modules
```

PostgreSQL is the only LMS data source. Google Sheets and Excel are not integrations. Telegram authentication and Mini App linking remain, but the retired bot-handler/Sheets architecture does not.

## Implemented Architecture Decisions

- One canonical `accounts` row owns login, password hash, role, status, forced-change state, and session version.
- Role data lives in Student, Parent, or staff profiles; teachers remain staff records without portal access.
- Every password-enabled role can change its own password through one v1 endpoint.
- Initial login-equals-password credentials are blocked from workspaces until changed.
- Telegram links authenticate through the same canonical account.
- Parent invites are hash-only, expiring, single-use, and atomically consumed.
- `students.id` is the internal student identity; legacy/public IDs are compatibility boundaries only.
- Runtime SQL is module-owned; the old technical-layer trees are removed.
- Runtime DDL is removed; Alembic repository head is `0008_remove_teacher_portal`.
- APIs are versioned under `/api/v1`; old role API namespaces are gone.
- React uses server bootstrap payloads, role-owned pages, shared accessible UI, and explicit `Asia/Tashkent` time helpers.

## Current Roles

- `system_admin`
- `ceo`
- `academic_director`
- `head_of_department`
- `customer_support`
- `student`
- `parent`

The business roles own separate workspaces. `system_admin` is protected internal operations. Role checks do not replace object checks such as linked child, subject scope, chat membership, or canonical student ownership.

## Important Remaining Compatibility

- physical schema name `msi_v2`;
- selected legacy correlation and public dashboard ID columns;
- remaining `/admin/*` HTML form actions and workspace helper services;
- `admin` presentation/session compatibility for `system_admin`;
- Telegram-first parent accounts without password credentials;
- an empty bot router registry until new inbound commands are product-approved and implemented.

## Release Boundary

Production branch `main` is reference-only during rewrite work. Validate migrations on a disposable clone, run backend/frontend verification, and use an explicitly approved merge/deploy process before production changes.
