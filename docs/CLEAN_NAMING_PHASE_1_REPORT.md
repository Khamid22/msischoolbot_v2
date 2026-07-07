# Clean Naming Phase 1 Report

Date: 2026-07-07

Scope: code-level Account Authentication naming only. The physical PostgreSQL schema remains `msi_v2`; no database schema or data migration was performed.

## Files Renamed

| Previous path | New implementation path | Notes |
| --- | --- | --- |
| `backend/identity/account_auth_v2.py` | `backend/identity/account_auth.py` | Password account authentication implementation now lives in the clean module. |
| `backend/identity/account_telegram_auth_v2.py` | `backend/identity/account_telegram_auth.py` | Telegram account authentication implementation now lives in the clean module. |
| `tests/test_phase1c_account_auth_v2.py` | `tests/test_identity_account_auth.py` | Tests now use identity/account auth naming. |
| `tests/test_phase1c_account_telegram_auth_v2.py` | `tests/test_identity_account_telegram_auth.py` | Tests now use identity/account Telegram auth naming. |
| `tests/test_phase1c_login_auth_v2.py` | `tests/test_identity_login.py` | Login tests now use identity naming. |
| `tests/test_phase1c_telegram_auth_v2_routes.py` | `tests/test_identity_telegram_routes.py` | Telegram route tests now use identity naming. |

## Wrappers Kept

The old import paths remain temporarily as compatibility wrappers:

- `backend/identity/account_auth_v2.py`
- `backend/identity/account_telegram_auth_v2.py`

Both wrappers alias the clean implementation modules through `sys.modules`, so old imports continue to receive the same module object as the new import path.

## Imports Updated

Updated safe runtime imports:

- `backend/domains/identity/routes.py`
  - `backend.identity.account_auth_v2` -> `backend.identity.account_auth`
  - `backend.identity.account_telegram_auth_v2` -> `backend.identity.account_telegram_auth`

Updated helper names in `backend/domains/identity/routes.py`:

- `set_account_auth_v2_session` -> `set_account_session`
- `account_auth_v2_redirect_url` -> `account_redirect_url`
- `account_auth_v2_response_role` -> `account_response_role`
- `record_account_auth_v2_student_activity` -> `record_account_student_activity`

Updated tests to import the clean modules by default. Compatibility is covered by explicit wrapper tests:

- `tests/test_identity_account_auth.py::test_previous_account_auth_import_path_still_works`
- `tests/test_identity_account_telegram_auth.py::test_previous_account_telegram_auth_import_path_still_works`

## Docs Updated

Visible migration-era auth wording was replaced with `Account Authentication` in docs and reports touched by this phase. Historical audit references to old wrapper file names remain where they describe the compatibility paths.

## Remaining v2 References and Why

| Remaining reference | Why it remains |
| --- | --- |
| `backend/identity/account_auth_v2.py` | Temporary compatibility wrapper requested for old imports. |
| `backend/identity/account_telegram_auth_v2.py` | Temporary compatibility wrapper requested for old imports. |
| Wrapper import tests | Prove old import paths still work during transition. |
| `msi_v2` SQL/schema references | Physical database schema rename is explicitly out of scope. |
| Historical audit/planning docs | Preserve migration history and explain why wrappers remain until the next cleanup phase. |

## Tests

Required verification:

```bash
python3 -m pytest
npm --prefix frontend run check-types
npm --prefix frontend run build
git diff --check
```

Targeted identity verification already covered:

```bash
python3 -m pytest tests/test_identity_account_auth.py tests/test_identity_account_telegram_auth.py tests/test_identity_login.py tests/test_identity_telegram_routes.py tests/test_phase1d_core_config.py tests/test_phase1d_core_security.py tests/test_phase1d_structure_safety.py
```

Result: passed, `62 passed`.
