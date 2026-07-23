"""Shared role workspace mobile navigation source contracts."""

from pathlib import Path


def test_role_workspace_shell_supports_telegram_bottom_nav_and_website_drawer():
    source = Path("frontend/src/shared/ui/RoleWorkspaceShell.tsx").read_text()
    mobile_nav = Path("frontend/src/shared/ui/RoleMobileNav.tsx").read_text()
    telegram = Path("frontend/src/shared/lib/telegram.ts").read_text()

    assert 'export type MobileNavigationMode = "auto" | "bottom" | "drawer"' in source
    assert 'mobileNavigationMode = "auto"' in source
    assert "isTelegramMiniApp()" in source
    assert "shouldUseBottomNav" in source
    assert "shouldUseDrawer" in source
    assert "<RoleMobileNav" in source
    assert "Open ${roleLabel} navigation" in source
    assert 'role="dialog"' in source
    assert 'aria-modal="true"' in source
    assert 'aria-label="Close navigation drawer"' in source
    assert "bg-foreground/60" in source
    assert "useBodyScrollLock(drawerOpen)" in source
    assert '"Escape"' in source
    assert "onClick={() => setDrawerOpen(false)}" in source
    assert "lg:hidden" in source
    assert "workspace-main-auto-sidebar" in source
    assert "lg:ml-[var(--workspace-sidebar-width)]" in source
    assert "fixed inset-x-0 bottom-0" in mobile_nav
    assert "var(--app-bottom-inset)" in mobile_nav
    assert "export function isTelegramMiniApp" in telegram
    assert 'typeof window === "undefined"' in telegram
    assert "window.Telegram?.WebApp" in telegram
