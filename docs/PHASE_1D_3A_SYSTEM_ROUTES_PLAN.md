# Phase 1D-3A System Routes Move Plan

Date: 2026-07-05  
Project: MSI LMS Portal  
Branch: FastAPI-Run-System

This is a planning document only. Do not move files, change route behavior, delete legacy files, change auth logic, or change frontend code in this phase.

## Goal

Move the behavior currently owned by `backend/routes/system.py` into the future `backend/api/v1` structure while keeping all current routes, imports, response shapes, and route registrations compatible.

## 1. Current Routes In `backend/routes/system.py`

Current module: `backend/routes/system.py`

Routes:

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| `GET` | `/manifest.webmanifest` | Serves the PWA manifest from the static folder | Uses module-level `STATIC_FOLDER` set during app bootstrap |
| `GET` | `/sw.js` | Serves the service worker file from the static folder | Uses module-level `STATIC_FOLDER` set during app bootstrap |
| `GET` | `/api/v1/system/status` | API health/status response | Response model: `ApiMessage`, tag: `system` |
| `GET` | `/api/v1/auth/me` | Current authenticated user metadata and permissions | Response model: `ApiSuccess`, tag: `identity` |

Current `/api/v1/auth/me` response data shape:

```json
{
  "login": "current auth login",
  "role": "current resolved role",
  "permissions": {
    "permission_name": true
  }
}
```

The exact outer `api_success(...)` envelope must stay unchanged.

## 2. Current Import And Registration Path

Current app bootstrap flow in `backend/server.py`:

1. Imports `backend.routes.system as system_routes`.
2. Assigns `system_routes.STATIC_FOLDER = _STATIC_DIR`.
3. Imports `router` from `backend.routes.system`.
4. Calls `app_instance.include_router(system_router)`.

Current dependency imports used by `backend/routes/system.py`:

- `fastapi.APIRouter`
- `fastapi.Depends`
- `fastapi.responses.FileResponse`
- `backend.security.get_current_user_role`
- `backend.security.role_has_permission`
- `backend.security.permissions.ALL_PERMISSIONS`
- `backend.api.api_success`
- `backend.api.api_message`
- `backend.api.ApiMessage`
- `backend.api.ApiSuccess`
- `backend.utils.session`

Current route registration tests already cover:

- app starts through `backend.server:create_app`
- `GET /api/v1/auth/me` is registered
- route snapshot includes `/api/v1/auth/me`
- route snapshot includes `/api/v1/system/status`

## 3. Target Location

Target structure for the moved runtime code:

```text
backend/
  api/
    v1/
      auth/
        routes.py
      system/
        routes.py
```

Recommended ownership:

| Current behavior | Target file | Reason |
| --- | --- | --- |
| `/api/v1/auth/me` | `backend/api/v1/auth/routes.py` | Auth/session metadata belongs to the auth API namespace |
| `/api/v1/system/status` | `backend/api/v1/system/routes.py` | System status belongs to the system API namespace |
| `/manifest.webmanifest` | `backend/api/v1/system/routes.py` or temporary wrapper | It is system/static infrastructure, but it is not an `/api/v1` path |
| `/sw.js` | `backend/api/v1/system/routes.py` or temporary wrapper | It is system/static infrastructure, but it is not an `/api/v1` path |

Preferred implementation target:

- Put API endpoints in `backend/api/v1/auth/routes.py` and `backend/api/v1/system/routes.py`.
- Keep PWA static routes either in `backend/api/v1/system/routes.py` with explicit static-folder configuration, or keep them in the compatibility wrapper for one step if that is safer.

## 4. Compatibility Wrapper Strategy

Keep `backend/routes/system.py` in place temporarily.

The wrapper should continue to export:

- `router`
- `STATIC_FOLDER`, or an equivalent compatibility path for `backend/server.py`

Safe wrapper strategy:

1. Create the new routers under `backend/api/v1/auth/routes.py` and `backend/api/v1/system/routes.py`.
2. Keep `backend/routes/system.py` as the old import path.
3. Have `backend/routes/system.py` compose and export a router that includes the new routers.
4. Preserve route paths exactly. Do not add prefixes unless the paths inside the new routers are adjusted to produce the same final paths.
5. Preserve the `STATIC_FOLDER` bootstrap behavior.

