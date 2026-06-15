// Typed client for the WebHawk backend API.
//
// In dev, Vite proxies `/api/*` to the FastAPI service (see vite.config.ts), so
// the browser only ever talks to its own origin. In production a reverse proxy
// fronts both under the same origin, so the relative `/api` base works there too.

const API_BASE = '/api';

/** Shape of the backend `GET /health` response. Mirrors `HealthResponse` in
 * `backend/app/api/health.py`. */
export interface Health {
  status: string;
  version: string;
  uptime_seconds: number;
}

/** Error thrown for non-2xx responses, carrying the HTTP status for callers. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: 'application/json' },
      ...init,
    });
  } catch (cause) {
    // Network-level failure (backend down, DNS, CORS, offline, …).
    throw new ApiError(0, `Network error: ${(cause as Error).message}`);
  }

  if (!res.ok) {
    throw new ApiError(res.status, `Request to ${path} failed (${res.status})`);
  }

  return (await res.json()) as T;
}

/** Fetch backend liveness/version info. */
export function getHealth(signal?: AbortSignal): Promise<Health> {
  return request<Health>('/health', { signal });
}
