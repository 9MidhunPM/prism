export type ApiErrorStatus =
  | 0
  | 400
  | 401
  | 403
  | 404
  | 409
  | 422
  | 429
  | 500
  | 502
  | 503;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: ApiErrorStatus,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function toApiErrorStatus(status: number): ApiErrorStatus {
  switch (status) {
    case 400:
    case 401:
    case 403:
    case 404:
    case 409:
    case 422:
    case 429:
    case 500:
    case 502:
    case 503:
      return status;
    default:
      return 0;
  }
}

async function request<T>(
  path: `/api/${string}`,
  init?: RequestInit,
): Promise<T> {
  try {
    const headers = new Headers(init?.headers);
    if (init?.method && !["GET", "HEAD", "OPTIONS"].includes(init.method)) {
      const csrf = document.cookie
        .split("; ")
        .find((cookie) => cookie.startsWith("prism_csrf="))
        ?.split("=", 2)[1];
      if (csrf) headers.set("X-CSRF-Token", decodeURIComponent(csrf));
    }
    const response = await fetch(path, {
      ...init,
      headers,
      credentials: "include",
    });
    if (response.ok) {
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    }

    const body = await response.json().catch(() => null);
    throw new ApiError(
      body?.detail ?? "The request could not be completed.",
      toApiErrorStatus(response.status),
    );
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("Unable to reach PRISM. Please try again.", 0);
  }
}

export const api = {
  get: <T>(path: `/api/${string}`) => request<T>(path),
  post: <T>(path: `/api/${string}`, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      ...(body === undefined
        ? {}
        : {
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    }),
  patch: <T>(path: `/api/${string}`, body: unknown) =>
    request<T>(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  put: <T>(path: `/api/${string}`, body: unknown) =>
    request<T>(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  delete: <T>(path: `/api/${string}`) => request<T>(path, { method: "DELETE" }),
  request,
};
