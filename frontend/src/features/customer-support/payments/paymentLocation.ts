import type {
  AccountFilters,
  InvoiceFilters,
  PaymentView,
} from "@/features/customer-support/payments/PaymentFilters";

export type PaymentLocation = {
  view: PaymentView;
  search: string;
  selectedAccountType: "student" | "admission" | null;
  selectedAccountId: number | null;
  selectedInvoiceId: number | null;
  accountFilters: AccountFilters;
  invoiceFilters: InvoiceFilters;
};

export const DEFAULT_ACCOUNT_FILTERS: AccountFilters = {
  schoolId: "",
  accountType: "all",
  scheduleStatus: "all",
  attention: "all",
  access: "all",
};

export const DEFAULT_INVOICE_FILTERS: InvoiceFilters = {
  schoolId: "",
  status: "all",
  origin: "all",
  billingPeriod: "",
  access: "all",
};

export function readPaymentLocation(): PaymentLocation {
  const params = new URLSearchParams(window.location.search);
  const accountType = params.get("accountType");
  const selectedInvoiceId = Number(params.get("invoiceId") || 0) || null;
  return {
    view: params.get("view") === "invoices" || (!params.has("view") && selectedInvoiceId)
      ? "invoices"
      : "accounts",
    search: params.get("q") || "",
    selectedAccountType: accountType === "student" || accountType === "admission"
      ? accountType
      : null,
    selectedAccountId: Number(params.get("accountId") || 0) || null,
    selectedInvoiceId,
    accountFilters: {
      schoolId: params.get("schoolId") || "",
      accountType: params.get("type") || "all",
      scheduleStatus: params.get("scheduleStatus") || "all",
      attention: params.get("attention") || "all",
      access: params.get("access") || "all",
    },
    invoiceFilters: {
      schoolId: params.get("schoolId") || "",
      status: params.get("status") || "all",
      origin: params.get("origin") || "all",
      billingPeriod: params.get("billingPeriod") || "",
      access: params.get("access") || "all",
    },
  };
}

export function billingAccountKey(
  accountType: string | null,
  accountId: number | null,
) {
  return accountType && accountId ? `${accountType}:${accountId}` : null;
}
