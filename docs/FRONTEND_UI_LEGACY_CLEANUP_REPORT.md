# Frontend UI Legacy Cleanup Report

Date: 2026-07-07

Scope: source audit during architecture migration. No redesign or new UI feature was added.

## Duplicate UI Removed Or Already Cleaned

No additional components were deleted in this pass. Earlier UI cleanup already removed the AD/HOD home/profile duplication and kept logout/profile behavior inside the sidebar/footer and Profile page.

## Components Kept

- `RoleWorkspaceShell`, `RoleSidebar`, and `RoleMobileNav`: active shared shell/navigation system.
- `Modal`, `ConfirmDialog`, and `FloatingToast`: active shared modal/toast system.
- `ResponsiveTable`, `MobileCardList`, `MetricGrid`, `MetricCard`, `ActionMenu`, and `IconButton`: active responsive UI primitives.
- `AcademicDirectorShell.tsx`: still active as the AD/HOD wrapper around the shared role shell.
- `AdminSidebar`: kept only inside the true `/admin` workspace.

## Search Results

- No active AD/HOD source imports the old Admin sidebar.
- Teacher Academy visible action labels remain `Schedule`, `Assess`, and review/promote language.
- Hardcoded truncated labels like `Announc...` are guarded by source tests.
- `Training` label checks remain in tests/source guards so visible role navigation stays Teacher Academy wording.

## Mobile Nav Behavior

Website mobile uses the drawer/toggle role shell behavior. Telegram Mini App mobile keeps the bottom navigation and safe-area padding. No student/parent/teacher page was intentionally changed by this pass.

## Remaining Cleanup

Old admin modals, admin panel-specific components, and student/teacher/parent route components are still active and should not be deleted until imports and route ownership are replaced.
