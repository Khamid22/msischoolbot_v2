# FastAPI API Foundation

This is the mandatory route standard for new and migrated backend API endpoints.
The API plane is JSON only and lives under `backend/api/v1`. HTML shell routes
belong in the pages/role route layer until the `backend/pages` split lands.

## Route Standard

Every migrated endpoint must follow these six rules:

1. Inputs are declared with FastAPI and Pydantic: `Form()`, `Query()`, path
   parameters, or a Pydantic body model. Do not use the legacy request proxy or
   `request_payload`.
2. Outputs use the `ApiSuccess[T]` envelope with `response_model=` and
   `api_success(...)`. Do not return `jsonify(...)`, `{"ok": ...}`, or bare
   message dictionaries from v1 routes.
3. Operational failures raise `HTTPException`. Do not hand-roll JSON error
   responses inside handlers.
4. Auth is resolved by router dependencies and `CurrentUser` from
   `backend.security.dependencies`. Do not call `current_auth_*()` inside API
   handlers.
5. Route modules do not open database connections or run SQL. They call
   domain services; SQL lives in `backend/domains/*/queries.py`.
6. Do not hide unexpected failures behind blanket `except Exception` defaults.
   Let the global handler log them.

## Canonical Example

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException

from backend.api import ApiSuccess, api_success
from backend.security import CurrentUser, get_current_user, require_role

router = APIRouter(
    prefix="/academic-director",
    dependencies=[Depends(require_role("academic_director"))],
)


@router.post("/head-of-departments", response_model=ApiSuccess[HodCreated])
def create_hod(
    payload: Annotated[CreateHodForm, Form()],
    user: CurrentUser = Depends(get_current_user),
):
    created, error, creds = create_head_of_department_account(
        display_name=payload.hod_display_name,
        subject_id=payload.hod_subject_id,
        created_by=user.login,
    )
    if not created:
        raise HTTPException(400, error or "Unable to create Head of Department.")
    return api_success(HodCreated.from_credentials(creds))
```

## Shared Contracts

- Response envelopes: `backend/api/schemas.py` and `backend/api/responses.py`.
- Security dependencies: `backend/security/dependencies.py`.
- Role and permission constants: `backend/security/roles.py` and
  `backend/security/permissions.py`.
- Canonical frontend API URLs: `frontend/src/shared/api/routes.ts`.

## Migration Proofs

For a slice to count as clean, these checks should not find hits inside its v1
route modules:

```bash
rg "from backend.utils.context|request\\.form|jsonify\\(|request_payload" backend/api/v1
rg "connect_auth_db" backend/api/v1
```

The OpenAPI `/docs` page should show request schemas and `ApiSuccess[...]`
responses for every JSON endpoint in the migrated slice.
