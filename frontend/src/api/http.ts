import { useAuthStore } from '../stores/authStore';
import type { ApiErrorBody } from '../types/api';

/** Error thrown for any non-2xx API response, carrying the backend error code. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody['error']) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }
}

/**
 * Thin typed wrapper over `fetch` for the backend API.
 * All paths are relative (`/api/v1/...`) — the dev server / nginx proxies them.
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token;
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    // An expired/forged token: drop the stale session so route guards send the
    // user back to login. Harmless when there was no session (e.g. a bad login).
    if (response.status === 401) useAuthStore.getState().clearSession();

    let errorBody: ApiErrorBody['error'] = {
      code: 'unknown_error',
      message: `Request failed with status ${response.status}`,
      details: {},
    };
    try {
      const parsed = (await response.json()) as ApiErrorBody;
      if (parsed?.error) errorBody = parsed.error;
    } catch {
      // Non-JSON error body — keep the fallback.
    }
    throw new ApiError(response.status, errorBody);
  }

  // 204 No Content (e.g. DELETE) has no body to parse.
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
