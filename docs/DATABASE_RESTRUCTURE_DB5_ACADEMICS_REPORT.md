# Database Restructure DB-5: Academics, Timetable, Announcements

## Scope

Moved academic operational SQL into domain query modules without changing the physical database schema. The database schema remains `msi_v2`.

## New/Updated Query Modules

- `backend/domains/academics/queries.py`
- `backend/domains/timetable/queries.py`
- `backend/domains/announcements/queries.py`

## Moved Academic Query Access

Academic operational reads and writes now live in `backend/domains/academics/queries.py`:

- schools
- subjects
- subject programs
- subject program items
- groups
- group enrollments
- lesson catalog rows
- internal dashboard overview rows
- enrollment dashboard rows
- student creation/enrollment helper queries
- legacy id minting helper

`backend/domains/academics/postgres_service.py` now keeps workflow and return-shape logic. It no longer embeds runtime `msi_v2` SQL.

`backend/domains/academics/internal_dashboard_service.py` now keeps dashboard payload shaping and chart filtering. It no longer embeds runtime `msi_v2` SQL.

## Moved Timetable Query Access

Timetable SQL now lives in `backend/domains/timetable/queries.py`:

- schedule rule listing
- lesson session listing
- schedule conflict checks
- schedule rule insert
- generated lesson session insert

Academic Director and HOD timetable pages continue to receive the same schedule/session payloads, including Teacher Academy lesson events from the existing Teacher Academy domain service.

## Moved Announcement Query Access

Announcement SQL now lives in `backend/domains/announcements/queries.py`:

- schema ensure helper
- list rows
- insert row
- get row
- update row
- delete row

`database/queries/announcement_queries.py` is now a compatibility wrapper.

## Compatibility Wrappers Kept

- `database/queries/announcement_queries.py`

Existing imports of `database.queries.ensure_announcements_schema` still work through the query barrel while callers migrate.

## Frontend Legacy UI Audit

See `FRONTEND_LEGACY_UI_DELETION_REPORT.md`.

No frontend components were deleted because the legacy-looking candidates are still active route entrypoints or admin/system-admin UI.

## Fresh Architecture Docs

- `CURRENT_ARCHITECTURE.md`
- `SCHEMA_RENAME_MSI_V2_TO_LMS_PLAN.md`
- `README.md` updated to current paths and commands.
- `docs/PHASE_*` planning docs moved to `docs/archive/`.

## Focused Verification

Command:

```bash
python3 -m pytest tests/test_database_restructure_db5_academics.py tests/test_academic_dashboard_bugfixes.py tests/test_academic_director_sidebar_ui.py tests/test_phase2a_system_admin_workspace_cards.py
```

Result: `41 passed, 1 warning`

## Risk Notes

- No database schema was changed.
- No `msi_v2` rename was attempted.
- Existing payload shapes were preserved.
- Domain service behavior was not rewritten; query ownership moved underneath it.
