# Frontend Cleanliness Report

> Superseded again 2026-07-14: the new recruitment workspace is active. The former candidate practice UI and `TrainingEvaluationModal.tsx` remain removed, and Teacher Academy remains active.

Scope: cleanup/refactor pass on `FastAPI-Run-System`. No redesign, no new widgets, no business features, and no push.

## Duplicate UI Removed

- Academic Director and HOD Overview pages no longer render profile/logout cards.
- Profile/logout cards now render only through the explicit profile view.
- Old hash profile route constants were removed from `frontend/src/shared/lib/routes.ts`.
- Academic nav active-state logic no longer treats `#academic-director-profile` or `#head-of-department-profile` as Profile; Overview remains Overview.

## Label Cleanup

- Academic Director Teacher Academy CTA changed from "assign lessons" to "select lessons".
- Teacher cabinet empty-state detail changed from "assign lessons" to "select lessons".
- Existing tests continue to guard against visible Teacher Academy "Assign" action labels and "Training" tab wording.

## Components Kept And Why

| Component | Why kept |
| --- | --- |
| `RoleWorkspaceShell`, `RoleSidebar`, `RoleMobileNav` | Active shared role shell/navigation system. |
| `Modal`, `ConfirmDialog`, `FloatingToast` | Active shared overlay/notification system. |
| `ResponsiveTable`, `MobileCardList`, `MetricGrid`, `MetricCard`, `ActionMenu`, `IconButton` | Active shared responsive UI components. |
| `AdminSidebar` inside `frontend/src/roles/admin/pages/Admin.tsx` | Still active for system/admin only. AD/HOD tests assert it is not present in their pages. |
| `TrainingEvaluationModal.tsx` | Still used by admin HR/candidate practice flow, which is separate from Teacher Academy. |

## Old Components Deleted

No frontend components were deleted in this pass. The audit did not find an unused component with enough proof to delete safely.

## Mobile Nav Behavior Verification

- `RoleWorkspaceShell` keeps auto mode: Telegram Mini App uses fixed bottom nav through `RoleMobileNav`; normal website mobile uses the hamburger drawer.
- Desktop uses the sidebar.
- Source tests assert drawer dialog, escape/body scroll lock, and bottom safe-area padding.

## Remaining Frontend Legacy References

- `adminTeacherAcademy` remains a bootstrap prop name used by admin, AD, and HOD Teacher Academy pages. It is not an old `/admin/teacher-academy` action helper.
- `TrainingEvaluationModal` and `training` keys remain in the HR/candidate practice area. They are not Teacher Academy navigation labels.
- `Assigned` appears as a status/field label where it describes already assigned groups or lesson state, not the old schedule action.

## Next Frontend Cleanup Recommendation

1. Rename bootstrap prop `adminTeacherAcademy` to a neutral `teacherAcademyRows` with a temporary alias.
2. If HR/candidate practice is still active, separate its naming from Teacher Academy in a dedicated pass.
3. Keep deleting UI only after reference search proves no active route imports it.
