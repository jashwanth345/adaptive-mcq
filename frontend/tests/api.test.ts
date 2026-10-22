import { describe, expect, it, vi } from 'vitest';
import { ApiError, errorMessage, request } from '../src/api';
import { localOrigin } from '../local-origin';

describe('local API boundary', () => {
  it.each(['https://cloud.example', 'http://localhost:8000/api', 'http://user:secret@127.0.0.1:8000', 'http://127.0.0.1:8000?redirect=x', 'http://192.168.1.2:8000'])('rejects nonlocal or decorated targets: %s', (value) => expect(() => localOrigin(value)).toThrow());
  it('accepts a clean loopback origin', () => expect(localOrigin('http://127.0.0.1:8000')).toBe('http://127.0.0.1:8000'));
  it('keeps credentials same-origin, out of URLs and without cookies/redirects', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 })); vi.stubGlobal('fetch', fetcher);
    await request('/auth/login', { body: { email: 'x@example.com', password: ' keep my spaces ' } });
    expect(fetcher).toHaveBeenCalledWith('/api/v1/auth/login', expect.objectContaining({ method: 'POST', credentials: 'omit', redirect: 'error', cache: 'no-store', body: JSON.stringify({ email: 'x@example.com', password: ' keep my spaces ' }) }));
    await expect(request('https://other.example/auth/login')).rejects.toThrow('Unsupported API path'); expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('handles an empty logout response', async () => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 }))); expect(await request('/auth/logout', { method: 'POST', token: 'fixture' })).toBeUndefined(); });
  it('preserves safe request identifiers and rate-limit delay without echoing server input', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'RATE_LIMITED', message: 'private echoed input' } }), { status: 429, headers: { 'Retry-After': '120', 'X-Request-ID': 'fixture-id' } })));
    try { await request('/auth/login', { body: {} }); throw new Error('should fail'); } catch (error) { expect(error).toMatchObject({ status: 429, retryAfter: 120, requestId: 'fixture-id' }); expect(errorMessage(error)).toContain('2 minute(s)'); expect(errorMessage(error)).not.toContain('private'); }
  });
  it('handles non-JSON gateway errors', async () => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('unavailable', { status: 503 }))); await expect(request('/auth/me')).rejects.toMatchObject({ status: 503 }); });
  it('explains a network failure', async () => { vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('fetch failed'))); await expect(request('/auth/me')).rejects.toMatchObject({ code: 'UNREACHABLE' }); expect(errorMessage(new ApiError(0, 'UNREACHABLE'))).toContain('Start the backend'); });
  it('aborts requests that time out', async () => {
    vi.useFakeTimers(); vi.stubGlobal('fetch', vi.fn((_url, init: RequestInit) => new Promise((_resolve, reject) => init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))))));
    const result = expect(request('/auth/me')).rejects.toMatchObject({ code: 'TIMEOUT' }); await vi.advanceTimersByTimeAsync(15001); await result;
  });
  it('distinguishes caller cancellation from connection errors', async () => {
    vi.stubGlobal('fetch', vi.fn((_url, init: RequestInit) => new Promise((_resolve, reject) => init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))))));
    const controller = new AbortController(); const result = expect(request('/auth/me', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' }); controller.abort(); await result;
  });
});
