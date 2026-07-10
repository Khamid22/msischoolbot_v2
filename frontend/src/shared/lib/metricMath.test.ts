import test from "node:test";
import assert from "node:assert/strict";
import { averageRecordedMetrics, finiteMetricOrNull } from "./metricMath.ts";

test("finiteMetricOrNull preserves explicit zero and rejects missing values", () => {
  assert.equal(finiteMetricOrNull(0), 0);
  assert.equal(finiteMetricOrNull("0"), 0);
  assert.equal(finiteMetricOrNull(null), null);
  assert.equal(finiteMetricOrNull(""), null);
  assert.equal(finiteMetricOrNull("not-a-score"), null);
});

test("averageRecordedMetrics includes zero without inventing missing scores", () => {
  assert.equal(averageRecordedMetrics([0, 6, 9]), 5);
  assert.equal(averageRecordedMetrics([0, null, "", undefined]), 0);
  assert.equal(averageRecordedMetrics([null, "", undefined]), null);
});
