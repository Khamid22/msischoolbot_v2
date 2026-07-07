# Wrapper Classification Report

Branch: FastAPI-Run-System

## Search Commands

- `rg "compatibility|Compatibility|wrapper|re-export|sys.modules|globals\\(\\)\\.update|from .* import \\*" backend`
- `rg "backend.identity.account_service"`
- `rg "backend.roles.common.teacher_academy_api"`
- `rg "backend.roles.admin.services.teacher_academy_service"`
- `rg "backend.identity.account_auth_v2"`
- `rg "backend.identity.account_telegram_auth_v2"`
- `rg "backend.identity.profiles"`

## DELETE_NOW

These wrappers have no active app imports, clean replacements exist, and startup does not require the old path:

| Old path | Clean replacement | Status |
| --- | --- | --- |
| `backend.identity.account_service` | `backend.identity.storage`, `backend.identity.account_auth`, `backend.identity.account_telegram_auth`, and domain services | Already deleted. `main.py` imports `init_storage` from `backend.identity.storage`. |
| `backend.identity.account_auth_v2` | `backend.identity.account_auth` | Already deleted. Tests assert the old import raises `ModuleNotFoundError`. |
| `backend.identity.account_telegram_auth_v2` | `backend.identity.account_telegram_auth` | Already deleted. Tests assert the old import raises `ModuleNotFoundError`. |
| `backend.identity.profiles` | Domain-specific identity/profile services | Already deleted. Tests assert the old import raises `ModuleNotFoundError`. |
| `backend.roles.common.teacher_academy_api` | `backend/api/v1/academic_director/teacher_academy.py`, `backend/api/v1/head_of_department/teacher_academy.py`, and `backend/api/v1/teacher_academy_actions.py` | Already deleted. No active imports remain. |
| `backend.roles.admin.services.teacher_academy_service` | `backend.domains.teacher_academy.service` and `backend.domains.teacher_academy.queries` | Already deleted. Tests assert absence. |

## REPLACE_IMPORTS_THEN_DELETE

No wrapper in this pass is in the middle state. AD/HOD Teacher Academy API route code was moved into role-specific v1 modules before this report:

- `backend/api/v1/academic_director/teacher_academy.py`
- `backend/api/v1/head_of_department/teacher_academy.py`

The shared API helper remains real shared code:

- `backend/api/v1/teacher_academy_actions.py`

## KEEP_TEMPORARILY

These wrappers still have active imports or test coverage. They now carry the required temporary compatibility comment.

| Wrapper | Active import evidence | Clean target | Reason kept |
| --- | --- | --- | --- |
| `backend/identity/parent_accounts.py` | `tgbot/handlers/start.py`, `tgbot/helpers.py`, `tests/test_database_restructure_db4_parents.py` | `backend.domains.parents.service` | Telegram parent flow still imports this path. |
| `backend/identity/parent_invites.py` | `tgbot/handlers/start.py`, `tests/test_database_restructure_db4_parents.py` | `backend.domains.parents.service` | Telegram invite flow still imports this path. |
| `backend/roles/admin/services/parent_service.py` | `tests/test_database_restructure_db4_parents.py` | `backend.domains.parents.service` | Kept for compatibility coverage until admin imports are fully retired. |
| `backend/roles/parent/services.py` | `tests/test_database_restructure_db4_parents.py` | `backend.domains.parents.service` | Kept for compatibility coverage until parent role imports are fully retired. |
| `config.py` | External/root imports; current app code has moved to `backend.core.config` | `backend.core.config` | Kept as a root compatibility import surface. |
| `database/database.py` | External/direct legacy imports; `database/__init__.py` and Alembic now use core directly | `backend.core.database` | Kept as a direct legacy compatibility import surface. |
| `database/queries/__init__.py` | Many active `from database import queries` imports in backend/domain/role code | Domain query modules and `backend.core.database` | Central query barrel is still broadly active. |
| `database/cross_queries/__init__.py` | Re-export surface for shared query package | Domain query modules plus Telegram-specific query modules | Active until shared query ownership is separated. |
| `database/queries/teacher_queries.py` | `tests/test_database_restructure_db2_teachers.py`, `tests/test_teacher_academy_tomorrow_ready.py` | `backend.domains.teachers.queries` | Compatibility tests and Teacher Academy helper references remain. |
| `database/cross_queries/student_queries.py` | `tests/test_database_restructure_db3_students.py` | `backend.domains.students.queries` | Compatibility coverage remains. |
| `database/queries/parent_account_queries.py` | `tests/test_database_restructure_db4_parents.py` | `backend.domains.parents.queries` | Compatibility coverage remains. |
| `database/queries/parent_queries.py` | `tests/test_database_restructure_db4_parents.py` | `backend.domains.parents.queries` | Compatibility coverage remains. |
| `database/queries/payment_queries.py` | Legacy query barrel imports | `backend.domains.payments.queries` | Kept as a wrapper while the database query barrel remains active. |
| `database/queries/announcement_queries.py` | `tests/test_database_restructure_db5_academics.py` | `backend.domains.announcements.queries` | Compatibility coverage remains. |

## Active Code Moved Or Clarified

- AD Teacher Academy action routes now live in `backend/api/v1/academic_director/teacher_academy.py`.
- HOD Teacher Academy action routes now live in `backend/api/v1/head_of_department/teacher_academy.py`.
- Teacher Academy business logic remains in `backend/domains/teacher_academy/service.py`.
- Teacher Academy SQL remains in `backend/domains/teacher_academy/queries.py`.
- `backend/core/config.py` owns runtime settings helpers.
- `backend/core/database.py` owns DB connection and pooling helpers; `database/database.py` is now only a compatibility wrapper.
