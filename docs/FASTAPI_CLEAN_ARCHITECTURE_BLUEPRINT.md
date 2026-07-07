# FastAPI Clean Architecture Blueprint

Date: 2026-07-07
Scope: backend only. Diagnosis of the current state plus the complete file-level inventory — what to delete, what to create, what to rewrite — to reach the conventional FastAPI layout (routers → dependencies → services → queries, Pydantic contracts, one URL scheme, one envelope).

Status baseline: branch `FastAPI-Run-System`, after the 2026-07-07 API v1 first slice (AD/HOD Teacher Academy actions moved to `/api/v1`).

---

## 1. Diagnosis (current state)

| Area | State |
| --- | --- |
| Route decorators total | 131 |
| Legacy closure-registered routes in `backend/roles/` | ~113 (`/admin/api/*` 68, bare `/api/*` 16, `/teacher/api/*`, page routes) |
| Clean `/api/v1/*` routes | 12 (auth/me, system/status, 10 Teacher Academy actions) |
| Pydantic request models | 0 endpoints (`request_payload` manual parsing: 37 call sites) |
| `response_model` usage | 2 files (`api/v1/auth`, `api/v1/system`) |
| Response envelopes in production | 3 (`{"ok"}`, `{"status","data"}`, bare `{"message"}`) |
| Role registries / permission maps | 2 of each (`identity/` vs `security/`) |
| Direct DB connections inside `backend/roles/` | 33 (SQL belongs in `domains/*/queries.py`) |
| Flask emulation layer | `utils/context.py` proxies + `RequestContextMiddleware` body pre-consumption + `jsonify`/`redirect` shims |

Root problem: the codebase runs Flask idioms on FastAPI. The `/api/v1` skeleton is now real, but its first 10 routes copied the Flask idioms (global `request` proxy, `jsonify`, `{"ok"}` envelope), so the pattern must be corrected **before** the remaining ~120 routes migrate.

What is already correct and must NOT change:

- `backend/domains/*` — service.py + queries.py split. This is the strongest layer; every migrated route plugs into it unchanged.
- `backend/api/schemas.py` + `backend/api/responses.py` — the `ApiSuccess`/`ApiError` envelope (exists, underused).
- `backend/api/v1/router.py` per-role aggregation under `/api/v1` (Codex, 2026-07-07).
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
| `backend/roles/common/teacher_academy_api.py` | Dead code — zero imports since the v1 slice superseded it |

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
| `backend/roles/ceo/routes.py`, `hr_manager/routes.py`, `customer_support/routes.py` | `pages/{ceo,hr_manager,customer_support}.py` (page-only roles) |
| `backend/roles/academic_director/routes.py`, `head_of_department/routes.py` | `pages/{academic_director,head_of_department}.py` (their APIs are already in v1); drop the `/academic_director` underscore alias |
| `backend/routes/system.py` + `backend/routes/` package | manifest/sw.js → `pages/public.py`; router includes → `server.py` |
| `backend/domains/identity/routes.py` `register_user_auth_routes` closure | `pages/public.py` (login/telegram/logout pages) + `api/v1/auth/` |
| `database/queries/` (12 modules) + `database/cross_queries/` (3 modules) | SQL relocated into `domains/*/queries.py` as slices touch it. Verified: `tgbot/` has zero imports of these — web-side only |

Note: `roles/*/services/`, `workspace_cards.py`, `academy_scope.py`, `staff_registration.py` are business logic, not transport — they move under `domains/` (or stay put) but are NOT deleted.

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
| 0 | Retrofit the 10 existing v1 routes (AD/HOD) to §5; update `docs/API_FOUNDATION.md` | Low — one frontend module consumes them | v1 tree contains zero `jsonify`/proxy uses |
| 1 | §3.1 + §3.2 deletions; registry merge; drop werkzeug | Zero | one `roles.py`, one `permissions.py`; wrappers gone |
| 2 | `CurrentUser` + `require_role` in `security/dependencies.py`; unify exception-handler envelope; slim middleware | Low | one auth dependency system |
| 3 | Slice migrations: teacher office-hours → student `/api/*` → parent → admin (last, split by panel); per slice: port, Pydantic, frontend URLs, `npm run build`, delete old routes, regen snapshot | Medium, bounded per PR | `route_snapshot.txt` = pages + `/api/v1/*` only |
| 4 | Delete Flask layer (§3.4); `pages/` fully owns HTML routes | Low by then | greps in §7 all zero |
| 5 | Slim `server.py` to composition-only; `core/assets.py` replaces monkey-patching | Low | `server.py` ≈ 100 lines |

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
