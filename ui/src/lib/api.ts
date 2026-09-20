import type {
  ApplicationDetail,
  DecideResponse,
  HumanDecision,
  QueueResponse,
  Stats,
} from "./types";

/**
 * Auth-readiness: when the app later sits behind Keycloak OIDC, register a
 * token getter with setTokenProvider() and every request will carry
 * `Authorization: Bearer <token>`. Until then, no header is attached.
 */
export type TokenProvider = () => string | null | Promise<string | null>;

let tokenProvider: TokenProvider | null = null;

export function setTokenProvider(fn: TokenProvider | null): void {
  tokenProvider = fn;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Single fetch wrapper — every API call in the app goes through this. */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (tokenProvider !== null) {
    const token = await tokenProvider();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "Could not reach the Duta API.");
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body: unknown = await response.json();
      if (
        typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        typeof (body as { detail: unknown }).detail === "string"
      ) {
        message = (body as { detail: string }).detail;
      }
    } catch {
      // non-JSON error body — keep the status message
    }
    throw new ApiError(response.status, message);
  }

  return (await response.json()) as T;
}

export const api = {
  stats: (): Promise<Stats> => request<Stats>("/api/stats"),

  queue: (status = "open", limit = 100): Promise<QueueResponse> =>
    request<QueueResponse>(
      `/api/queue?status=${encodeURIComponent(status)}&limit=${limit}`,
    ),

  application: (applicationId: number | string): Promise<ApplicationDetail> =>
    request<ApplicationDetail>(`/api/applications/${applicationId}`),

  decide: (
    queueItemId: number,
    body: { decision: HumanDecision; actor: string; note: string },
  ): Promise<DecideResponse> =>
    request<DecideResponse>(`/api/queue/${queueItemId}/decide`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
