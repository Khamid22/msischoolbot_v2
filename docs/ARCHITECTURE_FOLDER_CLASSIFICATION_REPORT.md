# Architecture Folder Classification Report

Branch: FastAPI-Run-System

Scope:
- `backend/api/v1/`
- `backend/domains/`
- `backend/core/`
- `backend/security/`
- `frontend/src/shared/api/`

## Summary

The new architecture is kept. Real API, domain, core, security, and frontend API helper modules remain in place. Only unused empty placeholder directories were removed:

- `backend/api/v1/workspaces/`
- `backend/domains/people/`

No database schema, Alembic history, role page URL, Telegram Mini App flow, or auth behavior was changed.

## backend/api/v1

| Path | Classification | Reason |
| --- | --- | --- |
| `backend/api/v1/` | KEEP_REAL_CODE | API v1 root package and router registry are active. |
| `backend/api/v1/router.py` | KEEP_REAL_CODE | Registers active role API routers under `/api/v1`. |
| `backend/api/v1/teacher_academy_actions.py` | KEEP_REAL_CODE | Shared Pydantic forms and response adapters used by AD/HOD Teacher Academy APIs. |
| `backend/api/v1/README.md` | KEEP_REAL_CODE | Documents the active v1 route standard. |
| `backend/api/v1/auth/routes.py` | KEEP_REAL_CODE | Active auth/status endpoint. |
| `backend/api/v1/system/routes.py` | KEEP_REAL_CODE | Active system API endpoint. |
| `backend/api/v1/admin/` | KEEP_REAL_CODE | Active admin v1 API package. |
| `backend/api/v1/admin/academic.py` | KEEP_REAL_CODE | Admin academic API routes migrated from legacy admin routes. |
| `backend/api/v1/admin/announcements.py` | KEEP_REAL_CODE | Admin announcements API routes. |
| `backend/api/v1/admin/chat.py` | KEEP_REAL_CODE | Admin chat API routes. |
| `backend/api/v1/admin/complaints.py` | KEEP_REAL_CODE | Admin support/complaints API routes. |
| `backend/api/v1/admin/office_hours.py` | KEEP_REAL_CODE | Admin office-hours API routes. |
| `backend/api/v1/admin/parents.py` | KEEP_REAL_CODE | Admin parent API routes. |
| `backend/api/v1/admin/payments.py` | KEEP_REAL_CODE | Admin payment API routes. |
| `backend/api/v1/admin/resources.py` | KEEP_REAL_CODE | Admin resource API routes. |
| `backend/api/v1/admin/router.py` | KEEP_REAL_CODE | Registers active admin API modules. |
| `backend/api/v1/admin/schemas.py` | KEEP_REAL_CODE | Pydantic request/response models for admin v1 APIs. |
| `backend/api/v1/admin/students.py` | KEEP_REAL_CODE | Admin student API routes. |
| `backend/api/v1/academic_director/` | KEEP_REAL_CODE | Active Academic Director v1 API package. |
| `backend/api/v1/academic_director/router.py` | KEEP_REAL_CODE | Role router and HOD account creation API. |
| `backend/api/v1/academic_director/schemas.py` | KEEP_REAL_CODE | Pydantic models for Academic Director APIs. |
| `backend/api/v1/academic_director/teacher_academy.py` | KEEP_REAL_CODE | Academic Director Teacher Academy action APIs. |
| `backend/api/v1/head_of_department/` | KEEP_REAL_CODE | Active Head of Department v1 API package. |
| `backend/api/v1/head_of_department/router.py` | KEEP_REAL_CODE | Role router including HOD Teacher Academy APIs. |
| `backend/api/v1/head_of_department/teacher_academy.py` | KEEP_REAL_CODE | Subject-scoped HOD Teacher Academy action APIs. |
| `backend/api/v1/student/` | KEEP_REAL_CODE | Active student API package. |
| `backend/api/v1/student/activity.py` | KEEP_REAL_CODE | Student activity API. |
| `backend/api/v1/student/chat.py` | KEEP_REAL_CODE | Student chat API. |
| `backend/api/v1/student/comments.py` | KEEP_REAL_CODE | Student resource comments API. |
| `backend/api/v1/student/office_hours.py` | KEEP_REAL_CODE | Student office-hours API. |
| `backend/api/v1/student/router.py` | KEEP_REAL_CODE | Registers active student API modules. |
| `backend/api/v1/student/schemas.py` | KEEP_REAL_CODE | Student API schemas. |
| `backend/api/v1/teacher/` | KEEP_REAL_CODE | Active teacher API package. |
| `backend/api/v1/teacher/office_hours.py` | KEEP_REAL_CODE | Teacher office-hours API. |
| `backend/api/v1/teacher/router.py` | KEEP_REAL_CODE | Registers active teacher API modules. |
| `backend/api/v1/teacher/schemas.py` | KEEP_REAL_CODE | Teacher API schemas. |
| `backend/api/v1/parent/router.py` | FILL_LATER_KEEP_WITH_REASON | No child routes yet, but it is registered by `backend/api/v1/router.py`; deleting it would break startup import composition. |
| `backend/api/v1/ceo/router.py` | FILL_LATER_KEEP_WITH_REASON | No child routes yet, but it is registered by `backend/api/v1/router.py`; keep until CEO APIs are migrated. |
| `backend/api/v1/hr_manager/router.py` | FILL_LATER_KEEP_WITH_REASON | No child routes yet, but it is registered by `backend/api/v1/router.py`; keep until HR APIs are migrated. |
| `backend/api/v1/customer_support/router.py` | FILL_LATER_KEEP_WITH_REASON | No child routes yet, but it is registered by `backend/api/v1/router.py`; keep until support APIs are migrated. |
| `backend/api/v1/*/__init__.py` | FILL_LATER_KEEP_WITH_REASON | Package markers required for importable router packages. |
| `backend/api/v1/workspaces/` | DELETE_EMPTY_PLACEHOLDER | Empty unused placeholder tree; no router registration, imports, or tests depend on it. Deleted. |

