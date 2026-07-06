# UI/UX Repair Report

Date: 2026-07-06

Mode: UI/UX stabilization audit only. No source fixes were implemented.

Type check:

```text
npm --prefix frontend run check-types
passed
```

## Files Inspected

- `frontend/src/roles/common/components/AcademicDirectorShell.tsx`
- `frontend/src/roles/common/pages/RoleHome.tsx`
- `frontend/src/roles/academic_director/pages/TeacherAcademy.tsx`
- `frontend/src/roles/academic_director/pages/HeadOfDepartments.tsx`
- `frontend/src/roles/head_of_department/pages/TeacherAcademy.tsx`
- `frontend/src/roles/admin/pages/Admin.tsx`
- `frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx`
- `frontend/src/roles/admin/panels/teachers/CandidateCard.tsx`
- `frontend/src/roles/admin/panels/teachers/CandidateDetailModal.tsx`
- `frontend/src/roles/admin/panels/teachers/TrainingEvaluationModal.tsx`
- `frontend/src/roles/admin/panels/teachers/shared.ts`
- `frontend/src/roles/teacher/pages/TeacherHome.tsx`
- `frontend/src/roles/teacher/teacherNav.ts`
- `frontend/src/shared/lib/api.ts`
- `frontend/src/shared/lib/bootstrap.ts`
- `frontend/src/shared/lib/dashboard-data.ts`
- `frontend/src/shared/lib/lesson-date.ts`
- `frontend/src/shared/lib/motion.ts`
- `frontend/src/shared/lib/routes.ts`
- `frontend/src/shared/lib/staleUiState.ts`
- `frontend/src/shared/lib/telegram.ts`
- `frontend/src/shared/lib/useDismissibleLayer.ts`
- `frontend/src/shared/lib/useLazyVisible.ts`
- `frontend/src/shared/ui/ActionMenu.tsx`
- `frontend/src/shared/ui/AdminEmbedLayout.tsx`
- `frontend/src/shared/ui/Avatar.tsx`
- `frontend/src/shared/ui/Badge.tsx`
- `frontend/src/shared/ui/ChartCard.tsx`
- `frontend/src/shared/ui/ConfirmDialog.tsx`
- `frontend/src/shared/ui/Drawer.tsx`
- `frontend/src/shared/ui/FloatingToast.tsx`
- `frontend/src/shared/ui/Pagination.tsx`
- `frontend/src/shared/ui/PortalCard.tsx`
- `frontend/src/shared/ui/ProgressBar.tsx`
- `frontend/src/shared/ui/StatCard.tsx`
- `frontend/src/shared/ui/TelegramLayout.tsx`
- `frontend/src/app/App.tsx`

Note: the requested path `frontend/src/App.tsx` does not exist. The active app entry inspected is `frontend/src/app/App.tsx`.

## Top Repair Priorities

1. Shared `ActionMenu` is rendered inline with `absolute z-50`, so it can be clipped by `overflow-hidden` cards and scroll containers.
2. Admin edit-resource modal uses `z-50`, while the admin mobile navigation overlay uses `z-[60]`, so nav can appear above a modal.
3. There are multiple independent sidebar and mobile-nav implementations, which increases duplicate sidebar/navbar and z-index drift risk.
4. AD/HOD academy pages reuse the admin `TeacherAcademyPanel`, so role-specific UI can regress if admin-only actions or wording are added there.
5. Admin desktop shell uses `lg:overflow-hidden` plus nested scrolling, which can clip menus, modals, sticky headers, and large panels.
6. Teacher Academy table has many inline action buttons in a fixed-width table and no shared action collapse behavior.
7. Teacher Academy mobile cards use ad hoc wrapping action rows; buttons can become ragged or float on narrow screens.
8. Assessment modal uses a horizontal rubric table on mobile and an ad hoc footer, instead of a card-based mobile list and shared modal actions.
9. Modal implementations are fragmented across `Admin.tsx`, `TeacherAcademyPanel.tsx`, `TeacherHome.tsx`, `ConfirmDialog`, `Drawer`, and legacy candidate modals.
10. Active navigation state is split across URL reads, hard-coded active props, and local state, which can make active states stale or inconsistent.

## Findings

### 1. Inline action menus can be clipped

