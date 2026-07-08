# FastAPI Clean Architecture Blueprint

Date: 2026-07-08
Scope: backend only. Diagnosis of the current state plus the complete file-level inventory — what to delete, what to create, what to rewrite — to reach the conventional FastAPI layout (routers → dependencies → services → queries, Pydantic contracts, one URL scheme, one envelope).

Status baseline: branch `FastAPI-Run-System`, after the 2026-07-08 Teacher Academy cleanup slice.

---

## 1. Diagnosis (current state)

| Area | State |
| --- | --- |
| Runtime routes total | 145 |
| Runtime `/api/v1/*` routes | 76 |
| Runtime legacy `/admin/api`, `/teacher/api`, role `/api`, or bare non-v1 `/api/*` routes | 0 |
| Page/form routes | 57 |
| Static/docs/public routes | 12 |
| Pydantic request models | Partial: AD/HOD Teacher Academy, student, teacher office-hours, and migrated admin slices use schemas; old form routes still use compatibility parsing |
| `response_model` usage | Broad in migrated `/api/v1` slices; remaining old page/form routes are still untyped |
| Response envelopes in production | 3 (`{"ok"}`, `{"status","data"}`, bare `{"message"}`) |
| Role registries / permission maps | 2 of each (`identity/` vs `security/`) |
| Direct DB connections inside `backend/roles/` | 33 (SQL belongs in `domains/*/queries.py`) |
| Flask emulation layer | `utils/context.py` proxies + `RequestContextMiddleware` body pre-consumption + `jsonify`/`redirect` shims |

Root problem: the codebase runs Flask idioms on FastAPI. The `/api/v1` skeleton is now real, but its first 10 routes copied the Flask idioms (global `request` proxy, `jsonify`, `{"ok"}` envelope), so the pattern must be corrected **before** the remaining ~120 routes migrate.

What is already correct and must NOT change:

- `backend/domains/*` — service.py + queries.py split. This is the strongest layer; every migrated route plugs into it unchanged.
- `backend/api/schemas.py` + `backend/api/responses.py` — the `ApiSuccess`/`ApiError` envelope (exists, underused).
- `backend/api/v1/router.py` per-role aggregation under `/api/v1`.
- `backend/api/v1/teacher_academy/{schemas,responses}.py` owns shared Teacher Academy API schemas/adapters.
- `backend/domains/teacher_academy/{permissions,notifications}.py` owns HOD scope checks and academy notification helpers. Permission functions now accept `CurrentUser` or explicit identity context instead of reading the legacy request/session proxy.
- `backend/pages/{ceo,hr_manager,customer_support}.py` owns the three page-only role shells; their old role route modules are compatibility re-exports.
- `AuthAndSecurityMiddleware` security ideas: same-origin/CSRF check, fail-closed secret key, security headers, cache-control policy (to be slimmed, not removed).
- `backend/core/` (config, database, security), `backend/integrations/`, `render.py` page rendering.

---

## 2. Target structure

```text
backend/
  main.py                      entrypoint (exists, unchanged)
  server.py                    slim create_app(): middleware, exception handlers,
                               include_router() calls only (~100 lines)
  core/
    config.py                  exists
    security.py                exists (absorbs the werkzeug hash call)
    db.py                      NEW — Depends-able connection provider
    assets.py                  NEW — asset version + static dir (kills bootstrap monkey-patching)
  security/                    THE single auth authority
    roles.py                   one merged role registry
    permissions.py             one merged permission map
    dependencies.py            CurrentUser, get_current_user, require_role(), require_permission()
  api/
    schemas.py, responses.py   exist — the only envelope
    v1/
      router.py                exists — aggregate /api/v1
      auth/  system/           exist
      {role}/                  router.py + schemas.py (+ per-panel modules for admin)
  pages/                       NEW — HTML shell routes (session auth, redirect on failure)
    public.py                  /, /login, /unauthorized, /manifest.webmanifest, /sw.js
    admin.py teacher.py student.py parent.py ceo.py hr_manager.py
    customer_support.py academic_director.py head_of_department.py
  domains/                     UNCHANGED
  integrations/                UNCHANGED
  render.py                    kept; reads from core/assets.py instead of patched globals
```

