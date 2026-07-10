# Backend Modules

The LMS is a modular monolith. Each business capability owns its HTTP adapters,
schemas, policy/service code, and persistence. Roles are authorization contexts;
they do not call one another.

Runtime flow:

```text
React or Telegram -> module API/page -> access policy -> module service -> repository -> PostgreSQL
```

Rules:

- `api.py`, `*_api.py`, `page.py`, and `*_page.py` are thin HTTP adapters.
- `service.py`, `operations.py`, and focused workflow modules own business rules and transactions.
- `repository.py` owns SQL. HTTP/page/workspace files must not contain SQL.
- A module may call another module's public service, never another role's page/API.
- `registry.py` and `router.py` are the only application-wide HTTP composition points.
- Alembic is the only DDL owner.
- PostgreSQL is the only application data source; there is no spreadsheet integration.

Modules include identity, portal, students, teachers, parents, academics,
office hours, Teacher Academy, announcements, communication, complaints,
payments, resources, staff workspaces, system administration, and system HTTP.
