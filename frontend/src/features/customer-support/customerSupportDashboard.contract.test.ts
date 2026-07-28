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

describe("Customer Support ticket queue", () => {
  const page = source("./tickets/TicketsPage.tsx");
  const filters = source("./tickets/TicketQueueFilters.tsx");
  const detail = source("./tickets/TicketDetailPanel.tsx");

  it("keeps only search and filter controls visible above the queue", () => {
    assert.match(filters, /role="search"/);
    assert.match(filters, /Search parent or ticket topic/);
    assert.match(filters, /aria-expanded=\{isOpen\}/);
    assert.match(filters, />Filter</);
    assert.equal((page.match(/<select/g) || []).length, 0);
    assert.doesNotMatch(page, /ShieldCheck/);
  });

  it("uses a compact dismissible filter popover with active-filter feedback", () => {
    assert.match(filters, /useDismissibleLayer/);
    assert.match(filters, /role="dialog"/);
    assert.match(filters, /w-\[min\(22rem,calc\(100vw-2rem\)\)\]/);
    assert.match(filters, /activeFilterCount/);
    assert.match(filters, /Results update immediately/);
    assert.match(filters, /Reset/);
  });

  it("searches while typing and preserves URL-backed queue filters", () => {
    assert.match(page, /window\.setTimeout\(\(\) =>/);
    assert.match(page, /}, 300\)/);
    assert.match(page, /params\.set\("q", search\)/);
    assert.match(page, /params\.set\("slaState", slaState\)/);
    assert.match(page, /params\.set\("assignedToMe", "true"\)/);
  });

  it("limits an open ticket to flag, escalate, and resolve actions", () => {
    assert.match(detail, /aria-label="Flag ticket priority"/);
    assert.match(detail, /label: "Escalate"/);
    assert.match(detail, /label: "Resolve"/);
    assert.doesNotMatch(detail, /label: "Start work"/);
    assert.doesNotMatch(detail, /Assign to me|UserCheck|UserMinus/);
    assert.doesNotMatch(detail, /Waiting on parent|Resume SLA/);
    assert.doesNotMatch(detail, /\/assignment|\/waiting-state/);
  });
});