Two planes, never mixed in one module:

- **Pages plane** (`pages/`): returns `render_react_page(...)` HTML, redirects to `/` on auth failure.
- **API plane** (`api/v1/`): JSON only, Pydantic in, `ApiSuccess[...]` out, `HTTPException` errors.

---

## 3. DELETE inventory

### 3.1 Delete immediately (dead or redundant, zero preconditions)

| File | Reason |
| --- | --- |
| `backend/api/v1/workspaces/` (whole tree, 10 `__init__.py`) | Empty placeholders superseded by `api/v1/{role}/` |
| `backend/api/v1/teacher_academy_actions.py` | **Deleted 2026-07-08** — split into `teacher_academy/schemas.py` and `teacher_academy/responses.py` |
| `backend/roles/head_of_department/academy_scope.py` | **Deleted 2026-07-08** — moved to `domains/teacher_academy/permissions.py` |
| `backend/roles/admin/services/teacher_academy_notifications.py` | **Deleted 2026-07-08** — moved to `domains/teacher_academy/notifications.py` |

### 3.2 Delete after retargeting imports (mechanical, same day)

> **STATUS 2026-07-07: DONE.** All files below plus `identity/teachers.py`,
> `identity/student_accounts.py`, `identity/passwords.py` were deleted; role and
> permission registries merged into `backend/security/`; password hashing
> centralized in `backend/core/security.py` (the only module that may import
> werkzeug hashing — stored hashes stay werkzeug-format). Remaining werkzeug
> use: `secure_filename` in `roles/admin/routes/student_routes.py`, which dies
> with that file in Phase 3.

| File | Precondition |
| --- | --- |
| `backend/identity/account_auth_v2.py` | 8-line `sys.modules` alias → import `identity.account_auth` directly |
| `backend/identity/account_telegram_auth_v2.py` | Same, → `identity.account_telegram_auth` |
| `backend/identity/profiles.py` | Re-export wrapper → import `domains.students.service` directly |
| `backend/identity/roles.py` | Merge `ROLE_DASHBOARD_PATHS` + display names into `security/roles.py`; reconcile the `owner` role discrepancy |
| `backend/identity/permissions.py` | Merge into `security/permissions.py` |
| `backend/identity/account_service.py` | Star-import facade over 6 modules (7 importers) → import the specific modules |
| `werkzeug` in `requirements.txt` | `identity/storage.py` switches to `core/security.py` hashing |

### 3.3 Delete per migrated slice (Phase 3, one PR each)

Each `roles/` route file is deleted when its routes have moved to `api/v1/{role}/` (JSON) and `pages/{role}.py` (HTML), with the frontend updated and `tests/route_snapshot.txt` regenerated.

