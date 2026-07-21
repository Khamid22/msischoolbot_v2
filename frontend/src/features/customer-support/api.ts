import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders, XHR_HEADERS } from "@/shared/lib/api";

export type SupportRecordKind = "student" | "parent";

export type SupportRecordSummary = {
  kind: SupportRecordKind;
  id: number;
  display_name: string;
  secondary: string;
  phone?: string;
  telegram_username?: string;
  status: string;
  school_id?: number;
  school_name: string;
  version: number;
  outstanding: number;
  linked_count: number;
};

export type SupportContext = {
  schools: Array<{ id: number; school_key: string; school_name: string }>;
  allSchools: boolean;
  recordTypes: string[];
  statuses: string[];
  languages: string[];
  permissions: Record<string, boolean>;
};

export type SearchPayload = {
  items: SupportRecordSummary[];
  nextCursor?: string | null;
  hasMore: boolean;
};

export type StudentDetail = {
  kind: "student";
  profile: Record<string, unknown>;
  academic: Array<Record<string, unknown>>;
  parents: Array<Record<string, unknown>>;
  payments: PaymentPayload;
  activity: Array<Record<string, unknown>>;
};

export type ParentDetail = {
  kind: "parent";
  profile: Record<string, unknown>;
  children: Array<Record<string, unknown>>;
  hiddenChildCount: number;
  activity: Array<Record<string, unknown>>;
};

export type SupportDetail = StudentDetail | ParentDetail;

export type PaymentPayload = {
  items: Array<Record<string, unknown>>;
  totals: Record<string, number>;
  currency: string;
};

type ApiError = Error & { code?: string; details?: unknown; status?: number };

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!apiSucceeded(response, payload)) {
    const error = new Error(apiErrorMessage(payload, "The request could not be completed.")) as ApiError;
    const envelope = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
    error.code = String(envelope.code || "");
    error.details = envelope.details;
    error.status = response.status;
    throw error;
  }
  return apiData<T>(payload);
}

export async function getSupport<T>(path: string, signal?: AbortSignal) {
  const response = await fetch(`/api/v1/customer-support${path}`, {
    credentials: "same-origin",
    cache: "no-store",
    headers: XHR_HEADERS,
    signal,
  });
  return parseResponse<T>(response);
}

export async function sendSupport<T>(path: string, method: string, body: unknown, csrfToken: string) {
  const response = await fetch(`/api/v1/customer-support${path}`, {
    method,
    credentials: "same-origin",
    headers: jsonCsrfHeaders(csrfToken),
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export async function deleteSupport<T>(path: string, csrfToken: string) {
  const response = await fetch(`/api/v1/customer-support${path}`, {
    method: "DELETE",
    credentials: "same-origin",
    headers: jsonCsrfHeaders(csrfToken),
  });
  return parseResponse<T>(response);
}
