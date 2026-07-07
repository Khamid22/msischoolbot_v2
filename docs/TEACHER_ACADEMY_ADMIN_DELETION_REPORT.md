# Teacher Academy Admin Deletion Report

Date: 2026-07-07

Scope: Legacy Deletion Phase 1. Removed only the old Teacher Academy admin action dependency that was already classified SAFE_DELETE_NOW in `LEGACY_DELETION_AUDIT.md`.

No database schema changes were made. `/admin` remains available for system/admin compatibility.

## Deleted Files

| Deleted path | Why safe | Replacement path | Tests/proof |
| --- | --- | --- | --- |
| `backend/roles/admin/services/teacher_academy_service.py` | It was only a compatibility import wrapper after Teacher Academy business logic moved to the domain layer. Runtime imports now use the domain service directly. | `backend/domains/teacher_academy/service.py` and `backend/domains/teacher_academy/queries.py` | `tests/test_database_restructure_db1.py::test_old_admin_teacher_academy_service_path_is_removed` asserts the file is absent and page service imports the domain service. |

## Deleted Admin Route Functions and Helpers

Removed from `backend/roles/admin/routes/teacher_routes.py`:

- `_form_list`
- `_academy_payload`
- `ACADEMY_SECTIONS`
- `ACADEMY_CRITERIA_REMARKS`
- `_assessment_sections_from_form`
- `_assessment_scores_from_form`
- `create_teacher_academy_route`
- `update_teacher_academy_assignment_route`
- `add_teacher_academy_assessment_route`
- `update_teacher_academy_status_route`
- `promote_teacher_academy_route`

These handlers were old admin action routes. Academic Director and Head of Department now use their own role APIs.

## Deleted Frontend Admin Action Helpers

Removed from `frontend/src/shared/lib/routes.ts`:

- `adminTeacherAcademyCreate`
- `adminTeacherAcademyAssignment`
- `adminTeacherAcademyAssessment`
- `adminTeacherAcademyStatus`
- `adminTeacherAcademyPromote`

`TeacherAcademyPanel.tsx` now resolves action routes only for Academic Director and HOD modes. True admin mode keeps read/display compatibility without posting Teacher Academy actions through admin endpoints.

## Replacement Paths

| Capability | Replacement |
| --- | --- |
| AD create academy teacher | `POST /api/v1/academic-director/teacher-academy` |
| AD schedule lesson | `POST /api/v1/academic-director/teacher-academy/assignments/{assignment_id}` |
| AD assess lesson | `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/assessments` |
| AD status update | `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/status` |
| AD promote | `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/promote` |
| AD delete | `POST /api/v1/academic-director/teacher-academy/{academy_teacher_id}/delete` |
| HOD schedule lesson | `POST /api/v1/head-of-department/teacher-academy/assignments/{assignment_id}` |
| HOD assess lesson | `POST /api/v1/head-of-department/teacher-academy/{academy_teacher_id}/assessments` |
| HOD status update | `POST /api/v1/head-of-department/teacher-academy/{academy_teacher_id}/status` |
| API v1 response helpers | `backend/api/v1/teacher_academy_actions.py` |
| Temporary compatibility wrapper | `backend/roles/common/teacher_academy_api.py` |
| Business logic | `backend/domains/teacher_academy/service.py` |
| SQL/data access | `backend/domains/teacher_academy/queries.py` |

## Safety Proof

Reference search before deletion showed the old runtime route and service wrapper were already absent from active runtime code. Remaining matches were reports/docs and negative tests.

After cleanup, runtime source should continue to satisfy:

```bash
rg "/admin/teacher-academy" backend frontend tests/route_snapshot.txt
rg "backend.roles.admin.services.teacher_academy_service" backend frontend tests/route_snapshot.txt
```

Expected result: no runtime matches, except tests that intentionally assert the removed admin routes/import path stay absent when included in a broader docs/tests search.

## Replacement Test Coverage

| Requirement | Coverage |
| --- | --- |
| AD create works through AD route | `tests/test_teacher_academy_clean_api_routes.py::test_academic_director_create_academy_teacher_uses_selected_lessons_and_safe_credentials` |
| AD schedule/assess/status/promote works through AD routes | `tests/test_teacher_academy_clean_api_routes.py::test_academic_director_schedule_assess_status_and_promote_routes_call_domain_service` |
| HOD schedule works with scope guard | `tests/test_teacher_academy_clean_api_routes.py::test_hod_schedule_own_scope_succeeds_and_out_of_scope_is_denied` |
| HOD assess/status work with scope guard | `tests/test_teacher_academy_clean_api_routes.py::test_hod_teacher_routes_enforce_subject_scope` |
| Old admin Teacher Academy action routes are removed | `tests/test_teacher_academy_tomorrow_ready.py::test_old_admin_teacher_academy_action_routes_are_removed` |
| Old admin service wrapper is removed | `tests/test_database_restructure_db1.py::test_old_admin_teacher_academy_service_path_is_removed` |
| Admin compatibility still loads | `tests/test_phase2a_system_admin_workspace_cards.py` and `tests/test_teacher_academy_tomorrow_ready.py::test_academy_critical_routes_remain_registered` |
| Teacher cabinet still loads | `tests/test_teacher_academy_tomorrow_ready.py::test_teacher_route_exposes_academy_overview_lessons_timetable_and_updates` |
| Student and parent routes still pass | full `python3 -m pytest` suite, including student/parent route coverage |

## Remaining References and Why

Remaining literal references to old admin Teacher Academy routes are allowed only in:

- Negative tests that assert old admin action routes are not registered.
- Audit/deletion reports that explain what was removed.

Remaining `adminTeacherAcademy` references are not old admin action helpers. They are a bootstrap prop name used to pass Teacher Academy rows into admin/AD/HOD React state. That naming is classified REPLACE_THEN_DELETE, not SAFE_DELETE_NOW.

## Conclusion

The old Teacher Academy admin mutation dependency has been removed. Admin/system admin remains available, AD/HOD role APIs own Teacher Academy actions, HOD scope guards remain in place, and domain service/query modules remain the canonical Teacher Academy implementation.