| Old file(s) | Replaced by |
| --- | --- |
| `backend/roles/teacher/routes.py` | `pages/teacher.py` + `api/v1/teacher/` |
| `backend/roles/student/routes/` (9 files: student_page, dashboard, students, chat_page, chat_routes, comment_routes, resources, rating_board, office_hours_routes) | `pages/student.py` + `api/v1/student/{dashboard,chat,comments,resources,rating,office_hours}.py` |
| `backend/roles/parent/routes.py` | `pages/parent.py` (incl. token-authed invite pages) + `api/v1/parent/` |
| `backend/roles/admin/routes/` (12 files: admin_page, admins, student_routes, teacher_routes, payment_routes, academic_routes, resource_routes, chat_admin_routes, announcement_routes, complaint_routes, office_hours_routes, parent_routes) | `pages/admin.py` + `api/v1/admin/{admins,students,teachers,payments,academic,resources,chat,announcements,complaints,office_hours,parents}.py` |
| `backend/roles/admin/routes/request_payload.py` | Pydantic models — no replacement file |
| `backend/roles/ceo/routes.py`, `hr_manager/routes.py`, `customer_support/routes.py` | **Moved 2026-07-08** to `pages/{ceo,hr_manager,customer_support}.py`; old modules are compatibility re-exports |
| `backend/roles/academic_director/routes.py`, `head_of_department/routes.py` | `pages/{academic_director,head_of_department}.py` (their APIs are already in v1); drop the `/academic_director` underscore alias |
| `backend/routes/system.py` + `backend/routes/` package | manifest/sw.js → `pages/public.py`; router includes → `server.py` |
| `backend/domains/identity/routes.py` `register_user_auth_routes` closure | `pages/public.py` (login/telegram/logout pages) + `api/v1/auth/` |
| `database/queries/` (12 modules) + `database/cross_queries/` (3 modules) | SQL relocated into `domains/*/queries.py` as slices touch it. Verified: `tgbot/` has zero imports of these — web-side only |

Note: `roles/*/services/`, `workspace_cards.py`, and `staff_registration.py` are business logic, not transport — they move under `domains/` (or stay put temporarily) but are NOT deleted until importers and tests are migrated. HOD Teacher Academy scope has already moved and no longer depends on `backend.utils.context`.

### 3.4 Delete last — the Flask emulation layer (Phase 4 endgame)

Precondition: `grep -r "from backend.utils.context import" backend/` returns zero.

| File | Replaced by |
| --- | --- |
| `backend/utils/context.py` (`request`/`session` proxies, `RequestContextMiddleware`) | FastAPI native `Request`, `Form()`, Pydantic bodies. Also permanently retires the body-pre-consumption hang bug |
| `backend/utils/response_helpers.py` (`jsonify`, `redirect`, `with_status`) | `api_success`/`api_error`, `RedirectResponse` |
| `backend/utils/guards.py` (`GuardResponse`, `install_guard_handler`) | `security/dependencies.py` raising `HTTPException` |
| `backend/roles/` package remnants | empty by then |

---

## 4. CREATE inventory

| New file | Contents |
| --- | --- |
| `backend/security/dependencies.py` (extend existing) | `CurrentUser` dataclass (login, role, teacher_id, student_id, admin_id — resolved once from session); `get_current_user`; `require_role(*roles)`; `require_permission(perm)` — moved from `utils/guards.py`, raising `HTTPException` |
| `backend/core/db.py` | `get_db()` dependency wrapping `connect_auth_db()` so services receive connections |
| `backend/core/assets.py` | `ASSET_VERSION` + `STATIC_DIR` computed at import (replaces `_build_default_asset_version` + bootstrap monkey-patching of `render`/`system_routes` globals) |
| `backend/pages/__init__.py` + `public.py` + 9 role modules | HTML shell routes ported from `roles/*/routes*.py`; module-level `APIRouter(dependencies=[Depends(require_role(...))])` |
| `backend/api/v1/{role}/schemas.py` (per role, as slices land) | Pydantic request/response models |
| `backend/api/v1/admin/{admins,students,teachers,payments,academic,resources,chat,announcements,complaints,office_hours,parents}.py` | The 68 admin routes split by panel, aggregated by the existing `api/v1/admin/router.py` |
| `backend/api/v1/student/{dashboard,chat,comments,resources,rating,office_hours}.py` | The bare `/api/*` student cluster |
| `backend/api/v1/teacher/office_hours.py` (first teacher slice) | `/teacher/api/office-hours/*` |
| `docs/API_FOUNDATION.md` (update) | The mandatory route standard (§5) so future slices — human or Codex — follow it |

---

## 5. The route standard (mandatory for every new/migrated endpoint)

