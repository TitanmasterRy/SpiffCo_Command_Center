import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from '../api/http';

/** Install a fake global fetch returning the given response shape. */
function mockFetch(response: { ok?: boolean; status?: number; jsonBody?: unknown }) {
  const fn = vi.fn(
    (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> =>
      Promise.resolve({
        ok: response.ok ?? true,
        status: response.status ?? 200,
        json: async () => response.jsonBody ?? {},
      } as unknown as Response),
  );
  globalThis.fetch = fn as unknown as typeof fetch;
  return fn;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('apiFetch header merge', () => {
  // Regression: init.headers (e.g. the admin Authorization bearer) must not
  // clobber the default Content-Type, or FastAPI can't parse the JSON body and
  // returns 422 on authenticated POST/PUT (e.g. POST /admin/execute).
  it('keeps Content-Type application/json when init supplies its own headers', async () => {
    const fetchMock = mockFetch({ ok: true, jsonBody: { ok: true } });

    await apiFetch('/api/v1/admin/execute', {
      method: 'POST',
      body: JSON.stringify({ action_id: 'player.fly', params: {} }),
      headers: { Authorization: 'Bearer test-token' },
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const init = fetchMock.mock.calls[0][1];
    const headers = init?.headers as Record<string, string>;
    expect(headers['Content-Type']).toBe('application/json');
    expect(headers.Authorization).toBe('Bearer test-token');
    expect(init?.method).toBe('POST');
  });

  it('throws ApiError carrying the backend error envelope on non-2xx', async () => {
    mockFetch({
      ok: false,
      status: 422,
      jsonBody: {
        error: { code: 'validation_failed', message: 'Request validation failed', details: {} },
      },
    });

    await expect(apiFetch('/x')).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetch('/x')).rejects.toMatchObject({ status: 422, code: 'validation_failed' });
  });
});