- Problem: `ActionMenu` renders the dropdown as an absolutely positioned child inside the same DOM container. Parents such as `ChartCard`, table wrappers, and rounded cards frequently use `overflow-hidden` or `overflow-auto`, so menus can be visually cut off even with `z-50`.
- File/component: `frontend/src/shared/ui/ActionMenu.tsx`, `frontend/src/shared/ui/ChartCard.tsx`, table/card users.
- Severity: critical
- Suggested fix: Portal the menu to `document.body`, calculate trigger position, use collision-aware placement, and place it on the shared overlay z-index scale.
- Whether shared component fix can solve it: yes, fix `ActionMenu`.
- Risk level: medium. This is shared UI behavior, so verify all existing menu users.

### 2. Admin modal can appear behind mobile navigation

- Problem: Admin mobile nav overlay is `z-[60]`, while the edit-resource modal is `z-50`. If both states are active or state cleanup fails, the modal can sit behind the nav overlay.
- File/component: `frontend/src/roles/admin/pages/Admin.tsx`
- Severity: critical
- Suggested fix: Move edit-resource modal to a shared `Modal/BottomSheet` with a higher modal layer than mobile nav and with route-safe close behavior.
- Whether shared component fix can solve it: yes, shared `Modal/BottomSheet`.
- Risk level: medium. Z-index changes should be tested across admin, AD, HOD, and teacher overlays.

### 3. Modal implementations are fragmented

- Problem: There are several independent modal/dialog patterns: admin edit-resource modal, `TeacherAcademyPanel` `ModalShell`, teacher `LessonReportSheet`, `ConfirmDialog`, `Drawer`, and legacy candidate evaluation modals. Body scroll lock, safe-area padding, focus behavior, action footer layout, and z-index vary.
- File/component: `Admin.tsx`, `TeacherAcademyPanel.tsx`, `TeacherHome.tsx`, `ConfirmDialog.tsx`, `Drawer.tsx`, `TrainingEvaluationModal.tsx`
- Severity: critical
- Suggested fix: Create one shared `Modal/BottomSheet` primitive for full dialog behavior and migrate local modal shells to it incrementally.
- Whether shared component fix can solve it: yes, shared `Modal/BottomSheet`.
- Risk level: medium-high. Dialog behavior is user-facing and should be verified on desktop and mobile.

### 4. Duplicate role shells create navigation drift

- Problem: AD, HOD, admin, and teacher shells each define their own desktop sidebars, mobile navigation, spacing, bottom padding, active styling, and z-index. This increases the chance of duplicate sidebars/navbars or inconsistent responsive behavior.
- File/component: `AcademicDirectorShell.tsx`, `RoleHome.tsx`, `Admin.tsx`, `TeacherHome.tsx`, AD/HOD academy pages
- Severity: high
- Suggested fix: Create `PageShell`, `Sidebar`, and `MobileBottomNav` components with role config, shared spacing, safe areas, and a single z-index scale.
- Whether shared component fix can solve it: yes, `PageShell`, `Sidebar`, `MobileBottomNav`.
- Risk level: medium. Migrate one role at a time to avoid touching student or parent flows.

### 5. Admin desktop layout can clip nested UI

- Problem: Admin page root and main use `lg:overflow-hidden`, then render the active panel inside an inner `overflow-y-auto` container. This can trap long panels, dropdowns, sticky elements, and portalless overlays.
- File/component: `frontend/src/roles/admin/pages/Admin.tsx`
- Severity: high
- Suggested fix: Let `PageShell` own the page scroll model. Avoid nested overflow unless a panel explicitly needs it.
- Whether shared component fix can solve it: yes, `PageShell`.
- Risk level: medium. Admin has many panels, so verify panel scroll positions and sticky headers.

### 6. AD/HOD pages reuse admin Teacher Academy internals

- Problem: AD and HOD pages mount `TeacherAcademyPanel` from the admin panel folder. Current visible labels are role-safe, but future admin-only actions, labels, or preview behavior can leak into AD/HOD pages because the component is shared by folder ownership rather than a role-neutral module.
- File/component: `frontend/src/roles/academic_director/pages/TeacherAcademy.tsx`, `frontend/src/roles/head_of_department/pages/TeacherAcademy.tsx`, `frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx`
- Severity: high
- Suggested fix: Move the UI-only Teacher Academy panel to a role-neutral shared/academic department module, with explicit role capabilities passed in.
- Whether shared component fix can solve it: partially, through `PageShell`, `ActionMenu`, and role-neutral panel extraction.
- Risk level: medium. Keep existing backend routes and Auth V2 unchanged.

### 7. Old Admin Console label is isolated but still risky in preview modes

