import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { densityRem, renderedDensityPixels } from "./uiDensity.ts";

describe("desktop interface density helpers", () => {
  it("converts legacy design pixels to rem without rounding drift", () => {
    assert.equal(densityRem(16), "1rem");
    assert.equal(densityRem(44), "2.75rem");
    assert.equal(densityRem(-8), "-0.5rem");
  });

  it("retains design pixels when no browser document is available", () => {
    assert.equal(renderedDensityPixels(48), 48);
  });
});