```python
# api/v1/<role>/<panel>.py
router = APIRouter()  # included by api/v1/<role>/router.py with prefix + require_role

@router.post("/head-of-departments", response_model=ApiSuccess[HodCreated])
def create_hod(
    hod_display_name: Annotated[str, Form()],
    hod_subject_id: Annotated[str, Form()],
    user: CurrentUser = Depends(get_current_user),
):
    created, error, creds = create_head_of_department_account(
        display_name=hod_display_name,
        subject_id=hod_subject_id,
        created_by=user.login,
    )
    if not created:
        raise HTTPException(400, error or "Unable to create Head of Department.")
    return api_success(HodCreated(**creds))
```

Rules:

1. Inputs declared as `Form()`/`Query()`/Pydantic body — never the `request` proxy, never `request_payload`.
2. Output is `ApiSuccess[...]` via `api_success()` with `response_model=` — never `jsonify`, never `{"ok": ...}`.
3. Errors raise `HTTPException` — the global handlers render JSON-or-redirect.
4. Auth via `require_role` on the router + `CurrentUser` dependency — never `current_auth_*()` calls inside handlers.
5. No SQL in route modules — call `domains/*/service.py`; SQL lives in `domains/*/queries.py`.
6. No blanket `except Exception` returning silent defaults — let the global handler log it.

Middleware contract after cleanup: `AuthAndSecurityMiddleware` keeps security headers, cache-control, same-origin/CSRF check, and the coarse "valid session exists" gate. Fine-grained role checks live ONLY in router dependencies. The `/teacher/*` public exemption in `server.py` is removed.

Frontend contract: canonical URLs live only in `frontend/src/shared/api/routes.ts`; the shared `api.ts` adapts once to the `{status, data}` envelope. Run `npm run build` in `frontend/` after every slice.

---

## 6. Execution order

| Phase | Work | Risk | Exit criterion |
| --- | --- | --- | --- |
| 0 | Inventory and document registered routes/imports | Done for 2026-07-08 baseline | `docs/API_MIGRATION_STATUS.md` lists counts, legacy namespaces, route-file blockers |
| 1 | Teacher Academy cleanup: schemas/responses split, HOD permissions, notifications, scoped responses | Done for current slice | domain permissions have no `backend.utils.context`; responses `__all__` exposes adapters only |
| 2 | Move page shells from `roles/` into `pages/`, preserving URLs | Low/medium | page routes load and old role route modules are compatibility re-exports or deleted after imports are zero |
| 3 | Complete student and teacher API/page split | Medium, bounded per role | JSON routes live under `/api/v1/{student,teacher}` and page shells live in `pages/` |
| 4 | Parent, AD, and HOD page/API finalization | Medium | invite/link flows and HOD subject scope stay covered by tests |
| 5 | Admin panel-by-panel migration | Highest, bounded per panel | each admin panel has v1 routes, schemas, domain service/query ownership, and frontend route constants |
| 6 | Database wrapper removal and Flask-layer deletion | Low by then | legacy import greps in §7 are zero |
| 7 | Slim `server.py` to composition-only; `core/assets.py` replaces monkey-patching | Low | `server.py` contains app creation, middleware, exception handlers, static mount, and router includes only |

## 7. Definition of done (verifiable)

```bash
grep -r "from backend.utils.context import" backend/   # 0 hits
grep -rn "jsonify("        backend/ --include="*.py"   # 0 hits
grep -rn "request_payload" backend/ --include="*.py"   # 0 hits
grep -rn "GuardResponse"   backend/ --include="*.py"   # 0 hits
grep -rn "connect_auth_db" backend/pages backend/api   # 0 hits (SQL only in domains/)
```

- `tests/route_snapshot.txt` contains only page URLs and `/api/v1/*`.
- `/docs` (OpenAPI) shows typed request/response schemas for every JSON endpoint.
- One role registry, one permission map, one `require_role`, one envelope.
