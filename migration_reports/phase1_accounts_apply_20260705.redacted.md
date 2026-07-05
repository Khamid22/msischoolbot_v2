# Phase 1 Accounts Apply Report (Redacted)

- Scope: Phase 1 shared accounts identity migration on confirmed local/dev database.
- Redaction scope: counts only; no names, source IDs, Telegram IDs, phone numbers, raw student data, or private migration rows.
- Auth cutover: not performed.
- Account auth v2: not enabled.
- Legacy auth/session tables: not deleted.

## Row Counts

| Table | Count |
|---|---:|
| accounts | 185 |
| student_profiles | 177 |
| teacher_profiles | 3 |
| parent_profiles | 4 |
| staff_profiles | 1 |
| account_telegram_links | 1 |

## Role Counts

| Role | Count |
|---|---:|
| parent | 4 |
| student | 177 |
| system_admin | 1 |
| teacher | 3 |

## Status Counts

| Role | Status | Count |
|---|---|---:|
| parent | pending | 4 |
| student | active | 146 |
| student | disabled | 31 |
| system_admin | active | 1 |
| teacher | active | 3 |

## Uniqueness Checks

| Check | Duplicate Groups |
|---|---:|
| accounts.login | 0 |
| account_telegram_links.telegram_user_id | 0 |
| student_profiles.student_code | 0 |
| teacher_profiles.teacher_code | 0 |
| accounts legacy source mappings | 0 |

## Teacher Mapping Summary

| Metric | Count |
|---|---:|
| Teacher mappings generated | 3 |
| Existing TCH codes kept | 0 |
| TCH conflict remaps | 0 |

## Idempotency Result

| Apply Run | Result |
|---|---|
| First `--apply` | 185 accounts created, 185 profiles created, 1 Telegram link created |
| Second `--apply` | 185 accounts updated, 185 profiles updated, 1 Telegram link updated |
| Row count increase on second apply | 0 |

## Tests

| Command | Result |
|---|---|
| `python3 -m pytest tests/test_phase1_accounts_foundation.py tests/test_role_routing.py` | 27 passed, 1 warning |
