const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Session state lives entirely in httpOnly cookies set by the backend
// (/auth/login, /auth/register, /auth/refresh) -- this file never reads or
// stores a token itself, so there's nothing here for an XSS bug to steal.
// `credentials: "include"` is what makes the browser attach those cookies
// on every request, including across the frontend/backend's two separate
// Vercel domains.

const AUTH_PATHS_WITHOUT_RETRY = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

// Access tokens are short-lived by design (see app/config.py); a single
// shared in-flight refresh call means concurrent 401s from several requests
// firing at once only trigger one /auth/refresh, not a stampede of them.
let refreshInFlight: Promise<boolean> | null = null;

function attemptRefresh(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${BASE_URL}/auth/refresh`, { method: "POST", credentials: "include" })
      .then((res) => res.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function parseErrorDetail(res: Response): Promise<string> {
  let detail: unknown = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail ?? JSON.stringify(body);
  } catch {
    // response wasn't JSON; fall back to statusText
  }
  return typeof detail === "string" ? detail : JSON.stringify(detail);
}

async function request<T>(path: string, init?: RequestInit, _retried = false): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (res.status === 401 && !_retried && !AUTH_PATHS_WITHOUT_RETRY.includes(path)) {
    const refreshed = await attemptRefresh();
    if (refreshed) return request<T>(path, init, true);
    window.dispatchEvent(new Event("auth:unauthorized"));
  }
  if (res.status === 403) {
    // Membership may have changed since the company list was last loaded
    // (e.g. a stale selection from another account on this browser) --
    // let CompanyContext refresh and drop the selection if it's gone.
    window.dispatchEvent(new Event("api:forbidden"));
  }
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorDetail(res));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

export function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return request<T>(path, { method: "POST", body: form });
}

// Downloads exports (Excel, PDFs, etc.) that return raw bytes rather than
// JSON -- fetches with the same cookie session as everything else, then
// triggers a browser save using the filename the server suggested via
// Content-Disposition, falling back to `fallbackFilename` if that header's
// missing (e.g. from an error response before the file was ever built).
export async function apiDownload(path: string, fallbackFilename: string, _retried = false): Promise<void> {
  const res = await fetch(`${BASE_URL}${path}`, { credentials: "include" });
  if (res.status === 401 && !_retried) {
    const refreshed = await attemptRefresh();
    if (refreshed) return apiDownload(path, fallbackFilename, true);
    window.dispatchEvent(new Event("auth:unauthorized"));
  }
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorDetail(res));
  }
  const disposition = res.headers.get("Content-Disposition");
  const match = disposition?.match(/filename="?([^";]+)"?/);
  const filename = match?.[1] ?? fallbackFilename;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
