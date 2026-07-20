# Engineering Route Map

The executable route inventory is [tests/route_snapshot.txt](../tests/route_snapshot.txt). This document records ownership and canonical entry points.

## Business Workspace Pages

| Workspace | Canonical page root |
| --- | --- |
| CEO | `/ceo` |
| HR Manager | `/hr-manager` |
| Academic Director | `/academic-director` |
| Head of Departments | `/head-of-departments` |
| Customer Support | `/customer-support` |
| Student | `/student` |
| Parent | `/parent` |
| Teacher | `/teacher` |

Recruitment entries are role-scoped: HR Manager owns the workflow, while CEO, Academic Director, and HOD receive their authorized views inside existing workspaces. `/support`, singular `/head-of-department`, and `/hr` are compatibility redirects rather than canonical workspaces.

## Versioned API Ownership

| Namespace | Owner |
| --- | --- |
| `/api/v1/auth/*` | `backend/modules/accounts` |
| `/api/v1/system/*` | `backend/application/system_api.py` |
| `/api/v1/academic-director/*` | Academic Director workspace plus Academics/Staff Records modules |
| `/api/v1/head-of-department/*` | Head of Departments subject-scoped adapter |
| `/api/v1/student/*` | Student workspace plus Student Records modules |

There is no `/api/v1/teacher/*` namespace. Teacher office-hour and Teacher Academy data is managed through authorized business-role workflows.

Teacher Recruitment uses `/api/v1/recruitment/*`. The removed `/admin/teacher-candidates/*` endpoints and Lesson Practice UI are intentionally not restored.

## Public and Compatibility Pages

- `/` renders login; credentials submit to `POST /login`.
- `/account/security` owns the forced/self-service password flow.
- `/auth/telegram` accepts verified Telegram Mini App authentication.
- `/parent/invite/{code}` is the parent invite capability.
- `/dashboard/{student_id}` and its subpages retain public enrollment/dashboard compatibility.
- the former `/admin`, `/api/v1/admin/*`, and `/internal/operations` surfaces are intentionally absent.

New JSON mutations must use `/api/v1/*`. New page links must use canonical workspace roots.