- Problem: AD/HOD routes do not currently render `AdminSidebar`, and `Admin Console` was not found in the AD/HOD shell pages. However, `Admin.tsx` still uses `Admin Console` in the sidebar and mobile header, while admin preview modes can display role workspaces. This is a leakage risk if role-preview routes are reused outside admin.
- File/component: `frontend/src/roles/admin/pages/Admin.tsx`, `frontend/src/app/App.tsx`
- Severity: high
- Suggested fix: Keep `Admin Console` only for true admin pages. If preview modes remain, make the shell title role-aware and prevent AD/HOD routes from mounting `AdminPage`.
- Whether shared component fix can solve it: yes, shared `PageShell` and `Sidebar` with role config.
- Risk level: low-medium. Current AD/HOD app routes already point to dedicated pages.

### 8. Teacher Academy table actions are too dense

- Problem: The desktop Teacher Academy table has a fixed `min-w-[980px]`, `table-fixed`, and up to five inline action buttons in the Actions column. On narrower laptops this can wrap heavily and reduce scannability.
- File/component: `frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx`
- Severity: high
- Suggested fix: Move secondary actions into `ActionMenu`; keep one primary action inline. Use a shared responsive table pattern.
- Whether shared component fix can solve it: yes, `ActionMenu` and `ResponsiveTable/MobileCardList`.
- Risk level: medium. Action availability differs by teacher status, so verify each state.

### 9. Teacher Academy mobile card actions can float or wrap ragged

- Problem: Academy teacher mobile cards use `flex flex-wrap` with mixed `flex-1` and fixed-width action buttons. The row can become visually uneven on small screens.
- File/component: `frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx`
- Severity: high
- Suggested fix: Use a consistent action cluster: one full-width primary action, secondary actions in an `ActionMenu`, or a bottom action bar inside the card.
- Whether shared component fix can solve it: yes, `ActionMenu` and mobile card list conventions.
- Risk level: low-medium. UI-only, but action order should stay unchanged.

### 10. Assessment modal rubric is not mobile-first

- Problem: Assessment modal uses a horizontal `min-w-[760px]` rubric table inside a modal. Mobile users must scroll sideways inside a vertical dialog, and the footer uses local flex wrapping instead of the shared modal action pattern.
- File/component: `frontend/src/roles/admin/panels/teachers/TeacherAcademyPanel.tsx`
- Severity: high
- Suggested fix: Use `ResponsiveTable/MobileCardList` for rubric criteria on mobile and shared `Modal/BottomSheet` actions that stack full-width on narrow viewports.
- Whether shared component fix can solve it: yes, `Modal/BottomSheet` and `ResponsiveTable/MobileCardList`.
- Risk level: medium. Needs form-field regression testing.

### 11. Teacher report sheet does not lock body scroll

- Problem: `LessonReportSheet` is a fixed dialog with `role="dialog"` and `aria-modal`, but it uses `useDismissibleLayer` only and does not lock `document.body` scroll.
- File/component: `frontend/src/roles/teacher/pages/TeacherHome.tsx`
- Severity: high
- Suggested fix: Replace it with the shared `Modal/BottomSheet`, or add the same body scroll lock behavior used by the shared dialog primitive.
- Whether shared component fix can solve it: yes, `Modal/BottomSheet`.
- Risk level: low-medium. Teacher page only; avoid touching student dashboard or parent flow.

### 12. Active route state is inconsistent

- Problem: AD/HOD home reads `window.location` at render to infer active nav. AD/HOD academy pages pass hard-coded active keys. Admin and teacher pages use local state instead of URL-aware route state. This can make active indicators stale after hash-only changes, preview switches, or browser navigation.
- File/component: `RoleHome.tsx`, `AcademicDirectorShell.tsx`, `Admin.tsx`, `TeacherHome.tsx`, `teacherNav.ts`
- Severity: high
- Suggested fix: Centralize active-route resolution in `PageShell` or nav config. Use URLs for route pages and explicit tab state only for in-page tabs.
- Whether shared component fix can solve it: yes, `PageShell`, `Sidebar`, `MobileBottomNav`.
- Risk level: medium. Keep existing URLs stable.

### 13. Teacher mobile bottom nav has an academy timetable dead state