Static folder compatibility options:

- Option A: Update `backend/server.py` during implementation to configure the new system route module directly while still importing the old wrapper. This is explicit and easy to test.
- Option B: Keep `/manifest.webmanifest` and `/sw.js` in `backend/routes/system.py` temporarily, and move only `/api/v1/system/status` and `/api/v1/auth/me` first.

Recommended first implementation:

- Use Option B for the first route move to reduce static file risk.
- Move `/api/v1/auth/me` and `/api/v1/system/status` into new API modules.
- Leave root static PWA routes in `backend/routes/system.py` until a later static-assets phase.

## 5. Tests Needed Before And After

Before moving:

- Confirm app starts through `backend.server:create_app`.
- Confirm route snapshot includes all four current paths.
- Confirm `/api/v1/auth/me` response shape with an authenticated session.
- Confirm `/api/v1/system/status` response shape and message are unchanged.

After moving:

- App starts:
  - `backend.server:create_app` returns a `FastAPI` app.
  - App title remains unchanged.
- Route registration:
  - `GET /manifest.webmanifest`
  - `GET /sw.js`
  - `GET /api/v1/system/status`
  - `GET /api/v1/auth/me`
- `/api/v1/auth/me` response shape unchanged:
  - outer API success envelope unchanged
  - `login` key unchanged
  - `role` key unchanged
  - `permissions` key unchanged
- System/status routes unchanged:
  - status code unchanged
  - response model/envelope unchanged
  - current message unchanged unless separately approved
- Compatibility:
  - `from backend.routes.system import router` still works
  - `import backend.routes.system as system_routes` still works
  - `system_routes.STATIC_FOLDER = _STATIC_DIR` still supports existing static routes

## 6. Risks

- `STATIC_FOLDER` is assigned directly on `backend.routes.system` during app bootstrap; moving the static routes without a forwarding strategy can break `/manifest.webmanifest` and `/sw.js`.
- Accidentally registering both old and new routers can create duplicate route definitions.
- Adding prefixes incorrectly can change paths from `/api/v1/auth/me` to something like `/api/v1/api/v1/auth/me`.
- `/api/v1/auth/me` depends on current session helper behavior; moving it must not change dependency resolution or permission calculation.
- `backend.routes.system` may be used by tests or external deployment scripts as a stable import path.
- Route snapshot tests may need to be updated only if the route list ordering changes; paths and methods should not change.
- The current status text still says `MSI School Backend API`; changing wording should be a separate product/docs decision, not part of this move.

## 7. Exact Implementation Steps

Do not perform these steps until implementation is explicitly approved.

1. Add pre-move tests if missing:
   - route registration for all four current paths
   - `/api/v1/auth/me` response shape
   - `/api/v1/system/status` response shape
   - old import path compatibility
2. Create `backend/api/v1/auth/routes.py`.
3. Move only the `/api/v1/auth/me` handler logic into `backend/api/v1/auth/routes.py`.
4. Create `backend/api/v1/system/routes.py`.
5. Move only the `/api/v1/system/status` handler logic into `backend/api/v1/system/routes.py`.
6. Keep `/manifest.webmanifest` and `/sw.js` in `backend/routes/system.py` for the first implementation pass.
7. Update `backend/routes/system.py` to import/include the new auth and system API routers while preserving its exported `router`.
8. Do not change `backend/server.py` unless needed for router composition.
9. Run focused tests:
   - structure safety tests
   - route snapshot test
   - any auth/me tests
10. Run full test suite:
    - `python3 -m pytest`
11. Review `git diff` to confirm:
    - no route paths changed
    - no auth logic changed
    - no frontend changed
    - no database logic changed

## Acceptance Criteria

- `backend/routes/system.py` remains import-compatible.
- All current paths remain registered.
- `/api/v1/auth/me` response shape is unchanged.
- `/api/v1/system/status` behavior is unchanged.
- PWA static routes still work.
- Full pytest passes.
- No frontend, database, auth cutover, or dashboard behavior changes are included.
