import {
  apiData,
  apiErrorMessage,
  apiSucceeded,
  jsonCsrfHeaders,
  XHR_HEADERS,
} from "@/shared/lib/api";

export class ParentApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status = 400, code = "parent_request_failed") {
    super(message);
    this.name = "ParentApiError";
    this.status = status;
    this.code = code;
  }
}

async function parse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!apiSucceeded(response, payload)) {
    const envelope = payload && typeof payload === "object"
      ? payload as Record<string, unknown>
      : {};
    throw new ParentApiError(
      apiErrorMessage(payload, "The request could not be completed."),
      response.status,
      String(envelope.code || "parent_request_failed"),
    );
  }
  return apiData<T>(payload);
}

export async function getParent<T>(path: string, signal?: AbortSignal) {
  const response = await fetch(`/api/v1/parent${path}`, {
    credentials: "same-origin",
    cache: "no-store",
    headers: XHR_HEADERS,
    signal,
  });
  return parse<T>(response);
}

export async function sendParent<T>(
  path: string,
  method: "POST" | "PATCH",
  body: unknown,
  csrfToken: string,
) {
  const response = await fetch(`/api/v1/parent${path}`, {
    method,
    credentials: "same-origin",
    headers: jsonCsrfHeaders(csrfToken),
    body: JSON.stringify(body),
  });
  return parse<T>(response);
}
