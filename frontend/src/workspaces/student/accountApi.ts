import {
  apiData,
  apiErrorMessage,
  apiSucceeded,
  jsonCsrfHeaders,
  XHR_HEADERS,
} from "@/shared/lib/api";

async function parse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!apiSucceeded(response, payload)) {
    throw new Error(apiErrorMessage(payload, "The request could not be completed."));
  }
  return apiData<T>(payload);
}

export async function getStudent<T>(path: string, signal?: AbortSignal) {
  const response = await fetch(`/api/v1/student${path}`, {
    credentials: "same-origin",
    cache: "no-store",
    headers: XHR_HEADERS,
    signal,
  });
  return parse<T>(response);
}

export async function sendStudent<T>(
  path: string,
  method: "POST",
  body: unknown,
  csrfToken: string,
) {
  const response = await fetch(`/api/v1/student${path}`, {
    method,
    credentials: "same-origin",
    headers: jsonCsrfHeaders(csrfToken),
    body: JSON.stringify(body),
  });
  return parse<T>(response);
}
