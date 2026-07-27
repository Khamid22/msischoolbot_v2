# Backend Core

`backend/core` contains framework and runtime infrastructure only. Product rules belong in `backend/modules`.

```text
core/
├── access/                  # Roles, permissions, API users, HTML page guards
│   ├── api.py               # CurrentUser and FastAPI API dependencies
│   ├── pages.py             # Browser-page authorization responses
│   ├── management_permissions.py
│   ├── workspace_permissions.py
│   └── roles.py             # Canonical role names and normalization
├── api/                     # Shared JSON API contracts
│   ├── schemas.py
│   └── responses.py
├── runtime/                 # Process configuration and instrumentation
│   ├── config.py
│   ├── observability.py
│   ├── performance.py
│   └── rate_limit.py
├── web/                     # Browser/HTML infrastructure
│   ├── assets.py
│   ├── error_pages.py
│   ├── rendering.py
│   ├── request_context.py
│   └── responses.py
└── database.py              # PostgreSQL connection and pool infrastructure
```

Identity-owned password and session helpers live in:

- `backend/modules/domains/identity/passwords.py`
- `backend/modules/domains/identity/session.py`

Dependency direction:

```text
application / workspaces / modules → core
core ↛ product modules
```

`web/request_context.py` is the explicitly named compatibility boundary for older form routes. New FastAPI routes should accept `Request`, body models, and dependencies directly instead of extending those proxies.
