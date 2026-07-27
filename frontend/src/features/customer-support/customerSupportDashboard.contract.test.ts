import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

function source(relativePath: string) {
  return readFileSync(new URL(relativePath, import.meta.url), "utf8");
}

describe("Customer Support operational dashboard", () => {
  const workspace = source("./CustomerSupportWorkspace.tsx");
  const page = source("./dashboard/DashboardPage.tsx");
  const charts = source("./dashboard/DashboardCharts.tsx");
  const panels = source("./dashboard/DashboardPanels.tsx");

  it("replaces the placeholder with the real dashboard and six attention metrics", () => {
    assert.match(workspace, /DashboardPage/);
    assert.doesNotMatch(workspace, /DashboardPlaceholder/);
    assert.equal((page.match(/<MetricLink/g) || []).length, 6);
    for (const label of [
      "Open tickets",
      "Assigned to me",
      "Unassigned",
      "SLA breached",
      "Overdue accounts",
      "No parent link",
    ]) {
      assert.match(page, new RegExp(label));
    }
  });

  it("keeps drill-down filters in URLs", () => {
    assert.match(page, /assignedToMe=true/);
    assert.match(page, /unassigned=true/);
    assert.match(page, /slaState=breached/);
    assert.match(panels, /tickets\?ticketId=/);
    assert.match(panels, /students\?recordId=/);
  });

  it("provides accessible chart labels, exact tooltips, and data tables", () => {
    assert.match(charts, /accessibilityLayer/);
    assert.match(charts, /<Tooltip/);
    assert.match(charts, /<Legend/);
    assert.match(charts, /View chart data/);
    assert.match(charts, /<table/);
    assert.match(charts, /isAnimationActive=\{false\}/);
  });

  it("orders action and exception panels before charts", () => {
    const actionIndex = page.indexOf("<ActionRequiredPanel");
    const exceptionIndex = page.indexOf("<ExceptionPanels");
    const chartIndex = page.indexOf("<TicketFlowChart");
    assert.ok(actionIndex > 0 && exceptionIndex > actionIndex && chartIndex > exceptionIndex);
  });
});
