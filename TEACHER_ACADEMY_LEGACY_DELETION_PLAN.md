# Teacher Academy Legacy Deletion Plan

## 1. Old Admin Routes Still Remaining

The following compatibility routes remain in `backend/roles/admin/routes/teacher_routes.py`:

- `POST /admin/teacher-academy`
- `POST /admin/teacher-academy/assignments/{assignment_id}`
- `POST /admin/teacher-academy/{academy_teacher_id}/assessments`
- `POST /admin/teacher-academy/{academy_teacher_id}/status`
- `POST /admin/teacher-academy/{academy_teacher_id}/promote`

They are retained for admin/system-admin compatibility. Academic Director and Head of Department workspaces now have clean role-owned API routes.

## 2. Old Admin Service Wrapper Still Remaining

`backend/roles/admin/services/teacher_academy_service.py` remains as a compatibility import path.

It aliases to:

- `backend.domains.teacher_academy.service`

This wrapper is still needed because existing tests and admin compatibility routes import the old path.

## 3. Frontend References To `/admin/teacher-academy`

Remaining valid frontend references:

- `frontend/src/shared/lib/routes.ts`
  - `adminTeacherAcademyCreate`
  - `adminTeacherAcademyAssignment`
  - `adminTeacherAcademyAssessment`
  - `adminTeacherAcademyStatus`
  - `adminTeacherAcademyPromote`
- `frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx`
  - admin-mode fallback inside `teacherAcademyActionRoutes`

Academic Director mode uses:

- `/academic-director/api/teacher-academy`
- `/academic-director/api/teacher-academy/assignments/{assignment_id}`
- `/academic-director/api/teacher-academy/{academy_teacher_id}/assessments`
- `/academic-director/api/teacher-academy/{academy_teacher_id}/status`
- `/academic-director/api/teacher-academy/{academy_teacher_id}/promote`

Head of Department mode uses:

- `/head-of-department/api/teacher-academy/assignments/{assignment_id}`
- `/head-of-department/api/teacher-academy/{academy_teacher_id}/assessments`
- `/head-of-department/api/teacher-academy/{academy_teacher_id}/status`

## 4. Valid Admin Compatibility References

Keep for now:

- Admin/system-admin Teacher Academy panel fallback in `TeacherAcademyPanel.tsx`
- Admin route helpers in `frontend/src/shared/lib/routes.ts`
- Admin compatibility route tests and route snapshot references
- Old service import tests proving the wrapper still works

## 5. References To Delete In The Next Pass

Delete only after admin Teacher Academy has either been moved to role-owned API routes or formally frozen as admin-only:

- Admin compatibility route handlers in `backend/roles/admin/routes/teacher_routes.py`
- Admin Teacher Academy route helpers in `frontend/src/shared/lib/routes.ts`
- Old service wrapper `backend/roles/admin/services/teacher_academy_service.py`
- Tests that intentionally import the old service path, after equivalent domain-service tests exist
- Route snapshot entries for `/admin/teacher-academy...`, after the old routes are intentionally removed

## 6. Deletion Conditions

Before deleting anything:

1. No production frontend role workspace posts to `/admin/teacher-academy...`.
2. Admin/system-admin behavior has a replacement route or an approved removal decision.
3. `rg "backend.roles.admin.services.teacher_academy_service"` returns only deletion-plan/history references.
4. `rg "/admin/teacher-academy|adminTeacherAcademy"` returns only approved admin compatibility references or no references.
5. Academic Director route tests pass for create, schedule, assess, status, and promote.
6. HOD route tests pass for own-scope success and out-of-scope denial.
7. Teacher Academy selected lesson, progress, schedule, and assessment tests still pass.
8. Full pytest, frontend type-check, frontend build, and `git diff --check` pass.

## 7. Tests Required Before Deletion

- Domain service import and query split tests.
- Old wrapper removal tests updated to import `backend.domains.teacher_academy.service`.
- Academic Director API tests for all Teacher Academy actions.
- HOD API tests for schedule, assessment, status, and scope denial.
- Frontend source tests proving AD/HOD route selection does not call admin endpoints.
- Admin/system-admin regression test confirming either replacement behavior or intentional route removal.
- Full regression for `/academic-director/teacher-academy`, `/head-of-department/teacher-academy`, `/teacher`, `/admin`, student dashboard, and parent flow.
