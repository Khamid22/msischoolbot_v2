# API Migration Status

Date: 2026-07-10

Branch: `FastAPI-Run-System`

The API is versioned under `/api/v1` and composed by `backend/application/api.py`. Business workspace APIs are registered from the matching package under `backend/workspaces`; reusable capabilities are registered from `backend/modules`. The former System Admin API and Internal Operations adapter were removed.

The former `backend/api/v1` tree has been removed. There are no Teacher portal APIs and no non-versioned role API namespaces. `tests/route_snapshot.txt` is the executable contract.

Request flow:

```text
React/Mini App -> FastAPI role workspace adapter -> public module service -> module repository -> PostgreSQL
```

Adapters authenticate, validate, enforce role/object policy, and translate HTTP. They contain no SQL. Module repositories are private to their owner. New JSON mutations use `/api/v1/*`.

Verification:

```bash
APP_ENV=test APP_SECRET_KEY=test-secret python3 -m pytest -q tests/test_route_snapshot.py tests/test_api_v1_architecture.py
```
