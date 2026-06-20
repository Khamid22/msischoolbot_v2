# FastAPI API & Security Foundation

This document describes the role permissions, Pydantic schemas, and security dependencies designed for professionalizing backend route implementations in the MSI School project.

---

## 1. Supported Roles

All backend roles are defined as string constants under `web/backend/security/roles.py`:

*   `ROLE_OWNER = "owner"` (Super-admin with access to all settings and operations)
*   `ROLE_CEO = "ceo"` (Executive role with dashboard and data management access)
*   `ROLE_ADMIN = "admin"` (Administrative operations including user, teacher, parent, resource, and schedule management)
*   `ROLE_TEACHER = "teacher"` (Academics and study material resources management)
*   `ROLE_CUSTOMER_SUPPORT = "customer_support"` (Viewing complaints, chat message handling, and user viewing)
*   `ROLE_PARENT = "parent"` (Read-only student dashboard views for their linked children)
*   `ROLE_STUDENT = "student"` (Read-only personal student dashboard access)

---

## 2. Permissions & Mapping

Permissions are granular actions mapped to roles in `web/backend/security/permissions.py`:

*   `PERMISSION_VIEW_DASHBOARD`
*   `PERMISSION_MANAGE_STUDENTS`
*   `PERMISSION_MANAGE_TEACHERS`
*   `PERMISSION_MANAGE_PARENTS`
*   `PERMISSION_MANAGE_ANNOUNCEMENTS`
*   `PERMISSION_MANAGE_RESOURCES`
*   `PERMISSION_MANAGE_COMPLAINTS`
*   `PERMISSION_MANAGE_PAYMENTS`
*   `PERMISSION_MANAGE_ACADEMICS`
*   `PERMISSION_SYSTEM_SETTINGS`

### Role-Permission Matrix

| Permission | Owner | CEO | Admin | Teacher | Support | Parent | Student |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `view_dashboard` | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| `manage_students` | Yes | Yes | Yes | - | - | - | - |
| `manage_teachers` | Yes | Yes | Yes | - | - | - | - |
| `manage_parents` | Yes | Yes | Yes | - | - | - | - |
| `manage_announcements`| Yes | Yes | Yes | - | - | - | - |
| `manage_resources` | Yes | Yes | Yes | Yes | - | - | - |
| `manage_complaints` | Yes | Yes | Yes | - | Yes | - | - |
| `manage_payments` | Yes | Yes | Yes | - | - | - | - |
| `manage_academics` | Yes | Yes | Yes | Yes | - | - | - |
| `system_settings` | Yes | - | - | - | - | - | - |

---

## 3. Dependency Injection

FastAPI routes should protect themselves using security dependencies defined in `web/backend/security/dependencies.py`:

### `Depends(get_current_user_role)`
Resolves the current active session role (raising 401 if unauthenticated).

### `Depends(require_role(allowed_roles))`
Restricts endpoint access to specific roles (raising 403 if role mismatch).

```python
from fastapi import APIRouter, Depends
from web.backend.security import require_role, ROLE_ADMIN, ROLE_OWNER

router = APIRouter()

@router.get("/admin/settings")
def get_settings(role: str = Depends(require_role([ROLE_ADMIN, ROLE_OWNER]))):
    return {"message": "Hello Administrator!"}
```

### `Depends(require_permission(required_permission))`
Restricts endpoint access to users possessing the specified permission (raising 403 if permission is missing).

```python
from fastapi import APIRouter, Depends
from web.backend.security import require_permission, PERMISSION_MANAGE_RESOURCES

router = APIRouter()

@router.post("/resources/upload")
def upload_resource(role: str = Depends(require_permission(PERMISSION_MANAGE_RESOURCES))):
    return {"message": "Resource successfully uploaded."}
```

---

## 4. Standard Response Formats

API response shapes are defined as Pydantic models under `web/backend/api/schemas.py`. Use the response helper functions under `web/backend/api/responses.py` to return standardized shapes.

### Success Response (`ApiSuccess[T]`)
Returned for successful API calls containing a data payload.
```json
{
  "status": "success",
  "data": {
    "login": "MSI0001",
    "role": "student"
  }
}
```
*Helper Usage:*
```python
from web.backend.api import api_success
return api_success(user_data)
```

### Message Response (`ApiMessage`)
Returned for simple actions that yield a generic status message.
```json
{
  "status": "success",
  "message": "Operation completed successfully."
}
```
*Helper Usage:*
```python
from web.backend.api import api_message
return api_message("Announcement deleted successfully.")
```

### Error Response (`ApiError`)
Returned for operational, validation, or system errors.
```json
{
  "status": "error",
  "message": "Resource was not found.",
  "code": "RESOURCE_NOT_FOUND",
  "details": {
    "resource_id": 42
  }
}
```
*Helper Usage:*
```python
from web.backend.api import api_error
return api_error(message="Invalid parameters", code="VALIDATION_FAILED", status_code=400)
```
