import { apiData, apiErrorMessage, apiSucceeded, jsonCsrfHeaders, XHR_HEADERS } from "@/shared/lib/api";
import type {
  SupportApiErrorDetails,
  SupportErrorCode,
  TeacherDetail,
  TeacherDirectoryPage,
} from "@/features/customer-support/model";

export * from "@/features/customer-support/model";

export class SupportApiError extends Error {
  code: SupportErrorCode;
  details?: SupportApiErrorDetails;
  status?: number;

  constructor(message: string, options: { code?: SupportErrorCode; details?: SupportApiErrorDetails; status?: number } = {}) {
    super(message);
    this.name = "SupportApiError";
    this.code = options.code || "customer_support_error";
    this.details = options.details;
    this.status = options.status;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!apiSucceeded(response, payload)) {
    const envelope = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
    throw new SupportApiError(apiErrorMessage(payload, "The request could not be completed."), {
      code: String(envelope.code || "customer_support_error"),
      details: envelope.details && typeof envelope.details === "object"
        ? envelope.details as SupportApiErrorDetails
        : undefined,
      status: response.status,
    });
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

export async function sendSupportForm<T>(
  path: string,
  formData: FormData,
  csrfToken: string,
) {
  const response = await fetch(`/api/v1/customer-support${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRF-Token": csrfToken,
    },
    body: formData,
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

export type TeacherDirectoryFilters = {
  query?: string;
  schoolId?: string;
  status?: string;
  cursor?: string | null;
  limit?: number;
};

export async function listSupportTeachers(
  filters: TeacherDirectoryFilters,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    status: filters.status || "all",
    limit: String(filters.limit || 25),
  });
  if (filters.query?.trim()) params.set("q", filters.query.trim());
  if (filters.schoolId) params.set("schoolId", filters.schoolId);
  if (filters.cursor) params.set("cursor", filters.cursor);
  return getSupport<TeacherDirectoryPage>(`/teachers?${params}`, signal);
}

export async function getSupportTeacher(
  teacherId: number,
  signal?: AbortSignal,
) {
  return getSupport<TeacherDetail>(`/teachers/${teacherId}`, signal);
}
