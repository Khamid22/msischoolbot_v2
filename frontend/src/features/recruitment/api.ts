import { apiData, apiErrorMessage, apiSucceeded, XHR_HEADERS } from "@/shared/lib/api";

export async function recruitmentRequest<T>(url: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const response = await fetch(url, {
    credentials: "same-origin",
    cache: "no-store",
    ...init,
    headers: {
      ...XHR_HEADERS,
      ...(isForm ? {} : init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!apiSucceeded(response, payload)) {
    const error = new Error(apiErrorMessage(payload, "Unable to complete the recruitment request."));
    const detail = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
    Object.assign(error, { status: response.status, code: detail.code, details: detail.details });
    throw error;
  }
  return apiData<T>(payload);
}

export function jsonBody(value: unknown) {
  return JSON.stringify(value);
}

export function appointmentConflictDetails<T = Record<string, unknown>>(error: unknown): T[] {
  if (!error || typeof error !== "object") return [];
  const candidate = error as { code?: unknown; details?: unknown };
  return candidate.code === "appointment_conflict" && Array.isArray(candidate.details)
    ? candidate.details as T[]
    : [];
}

export function formValues(form: HTMLFormElement): Record<string, string | number | null> {
  const values: Record<string, string | number | null> = {};
  new FormData(form).forEach((value, key) => {
    const text = String(value).trim();
    values[key] = text;
  });
  return values;
}
