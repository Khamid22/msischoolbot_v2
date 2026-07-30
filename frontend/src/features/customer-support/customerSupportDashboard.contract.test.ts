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
    assert.match(page, /window\.history\.pushState/);
    assert.match(page, /window\.addEventListener\("popstate"/);
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

describe("Customer Support admissions and payments", () => {
  const workspace = source("./CustomerSupportWorkspace.tsx");
  const admissions = source("./admissions/AdmissionsPage.tsx");
  const detail = source("./admissions/AdmissionDetailPanel.tsx");
  const wizard = source("./admissions/AdmissionWizard.tsx");
  const payments = source("./payments/PaymentsPage.tsx");
  const paymentLocation = source("./payments/paymentLocation.ts");
  const billingProfile = source("./students/BillingProfileDialog.tsx");
  const students = source("./students/StudentsPage.tsx");
  const publicAdmission = source("../../workspaces/public_admission/pages/Admission.tsx");

  it("registers focused admission and two-view payment workspaces", () => {
    assert.match(workspace, /<AdmissionsPage/);
    assert.match(workspace, /<PaymentsPage/);
    assert.match(admissions, /Admission queue/);
    assert.match(payments, /Billing Accounts/);
    assert.match(payments, /Invoices\s*<\/PaymentViewButton>/);
    assert.match(payments, /params\.set\("view", view\)/);
  });

  it("derives subjects from school-scoped groups and keeps amounts in minor units", () => {
    assert.match(wizard, /Subjects are derived from the selected groups/);
    assert.match(wizard, /monthlyAmountMinor: Math\.round\(amountUzs \* 100\)/);
    assert.match(wizard, /Select only one group for each subject/);
  });

  it("supports contract review, manual settlement, atomic paid invoices, and audit history", () => {
    assert.match(detail, /Accept and issue invoice/);
    assert.match(detail, /Record manual payment/);
    assert.match(detail, /Add paid invoice and activate/);
    assert.match(detail, /Audit history/);
    assert.match(admissions, /\/paid-invoice/);
    assert.match(admissions, /\/manual-payment/);
  });

  it("uses the unified ledger for current students and recurring billing", () => {
    assert.match(students, /paid-invoices/);
    assert.match(students, /expectedStudentVersion/);
    assert.doesNotMatch(students, /Mark unpaid/);
    assert.match(billingProfile, /billing-profile/);
    assert.match(billingProfile, /Monthly amount in UZS/);
    assert.match(payments, /invoice-payments\/\$\{paymentId\}\/reversal/);
    assert.match(payments, /\/payments\/billing-accounts/);
    assert.match(source("./payments/BillingAccountDetailPanel.tsx"), /Save schedule/);
  });

  it("defaults to billing accounts and exposes semantic desktop tables with mobile cards", () => {
    const accountList = source("./payments/BillingAccountList.tsx");
    const invoiceList = source("./payments/InvoiceList.tsx");
    const filters = source("./payments/PaymentFilters.tsx");
    assert.match(paymentLocation, /params\.get\("view"\) === "invoices"/);
    assert.match(paymentLocation, /!params\.has\("view"\) && selectedInvoiceId/);
    assert.match(accountList, /<table/);
    assert.match(accountList, /xl:hidden/);
    assert.match(invoiceList, /<table/);
    assert.match(filters, /role="search"/);
    assert.match(filters, />Filter</);
    assert.match(filters, /role="dialog"/);
  });

  it("keeps Payme confirmation out of the browser callback", () => {
    assert.match(publicAdmission, /account\[invoice_id\]/);
    assert.match(publicAdmission, /method="POST"/);
    assert.match(publicAdmission, /action=\{data\.checkoutUrl\}/);
    assert.doesNotMatch(publicAdmission, /confirmPayment|performTransaction/);
    assert.match(publicAdmission, /mutation\.isError/);
  });
});

describe("Customer Support master-detail reliability", () => {
  const layout = source("./shared/MasterDetailLayout.tsx");
  const supportLayout = source("./shared/SupportPageLayout.tsx");
  const admissions = source("./admissions/AdmissionsPage.tsx");
  const payments = source("./payments/PaymentsPage.tsx");
  const automation = source("./payments/AutomationStatusPanel.tsx");
  const invoiceDetail = source("./payments/InvoiceDetailPanel.tsx");
  const teachers = source("./teachers/TeachersPage.tsx");
  const tickets = source("./tickets/TicketsPage.tsx");

  it("uses one collection-state decision across all six master-detail pages", () => {
    assert.match(layout, /itemCount > 0/);
    assert.match(layout, /if \(isLoading\)/);
    assert.match(layout, /if \(isError\)/);
    assert.match(layout, /collectionState !== "ready"/);
    assert.match(supportLayout, /MasterDetailLayout/);
    assert.match(admissions, /MasterDetailLayout/);
    assert.match(payments, /MasterDetailLayout/);
    assert.match(teachers, /MasterDetailLayout/);
    assert.match(tickets, /MasterDetailLayout/);
  });

  it("shows only the collection or detail on mobile and splits at lg", () => {
    assert.match(layout, /isDetailOpen \? "hidden lg:block" : "block"/);
    assert.match(layout, /isDetailOpen \? "block" : "hidden lg:block"/);
    assert.match(layout, /lg:grid-cols/);
    assert.match(admissions, /Back to admissions/);
    assert.match(payments, /Back to \{view === "accounts" \? "accounts" : "invoices"\}/);
  });

  it("exposes billing automation and privacy-safe notification results", () => {
    assert.match(payments, /\/payments\/automation-status/);
    assert.match(automation, /Billing automation/);
    assert.match(invoiceDetail, /Notification timeline/);
    assert.match(invoiceDetail, /without exposing Telegram identifiers/);
    assert.match(automation, /Worker \{status\.workerState/);
    assert.match(automation, /status\.openInvoices/);
    assert.match(automation, /status\.pendingFinanceJobs/);
    assert.match(automation, /status\.lastSuccessfulFinanceWorkerAt/);
    assert.match(automation, /<details/);
  });
});
