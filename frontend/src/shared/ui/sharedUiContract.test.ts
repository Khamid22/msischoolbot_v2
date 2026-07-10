import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { uiLayers } from "./layers.ts";

/**
 * Contract tests for the shared UI components. The repo intentionally has no
 * DOM test runner (no jsdom/RTL), so structural requirements — portals,
 * backdrops, scroll locking, aria labels, responsive classes — are asserted
 * against component source. If a refactor changes how a contract is met,
 * update the assertion alongside it.
 */
function source(name: string): string {
  return readFileSync(new URL(`./${name}`, import.meta.url), "utf8");
}

describe("uiLayers z-scale", () => {
  it("stacks sidebar < mobile nav < toast < overlay < popover", () => {
    const order: Array<keyof typeof uiLayers> = ["sidebar", "mobileNav", "toast", "overlay", "popover"];
    const values = order.map((key) => {
      const match = uiLayers[key].match(/z-\[?(\d+)\]?/);
      assert.ok(match, `uiLayers.${key} ("${uiLayers[key]}") is not a z-index class`);
      return Number(match[1]);
    });
    for (let i = 1; i < values.length; i += 1) {
      assert.ok(values[i] > values[i - 1], `uiLayers.${order[i]} must sit above uiLayers.${order[i - 1]}`);
    }
  });
});

