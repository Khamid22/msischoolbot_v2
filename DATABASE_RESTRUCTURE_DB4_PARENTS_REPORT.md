# Database Restructure DB-4: Parents

## Scope

Moved parent-related DB access and workflows into the parent domain without changing the physical database schema. The current schema remains `msi_v2`; this phase only changes code ownership and import surfaces.

## New Domain Files

- `backend/domains/parents/__init__.py`
- `backend/domains/parents/queries.py`
- `backend/domains/parents/service.py`

## Moved Query Functions

Parent account/profile and Telegram lookup:

- `link_parent_from_invite`
- `get_parent_by_telegram_id`
- `clear_parent_telegram_user_conflicts`
- `get_parents_for_student`

Parent-child link and dashboard access:

- `get_parent_child_link`
- `get_parent_child_link_by_dashboard_id`
- `get_parent_child_row`
- `list_parent_client_child_rows`
- `list_invite_parent_rows`
- `insert_parent_student_link`
- `delete_parent_student_link`
- `count_parent_child_links`

Parent invite/code helpers:

- `get_student_v2_id_by_legacy_row`
- `get_staff_db_id_for_admin_id`
- `insert_parent_invite_row`
- `get_pending_parent_invite_token`

Linked child dashboard/card data:

- `list_parent_subject_indicator_rows`
- `list_parent_recent_lesson_rows`

Parent delete safety checks:

- `get_parent_exists_row`
- `count_parent_support_tickets`
- `count_parent_ticket_messages`
- `delete_parent_row`

## Moved Service Functions

Parent invite and Telegram linking:

- `create_parent_invite_token`
- `load_parent_invite_payload`
- `create_parent_invite_code`
- `get_parent_invite_token`
- `load_parent_invite_code_payload`
- `link_parent_via_invite`
- `parent_from_telegram_user_id`

Parent workspace/admin workflows:

- `parent_children`
- `list_parent_client_children`
- `list_parent_accounts`
- `list_parent_children`
- `list_linked_parents_for_student`
- `assign_parent_child`
- `remove_parent_child`
- `delete_parent_account`
- `parent_can_access_student`
- `parent_can_access_dashboard`
- `resolve_parent_child_dashboard`

## Compatibility Wrappers Kept

The following files now re-export parent-domain functions temporarily:

- `database/queries/parent_account_queries.py`
- `database/queries/parent_queries.py`
- `backend/identity/parent_accounts.py`
- `backend/identity/parent_invites.py`
- `backend/roles/admin/services/parent_service.py`
- `backend/roles/parent/services.py`

These wrappers preserve old imports during the migration and no longer contain parent SQL.

## Imports Updated

Direct parent-domain imports are now used in:

- `backend/domains/identity/routes.py`
- `backend/identity/telegram_links.py`
- `backend/roles/admin/routes/admin_page.py`
- `backend/roles/admin/routes/parent_routes.py`
- `backend/roles/admin/routes/student_routes.py`
- `backend/roles/admin/services/page_service.py`
- `backend/roles/parent/routes.py`
- `backend/roles/student/services/payload_service.py`

## Remaining Compatibility References

Old parent modules remain intentionally as wrappers for the next cleanup phase. They are not deleted yet because other code, tests, or external imports may still depend on those import paths.

The generic `database.queries` package still exposes parent functions through the wrappers. This is intentional until the broader database query barrel is retired.

## Verification

Focused parent/login/dashboard slice:

- `python3 -m pytest tests/test_database_restructure_db4_parents.py tests/test_database_restructure_db3_students.py tests/test_phase2a_parent_workspace_cards.py tests/test_identity_telegram_routes.py tests/test_identity_account_telegram_auth.py tests/test_phase2a_student_dashboard_safety.py`
- Result: `69 passed, 4 warnings`

Full suite:

- `python3 -m pytest`
- Result: `328 passed, 11 warnings`

Frontend:

- `npm --prefix frontend run check-types`
- Result: passed

- `npm --prefix frontend run build`
- Result: passed

Diff hygiene:

- `git diff --check`
- Result: passed

## Risk Notes

- No database schema was changed.
- Parent invite token semantics were kept unchanged.
- Telegram parent linking still uses the verified Telegram user id and existing session setup.
- Student dashboard resolution still delegates to the student domain.
- Shared payment and student/admin Telegram conflict helpers remain in their existing owners for now; only parent-owned DB access moved in DB-4.