- Problem: In academy teacher mode, mobile bottom nav keys are Home, Reports/Lessons, Updates, Profile. `bottomNavActiveKey` returns `null` for `timetable`, but the profile view includes a Timetable button on larger screens. If `timetable` becomes reachable on mobile, no bottom nav item is active.
- File/component: `frontend/src/roles/teacher/teacherNav.ts`, `frontend/src/roles/teacher/pages/TeacherHome.tsx`
- Severity: medium
- Suggested fix: Either hide academy timetable on mobile completely, map it to Profile/Lessons, or add it to the academy mobile nav config.
- Whether shared component fix can solve it: yes, `MobileBottomNav`.
- Risk level: low. Pure UI navigation behavior.

### 14. Tables on mobile are inconsistent

- Problem: `HeadOfDepartments` has mobile cards, Teacher Academy has mobile cards for teacher rows, Teacher gradebook uses horizontal scroll, and assessment rubric uses horizontal scroll inside a modal. There is no common table/mobile-card pattern.
- File/component: `HeadOfDepartments.tsx`, `TeacherAcademyPanel.tsx`, `TeacherHome.tsx`
- Severity: high
- Suggested fix: Create `ResponsiveTable/MobileCardList` and migrate high-traffic tables first.
- Whether shared component fix can solve it: yes, `ResponsiveTable/MobileCardList`.
- Risk level: medium. Data density and row actions vary per screen.

### 15. Metric cards are duplicated and waste space in dense views

- Problem: Metric cards exist as local `MetricCard`, local `metric()` helper, `StatCard`, and hard-coded sections. The grids often jump to four columns and can consume valuable vertical space in the admin/academy panels.
- File/component: `RoleHome.tsx`, `TeacherAcademyPanel.tsx`, `TeacherHome.tsx`, `HeadOfDepartments.tsx`, `shared/ui/StatCard.tsx`
- Severity: medium
- Suggested fix: Create one `MetricCard` with compact/dense variants and responsive limits.
- Whether shared component fix can solve it: yes, `MetricCard`.
- Risk level: low-medium. Mostly visual, but affects scan speed.

### 16. Status badge styles and labels are duplicated

- Problem: Status badges are implemented locally in several files despite a shared `Badge` existing. Tone mapping, shape, casing, and truncation differ across role pages.
- File/component: `HeadOfDepartments.tsx`, `TeacherAcademyPanel.tsx`, `TeacherHome.tsx`, `shared/ui/Badge.tsx`
- Severity: medium
- Suggested fix: Create a `StatusBadge` wrapper around `Badge` with shared tone and label maps for Academy, account, and lesson states.
- Whether shared component fix can solve it: yes, `StatusBadge`.
- Risk level: low. UI-only if mappings preserve current labels.

### 17. Progress bars are duplicated

- Problem: Progress bars are locally implemented in teacher and academy cards even though `shared/ui/ProgressBar.tsx` exists.
- File/component: `TeacherAcademyPanel.tsx`, `TeacherHome.tsx`, `shared/ui/ProgressBar.tsx`
- Severity: medium
- Suggested fix: Expand `ProgressBar` to cover labels, compact variants, and accessible value text, then replace local bars.
- Whether shared component fix can solve it: yes, `ProgressBar`.
- Risk level: low.

### 18. Empty states are duplicated

- Problem: Teacher pages and Teacher Academy use local empty-state blocks. Shape, spacing, icons, and copy density vary.
- File/component: `TeacherHome.tsx`, `TeacherAcademyPanel.tsx`, `HeadOfDepartments.tsx`
- Severity: medium
- Suggested fix: Create shared `EmptyState` with size variants and optional action slot.
- Whether shared component fix can solve it: yes, `EmptyState`.
- Risk level: low.

### 19. `ChartCard` clips children by default

- Problem: `ChartCard` root has `overflow-hidden`. This is visually useful for rounded corners but can clip action menus, sticky elements, and focused controls inside card bodies.
- File/component: `frontend/src/shared/ui/ChartCard.tsx`
- Severity: high
- Suggested fix: Remove default clipping or move clipping to an inner media/body wrapper. Add an explicit prop for cards that genuinely need clipping.
- Whether shared component fix can solve it: yes, fix `ChartCard`.
- Risk level: medium. Cards across admin panels may rely on the current clipping.

### 20. Legacy candidate practice modals still use older modal stack

