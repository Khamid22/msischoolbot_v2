# Identity Naming Cleanup Report

Date: 2026-07-07

Scope: identity naming status during the architecture migration. No auth behavior was changed in this pass.

## Files Renamed Earlier

- `backend/identity/account_auth.py` is the clean password/account authentication implementation.
- `backend/identity/account_telegram_auth.py` is the clean Telegram account authentication implementation.

## Wrappers Kept

- `backend/identity/account_auth_v2.py`
- `backend/identity/account_telegram_auth_v2.py`

These compatibility wrappers remain by design so old imports keep working while runtime imports migrate gradually.

## Imports Updated In This Pass

None. This pass intentionally avoided auth changes.

## Remaining v2 References And Why

| Reference | Why it remains |
| --- | --- |
| `account_auth_v2.py` | Temporary compatibility wrapper. |
| `account_telegram_auth_v2.py` | Temporary compatibility wrapper. |
| `msi_v2` | Physical PostgreSQL schema; schema rename is explicitly out of scope. |
| Historical docs/tests | Preserve migration history and wrapper coverage. |

## Safety Note

The existing auth routes, password login, Telegram auth import path, sessions, and role redirects were left unchanged.
