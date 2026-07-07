/**
 * Shared request headers for same-origin API calls.
 *
 * The backend's security middleware requires the XMLHttpRequest marker on
 * JSON/XHR calls (see AuthAndSecurityMiddleware) — a cross-site page cannot
 * set this header without a CORS preflight, so it doubles as a CSRF guard.
 */
export const XHR_HEADERS = { "X-Requested-With": "XMLHttpRequest" } as const;

export const JSON_HEADERS = {
  "Content-Type": "application/json",
  ...XHR_HEADERS,
} as const;

type ApiEnvelope = {
  status?: unknown;
  data?: unknown;
  message?: unknown;
  detail?: unknown;
  ok?: unknown;
};

function asEnvelope(value: unknown): ApiEnvelope {
  return value && typeof value === "object" ? (value as ApiEnvelope) : {};
}

/** Unwrap the standard `{ status: "success", data }` envelope while accepting legacy payloads. */
export function apiData<T = Record<string, unknown>>(payload: unknown): T {
  const envelope = asEnvelope(payload);
  if (envelope.status === "success" && "data" in envelope) {
    return envelope.data as T;
  }
  return payload as T;
}

/** True for HTTP success and either the v1 success envelope or a non-failing legacy payload. */
export function apiSucceeded(response: Response, payload: unknown) {
  const envelope = asEnvelope(payload);
  if (envelope.status === "error" || envelope.ok === false) {
    return false;
  }
  if (envelope.status === "success") {
    return response.ok;
  }
  return response.ok;
}

export function apiErrorMessage(payload: unknown, fallback: string) {
  const envelope = asEnvelope(payload);
  return String(envelope.message || envelope.detail || fallback);
}

/** XHR marker + session CSRF token (for non-JSON mutations, e.g. FormData/DELETE). */
export function csrfHeaders(csrfToken: string) {
  return { ...XHR_HEADERS, "X-CSRFToken": csrfToken };
}

/** JSON + XHR marker + session CSRF token, for JSON mutations. */
export function jsonCsrfHeaders(csrfToken: string) {
  return { ...JSON_HEADERS, "X-CSRFToken": csrfToken };
}

/** GET a same-origin endpoint with the XHR marker. */
export function apiGet(url: string, init: RequestInit = {}) {
  return fetch(url, { ...init, headers: { ...XHR_HEADERS, ...(init.headers || {}) } });
}

/** Send a JSON body (POST/PATCH/PUT/DELETE) with the XHR marker. */
export function apiSend(url: string, method: string, body?: unknown, init: RequestInit = {}) {
  return fetch(url, {
    ...init,
    method,
    headers: { ...JSON_HEADERS, ...(init.headers || {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