- Problem: `TrainingEvaluationModal` and `RubricModal` use `z-50`, local fixed overlays, and no body scroll lock. They are legacy candidate practice UI, but they still sit near Teacher Academy work.
- File/component: `frontend/src/roles/admin/panels/teachers/TrainingEvaluationModal.tsx`
- Severity: high
- Suggested fix: Migrate to the shared `Modal/BottomSheet` when candidate practice UI is stabilized. Do not change backend field names.
- Whether shared component fix can solve it: yes, `Modal/BottomSheet`.
- Risk level: medium. Legacy workflow still has form state and candidate status transitions.

### 21. "Training" wording is mostly internal, but still mixed in legacy teacher files

- Problem: In AD/HOD Teacher Academy UI, visible labels now mostly say "Academy" or "Practice". Remaining `training_*` values and component names are internal, but they coexist with visible practice labels and can easily leak into UI copy during future edits.
- File/component: `TeacherAcademyPanel.tsx`, `TeacherHome.tsx`, `teacherNav.ts`, `TrainingEvaluationModal.tsx`, `shared.ts`
- Severity: medium
- Suggested fix: Keep backend/status keys unchanged, but centralize user-facing label maps so `training` never appears as visible copy unless explicitly approved.
- Whether shared component fix can solve it: partially, `StatusBadge` and label helper.
- Risk level: low-medium. Avoid renaming data keys during UI stabilization.

### 22. `frontend/src/App.tsx` requested path is stale

- Problem: The audit request included `frontend/src/App.tsx`, but the current app entry is `frontend/src/app/App.tsx`.
- File/component: `frontend/src/app/App.tsx`
- Severity: low
- Suggested fix: Update engineering notes or audit checklists to point at `frontend/src/app/App.tsx`.
- Whether shared component fix can solve it: no.
- Risk level: low.

## Shared Components To Create Or Fix

### PageShell

- Need: yes.
- Should handle: desktop left offset, mobile header/bottom padding, safe-area variables, page scroll model, z-index scale, and role-specific shell titles.
- Solves: duplicate shell layout, nested overflow, active route inconsistencies, duplicate sidebars/navbars.
- Risk level: medium.

### Sidebar

- Need: yes.
- Should handle: role config, active route state, logout slot, compact drawer rendering, and consistent icon/label layout.
- Solves: AD/HOD/admin/teacher sidebar duplication and old Admin Console leakage risk.
- Risk level: medium.

### MobileBottomNav

- Need: yes.
- Should handle: role config, active route mapping, safe-area padding, label truncation, and stable z-index below modals.
- Solves: inconsistent mobile nav z-index, active state drift, duplicate bottom nav code.
- Risk level: medium.

### Modal/BottomSheet

- Need: yes.
- Should handle: portal rendering, z-index above nav, body scroll lock, focus trap, Escape/outside close policy, safe-area padding, stacked mobile footer actions, and sheet-style mobile presentation.
- Solves: modal-behind-nav, body scroll, fragmented dialog behavior, legacy modal stack.
- Risk level: medium-high.

### MetricCard

- Need: yes.
- Should handle: compact/default variants, optional icon, detail text, width constraints, and dense dashboard mode.
- Solves: duplicated metrics and wasted space.
- Risk level: low-medium.

### StatusBadge

- Need: yes.
- Should handle: shared tone maps, label maps, truncation, optional icons, and status-specific aria labels.
- Solves: inconsistent badge copy and "Training" wording leakage.
- Risk level: low.

### ProgressBar

- Need: fix existing.
- Should handle: accessible value labels, size variants, tone variants, and optional inline text.
- Solves: duplicated local progress bars.
- Risk level: low.

### ResponsiveTable/MobileCardList

- Need: yes.
- Should handle: desktop table, mobile card rendering, sticky headers, row actions, empty state, and min-width escape hatches.
- Solves: inconsistent mobile tables and horizontal scroll inside modals.
- Risk level: medium.

### ActionMenu

- Need: fix existing.
- Should handle: portal, collision-aware placement, focus management, z-index scale, and disabled tooltips.
- Solves: clipped dropdowns and dense action-button rows.
- Risk level: medium.

### EmptyState

- Need: yes.
- Should handle: icon, title, detail, optional action, compact/default variants.
- Solves: inconsistent empty panels and repeated local implementation.
- Risk level: low.

## Guardrails For Repair Phase

- Do not change Auth V2.
- Do not change database schema.
- Do not change Teacher Academy backend logic.
- Keep backend field names such as `training_*` unless a separate migration is approved.
- Do not delete legacy candidate practice code during this stabilization pass.
- Do not touch student dashboard or parent flow unless a shared layout primitive breaks them.
- Do not push until reviewed.