describe("RoleWorkspaceShell", () => {
  const src = source("RoleWorkspaceShell.tsx");
  const telegramSrc = readFileSync(new URL("../lib/telegram.ts", import.meta.url), "utf8");

  it("renders sidebar, mobile nav, and a content slot", () => {
    assert.match(src, /<RoleSidebar/);
    assert.match(src, /<RoleMobileNav/);
    assert.match(src, /\{children\}/);
  });

  it("reserves bottom padding so the fixed mobile nav never overlaps content", () => {
    assert.match(src, /pb-\[calc\(var\(--app-bottom-inset\)\+/);
  });

  it("supports Telegram bottom nav and website mobile drawer modes", () => {
    assert.match(src, /mobileNavigationMode = "auto"/);
    assert.match(src, /isTelegramMiniApp/);
    assert.match(src, /shouldUseBottomNav/);
    assert.match(src, /shouldUseDrawer/);
    assert.match(src, /<RoleMobileNav/);
    assert.match(src, /Open .* navigation/);
    assert.match(src, /role="dialog"/);
    assert.match(src, /Close navigation drawer/);
    assert.match(src, /bg-foreground\/60/);
    assert.match(src, /useBodyScrollLock\(drawerOpen\)/);
    assert.match(src, /"Escape"/);
  });

  it("places the website drawer toggle before the mobile title block", () => {
    assert.match(
      src,
      /<button[\s\S]*?setDrawerOpen\(true\)[\s\S]*?<Menu className="h-5 w-5" \/>[\s\S]*?<\/button>\s*<div className="min-w-0 flex-1">/,
    );
  });

  it("keeps Telegram Mini App detection safe for browser builds", () => {
    assert.match(telegramSrc, /export function isTelegramMiniApp/);
    assert.match(telegramSrc, /typeof window === "undefined"/);
    assert.match(telegramSrc, /window\.Telegram\?\.WebApp/);
  });
});

describe("RoleSidebar", () => {
  const src = source("RoleSidebar.tsx");

  it("marks the active link and labels the logout icon button", () => {
    assert.match(src, /aria-current=\{isActive \? "page" : undefined\}/);
    assert.match(src, /aria-label="Logout"/);
  });

  it("uses the shared sidebar layer and hides below lg", () => {
    assert.match(src, /uiLayers\.sidebar/);
    assert.match(src, /hidden w-64 .*lg:flex/);
  });
});

describe("RoleMobileNav", () => {
  const src = source("RoleMobileNav.tsx");

  it("is fixed to the bottom with safe-area padding", () => {
    assert.match(src, /fixed inset-x-0 bottom-0/);
    assert.match(src, /var\(--app-bottom-inset\)/);
  });

  it("never truncates labels", () => {
    const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
    assert.doesNotMatch(code, /\btruncate\b/);
  });
});

describe("Modal / BottomSheet", () => {
  const src = source("Modal.tsx");
  const hookSrc = source("useBodyScrollLock.ts");

  it("renders through a portal on the shared overlay layer with a backdrop", () => {
    assert.match(src, /createPortal/);
    assert.match(src, /document\.body,?\s*\)/);
    assert.match(src, /uiLayers\.overlay/);
    assert.match(src, /bg-foreground\/60/);
    assert.match(src, /data-modal-backdrop="true"/);
  });

  it("locks body scroll while open", () => {
    assert.match(hookSrc, /export function useBodyScrollLock/);
    assert.match(hookSrc, /document\.body\.style\.overflow = "hidden"/);
    assert.match(hookSrc, /bodyLockCount/);
  });

  it("closes on Escape and has a labelled close button", () => {
    assert.match(src, /"Escape"/);
    assert.match(src, /aria-label="Close"/);
  });

  it("is a labelled dialog and exports BottomSheet on the same layer", () => {
    assert.match(src, /aria-modal="true"/);
    assert.match(src, /export function BottomSheet/);
  });

  it("exposes structured body/footer slots and mobile sheet/fullscreen modes", () => {
    assert.match(src, /export function ModalHeader/);
    assert.match(src, /export function ModalBody/);
    assert.match(src, /export function ModalFooter/);
    assert.match(src, /mobileMode = "sheet"/);
    assert.match(src, /mobileMode === "fullscreen"/);
    assert.match(src, /data-mobile-mode=\{mobileMode\}/);
    assert.match(src, /var\(--app-bottom-inset\)/);
    assert.match(src, /motion-reduce:animate-none/);
  });
});

describe("FloatingToast", () => {
  const src = source("FloatingToast.tsx");

  it("supports success, error, warning, and info variants", () => {
    for (const tone of ["success", "error", "warning", "info"]) {
      assert.match(src, new RegExp(`${tone}: \\{`), `missing toast variant "${tone}"`);
    }
  });

  it("auto-dismisses within 3-4 seconds by default", () => {
    const match = src.match(/autoDismissMs = (\d+)/);
    assert.ok(match, "useFloatingToast must declare a default auto-dismiss");
    const ms = Number(match[1]);
    assert.ok(ms >= 3000 && ms <= 4000, `auto-dismiss ${ms}ms is outside 3-4s`);
  });

  it("offers a labelled manual close and stays above the mobile nav", () => {
    assert.match(src, /aria-label="Dismiss notification"/);
    assert.match(src, /uiLayers\.toast/);
    assert.match(src, /bottom-\[calc\(var\(--app-bottom-inset\)\+/);
  });
});

describe("MetricGrid", () => {
  const src = source("MetricGrid.tsx");

  it("uses the responsive column classes from the spec", () => {
    assert.match(src, /grid-cols-1/);
    assert.match(src, /min-\[400px\]:grid-cols-2/);
    assert.match(src, /lg:grid-cols-4/);
  });
});

describe("ResponsiveTable / MobileCardList", () => {
  it("hides the table below its breakpoint and the cards above it", () => {
    const table = source("ResponsiveTable.tsx");
    assert.match(table, /hidden md:block/);
    assert.match(table, /hidden lg:block/);

    const cards = source("MobileCardList.tsx");
    assert.match(cards, /md:hidden/);
    assert.match(cards, /lg:hidden/);
  });
});

describe("IconButton / ActionMenu", () => {
  it("IconButton requires a label and forwards it to aria-label", () => {
    const src = source("IconButton.tsx");
    assert.match(src, /label: string;/);
    assert.match(src, /aria-label=\{label\}/);
  });

  it("ActionMenu labels its trigger and renders a popover-layer menu", () => {
    const src = source("ActionMenu.tsx");
    assert.match(src, /aria-label=\{label\}/);
    assert.match(src, /role="menu"/);
    assert.match(src, /uiLayers\.popover/);
  });

  it("keeps icon-only triggers at least 44px square", () => {
    assert.match(source("IconButton.tsx"), /h-11 min-h-11 w-11 min-w-11/);
    const actionMenu = source("ActionMenu.tsx");
    assert.match(actionMenu, /h-11 min-h-11 w-11 min-w-11/);
    assert.match(actionMenu, /flex min-h-11 w-full/);
  });

  it("ActionMenu clamps its popover to the viewport and can flip above the trigger", () => {
    const src = source("ActionMenu.tsx");
    assert.match(src, /spaceBelow/);
    assert.match(src, /spaceAbove/);
    assert.match(src, /placement: opensAbove \? "top" : "bottom"/);
    assert.match(src, /maxHeight/);
    assert.match(src, /overflow-y-auto/);
  });
});

describe("Shared touch targets", () => {
  it("keeps modal and drawer close actions at least 44px square", () => {
    assert.match(source("Modal.tsx"), /h-11 w-11/);
    assert.match(source("Drawer.tsx"), /h-11 w-11/);
  });

  it("keeps pagination actions and the shared touch utility at least 44px", () => {
    const pagination = source("Pagination.tsx");
    assert.match(pagination, /h-11 min-h-11/);

    const css = readFileSync(new URL("../../index.css", import.meta.url), "utf8");
    assert.match(css, /\.miniapp-touch-target\s*\{[\s\S]*?min-height:\s*2\.75rem;/);
    assert.match(css, /\.miniapp-touch-target\s*\{[\s\S]*?min-width:\s*2\.75rem;/);
  });

  it("keeps role navigation and account actions reachable and touch-sized", () => {
    const sidebar = source("RoleSidebar.tsx");
    const shell = source("RoleWorkspaceShell.tsx");
    assert.match(sidebar, /routes\.accountSecurity/);
    assert.match(sidebar, /min-h-11/);
    assert.match(sidebar, /h-11 w-11/);
    assert.match(shell, /routes\.accountSecurity/);
    assert.match(shell, /h-11 w-11/);
  });

  it("keeps browser pinch zoom available", () => {
    const html = readFileSync(new URL("../../../index.html", import.meta.url), "utf8");
    assert.doesNotMatch(html, /maximum-scale/);
    assert.doesNotMatch(html, /user-scalable\s*=\s*no/);
  });
});
