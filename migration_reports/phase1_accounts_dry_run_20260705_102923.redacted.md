# Phase 1 Accounts Dry-Run Report (Redacted)

- Source report: `phase1_accounts_dry_run_20260705_102923.md`
- Mode: `dry_run`
- Redaction scope: counts only; no names, source IDs, Telegram IDs, phone numbers, row-level grades, or private contact details.
- Alembic status: not applied.
- Migration apply status: `--apply` not run.

## Planned Accounts

| Metric | Count |
|---|---:|
| Total planned accounts | 185 |
| Planned Telegram links | 1 |

## Planned Accounts By Role

| Role | Count |
|---|---:|
| parent | 4 |
| student | 177 |
| system_admin | 1 |
| teacher | 3 |

## Validation Counts

| Validation | Count |
|---|---:|
| duplicate_logins | 0 |
| missing_password_hash | 31 |
| students_without_auth | 31 |
| teachers_without_staff_rows | 0 |
| parents_without_telegram | 4 |
| duplicate_telegram_ids | 0 |
| invalid_roles | 0 |
| disabled_or_inactive_users | 31 |
| teacher_code_conflicts | 0 |
| student_code_conflicts | 0 |

## Teacher Code Mapping Summary

| Metric | Count |
|---|---:|
| Total teacher mappings | 3 |
| Generated TCH codes | 3 |
| Kept existing TCH codes | 0 |
| Generated due to TCH conflict | 0 |

## Safety Notes

- Dry-run mode did not write to PostgreSQL.
- The original private report should not be committed because it includes source-level mapping details.
- Full database backup still needs a PostgreSQL 18-compatible backup method before any future `--apply`.