## backend/domains

| Path | Classification | Reason |
| --- | --- | --- |
| `backend/domains/` | KEEP_REAL_CODE | Domain package root. |
| `backend/domains/teacher_academy/service.py` | KEEP_REAL_CODE | Teacher Academy business logic. |
| `backend/domains/teacher_academy/queries.py` | KEEP_REAL_CODE | Teacher Academy SQL/query ownership. |
| `backend/domains/teachers/service.py` and `queries.py` | KEEP_REAL_CODE | Teacher domain services and SQL helpers. |
| `backend/domains/students/service.py` and `queries.py` | KEEP_REAL_CODE | Student domain services and SQL helpers. |
| `backend/domains/parents/service.py` and `queries.py` | KEEP_REAL_CODE | Parent domain services and SQL helpers. |
| `backend/domains/academics/*` | KEEP_REAL_CODE | Academic datasets, ratings, filters, and PostgreSQL helpers. |
| `backend/domains/announcements/service.py` and `queries.py` | KEEP_REAL_CODE | Announcement domain services and SQL helpers. |
| `backend/domains/complaints/service.py` | KEEP_REAL_CODE | Support/complaint business logic. |
| `backend/domains/payments/service.py` | KEEP_REAL_CODE | Payment business logic. |
| `backend/domains/resources/service.py` and `comments_service.py` | KEEP_REAL_CODE | Resource and comment business logic. |
| `backend/domains/communication/chat_service.py` | KEEP_REAL_CODE | Chat business logic. |
| `backend/domains/office_hours/service.py` | KEEP_REAL_CODE | Office-hours business logic. |
| `backend/domains/timetable/queries.py` | KEEP_REAL_CODE | Timetable query helpers. |
| `backend/domains/identity/service.py` and `routes.py` | KEEP_REAL_CODE | Identity/domain auth flow registration still active. |
| `backend/domains/*/__init__.py` | FILL_LATER_KEEP_WITH_REASON | Package markers required for active domain imports. |
| `backend/domains/people/` | DELETE_EMPTY_PLACEHOLDER | Empty unused placeholder directory; no imports or tests depend on it. Deleted. |

## backend/core

| Path | Classification | Reason |
| --- | --- | --- |
| `backend/core/` | KEEP_REAL_CODE | Shared infrastructure package. |
| `backend/core/database.py` | KEEP_REAL_CODE | Clean import path wrapping active DB connection helpers. |
| `backend/core/security.py` | KEEP_REAL_CODE | Password hash generation and verification helpers. |
| `backend/core/config.py` | KEEP_REAL_CODE | Clean package import path for runtime settings helpers. |
| `backend/core/README.md` | KEEP_REAL_CODE | Updated to describe real core modules. |
| `backend/core/__init__.py` | FILL_LATER_KEEP_WITH_REASON | Package marker required for active `backend.core.*` imports. |

## backend/security

| Path | Classification | Reason |
| --- | --- | --- |
| `backend/security/` | KEEP_REAL_CODE | Active security dependency package. |
| `backend/security/dependencies.py` | KEEP_REAL_CODE | CurrentUser, role, and permission FastAPI dependencies. |
| `backend/security/roles.py` | KEEP_REAL_CODE | Canonical role registry and role helpers. |
| `backend/security/permissions.py` | KEEP_REAL_CODE | Permission map and permission checks. |
| `backend/security/__init__.py` | KEEP_REAL_CODE | Public security import surface. |

## frontend/src/shared/api

| Path | Classification | Reason |
| --- | --- | --- |
| `frontend/src/shared/api/` | KEEP_REAL_CODE | Frontend API helper package. |
| `frontend/src/shared/api/routes.ts` | KEEP_REAL_CODE | AD/HOD/student API route constants pointing at `/api/v1`. |
