import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  activeNavKeyFromPath,
  mobileNavItemsFrom,
  normalizeNavPathname,
  type RoleNavItem,
} from "./roleNav.ts";

const icon = (() => null) as unknown as RoleNavItem["icon"];

const items: ReadonlyArray<RoleNavItem<"overview" | "academy" | "departments" | "profile">> = [
  { key: "overview", label: "Overview", href: "/role", icon },
  { key: "academy", label: "Teacher Academy", mobileLabel: "Academy", href: "/role/teacher-academy", icon },
  { key: "departments", label: "Head of Departments", href: "/role/head-of-departments", icon },
  { key: "profile", label: "Profile", href: "/role/profile", icon },
];

describe("mobileNavItemsFrom", () => {
  it("swaps in short mobile labels and keeps the rest", () => {
    const mobile = mobileNavItemsFrom(items);
    assert.deepEqual(
      mobile.map((item) => item.label),
      ["Overview", "Academy", "Head of Departments", "Profile"],
    );
  });

  it("drops excluded keys for phone layouts", () => {
    const mobile = mobileNavItemsFrom(items, ["departments"]);
    assert.deepEqual(
      mobile.map((item) => item.key),
      ["overview", "academy", "profile"],
    );
  });
});

describe("normalizeNavPathname", () => {
  it("strips query strings and trailing slashes", () => {
    assert.equal(normalizeNavPathname("/role/teacher-academy/?tab=1"), "/role/teacher-academy");
    assert.equal(normalizeNavPathname("/role///"), "/role");
    assert.equal(normalizeNavPathname(""), "/");
  });
});

describe("activeNavKeyFromPath", () => {
  it("matches the exact item for each href", () => {
    for (const item of items) {
      assert.equal(activeNavKeyFromPath(items, item.href, "overview"), item.key);
    }
  });

  it("prefers the longest href so subpages beat the overview", () => {
    assert.equal(activeNavKeyFromPath(items, "/role/teacher-academy", "overview"), "academy");
  });

  it("falls back for unknown paths", () => {
    assert.equal(activeNavKeyFromPath(items, "/somewhere-else", "overview"), "overview");
  });

  it("ignores query strings and trailing slashes", () => {
    assert.equal(activeNavKeyFromPath(items, "/role/profile/?from=nav", "overview"), "profile");
  });
});
