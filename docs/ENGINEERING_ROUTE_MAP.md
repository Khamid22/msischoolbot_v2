# Engineering Route Map

The executable route inventory is [tests/route_snapshot.txt](../tests/route_snapshot.txt). This document records ownership and canonical entry points.

## Business Workspace Pages

| Workspace | Canonical page root |
| --- | --- |
| CEO | `/ceo` |
| Academic Director | `/academic-director` |
| Head of Departments | `/head-of-departments` |
| Customer Support | `/customer-support` |
| HR Manager | `/hr-manager` |
| Student | `/student` |
| Parent | `/parent` |

System Admin uses `/internal/operations`. Teacher has no portal route. `/hr`, `/support`, singular `/head-of-department`, and `/admin` page entry points are redirects/compatibility boundaries, not canonical workspaces.

## Versioned API Ownership

| Namespace | Owner |
| --- | --- |
| `/api/v1/auth/*` | `backend/modules/accounts` |
| `/api/v1/system/*` | `backend/application/system_api.py` |
| `/api/v1/academic-director/*` | Academic Director workspace plus Academics/Staff Records modules |
| `/api/v1/head-of-department/*` | Head of Departments subject-scoped adapter |
| `/api/v1/student/*` | Student workspace plus Student Records modules |
| `/api/v1/admin/*` | protected internal-operations compatibility API |

There is no `/api/v1/teacher/*` namespace. Teacher office-hour and Teacher Academy data is managed through authorized business/internal workflows.

## Public and Compatibility Pages

- `/` renders login; credentials submit to `POST /login`.
- `/account/security` owns the forced/self-service password flow.
- `/auth/telegram` accepts verified Telegram Mini App authentication.
- `/parent/invite/{code}` is the parent invite capability.
- `/dashboard/{student_id}` and its subpages retain public enrollment/dashboard compatibility.
- selected `/admin/*` form actions remain protected compatibility routes into internal operations.

New JSON mutations must use `/api/v1/*`. New page links must use canonical workspace roots.
