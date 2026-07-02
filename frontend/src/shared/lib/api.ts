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
