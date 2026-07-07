# Frontend Legacy UI Deletion Report

## Scope

Audited legacy-looking frontend UI after the shared role shell and modal system migration. No files were deleted in this pass because the candidates are still active imports or route entrypoints.

## Kept Components

| Component/file | Current purpose | Proof | Recommendation |
| --- | --- | --- | --- |
| `frontend/src/roles/common/components/AcademicDirectorShell.tsx` | Shared Academic Director and HOD role shell wrappers. | Imported by `RoleHome`, `AcademicDepartmentWorkspace`, AD Teacher Academy, AD HOD page, and HOD Teacher Academy. | KEEP_FOR_NOW. |
| `frontend/src/roles/admin/pages/Admin.tsx::AdminSidebar` | Active `/admin` sidebar for system/admin workspace. | Rendered inside `Admin.tsx`; `/admin` still maps to this page. | KEEP_FOR_NOW. |
| `frontend/src/roles/admin/panels/teachers/*Modal.tsx` | Active admin teacher/candidate modals. | Imported and rendered by `TeachersPanel.tsx`. | KEEP_FOR_NOW. |
| `frontend/src/shared/ui/Modal.tsx` and `ActionMenu.tsx` | Shared modal/bottom-sheet and action menu system. | Imported by Teacher Academy, Announcements, Parents, and shared UI tests. | KEEP. |
| `frontend/src/roles/academic_director/pages/*` | AD workspace entrypoints. | Lazy-loaded by `frontend/src/app/App.tsx`. | KEEP. |
| `frontend/src/roles/head_of_department/pages/TeacherAcademy.tsx` | HOD Teacher Academy entrypoint. | Lazy-loaded by `frontend/src/app/App.tsx`. | KEEP. |

## Search Results

- `AdminSidebar`: active only inside real admin workspace; not leaking into AD/HOD page sources.
- `AcademicDirectorShell`: active shared role shell.
- Old teacher modal names: active in admin teacher panel.
- `Training tab`, `Training path`, `Training lessons`, `Training timetable`: no user-facing active label found in role navigation; remaining occurrences are tests/data keys or admin teacher legacy internals.
- `Assign` labels: remaining active uses are admin teacher/group assignment workflows or non-Teacher-Academy status labels. Teacher Academy action flow continues to use `Schedule`/`Assess`.
- `Announc...`: no hardcoded truncated label found.

## Deleted Files

None.

## Risk Notes

Deleting any candidate found in this pass would break at least one active route or admin/system-admin workflow. A later deletion pass can remove files only after their route map imports and admin panel imports are replaced.
