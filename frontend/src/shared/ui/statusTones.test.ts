import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { normalizeStatus, statusLabel, statusTone, statusToneMap } from "./statusTones.ts";

const requiredStatuses = [
  "Active",
  "In Training",
  "In Academy",
  "Ready",
  "Completed",
  "Needs Support",
  "Scheduled",
  "Assigned",
  "Assessed",
  "Draft",
  "Published",
  "Missing",
  "Trash Bin",
];

describe("statusToneMap", () => {
  it("defines a tone for every status StatusBadge must support", () => {
    for (const label of requiredStatuses) {
      const key = normalizeStatus(label);
      assert.ok(key in statusToneMap, `missing tone for status "${label}" (key "${key}")`);
    }
  });

  it("uses only tones Badge understands", () => {
    const allowed = new Set(["neutral", "success", "warning", "danger", "info"]);
    for (const [key, tone] of Object.entries(statusToneMap)) {
      assert.ok(allowed.has(tone), `unknown tone "${tone}" for status "${key}"`);
    }
  });
});

describe("statusLabel", () => {
  it("round-trips every required status to its display label", () => {
    for (const label of requiredStatuses) {
      assert.equal(statusLabel(label), label);
      assert.equal(statusLabel(normalizeStatus(label)), label);
    }
  });

  it("passes unknown statuses through untouched", () => {
    assert.equal(statusLabel("Custom Thing"), "Custom Thing");
  });
});

describe("statusTone", () => {
  it("normalizes spacing, dashes, and case", () => {
    assert.equal(statusTone("In Training"), statusTone("in_training"));
    assert.equal(statusTone("needs-support"), statusTone("Needs Support"));
    assert.equal(statusTone("MISSING"), "danger");
  });

  it("falls back to neutral for unknown statuses", () => {
    assert.equal(statusTone("banana"), "neutral");
  });
});
