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
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });

  if (!response.ok) {
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

  return (await response.json()) as T;
}
