import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

function source(name: string): string {
  return readFileSync(new URL(`./${name}`, import.meta.url), "utf8");
}

describe("Parent workspace navigation", () => {
  const shell = source("ParentWorkspaceShell.tsx");
  const sharedNav = readFileSync(
    new URL("../../shared/ui/RoleMobileNav.tsx", import.meta.url),
    "utf8",
  );

  it("defines the five parent priorities in stable order", () => {
    const keys = ["home", "updates", "children", "payments", "support"];
    let previousIndex = -1;
    for (const key of keys) {
      const index = shell.indexOf(`key: "${key}"`);
      assert.ok(index > previousIndex, `${key} is missing or out of order`);
      previousIndex = index;
    }
  });

  it("uses the third Children item as the raised mobile destination", () => {
    assert.match(shell, /mobileNavigationMode="bottom"/);
    assert.match(shell, /mobileNavVariant="floating"/);
    assert.match(shell, /mobilePrimaryKey="children"/);
    assert.match(sharedNav, /isPrimary/);
    assert.match(sharedNav, /-translate-y-3/);
  });

  it("keeps labels, touch targets, desktop sidebar, and safe areas", () => {
    assert.match(sharedNav, /min-h-\[3\.25rem\]/);
    assert.match(sharedNav, /var\(--app-bottom-inset\)/);
    assert.doesNotMatch(sharedNav, /\btruncate\b/);
    assert.match(shell, /<RoleWorkspaceShell/);
  });
});

describe("Parent workspace routes and screens", () => {
  const workspace = source("ParentWorkspace.tsx");
  const support = source("screens/SupportScreen.tsx");

  it("renders each destination as an independent feature", () => {
    for (const screen of [
      "HomeScreen",
      "UpdatesScreen",
      "ChildrenScreen",
      "PaymentsScreen",
      "SupportScreen",
    ]) {
      assert.match(workspace, new RegExp(`<${screen}`));
    }
  });

  it("keeps resolved tickets read-only with a new-ticket action", () => {
    assert.match(support, /ticket\.status === "resolved"/);
    assert.match(support, /\/parent\/support/);
    assert.match(support, /disabled=\{reply\.isPending\}/);
  });
});
