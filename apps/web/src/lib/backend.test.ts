// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv('BACKEND_URL', 'https://backend.example.test');
  vi.stubGlobal('fetch', fetchMock.mockReset());
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('backendRequest', () => {
  it('menerapkan timeout opsional tanpa memperlebar permintaan lain', async () => {
    const { backendRequest } = await import('./backend');
    const timeout = vi.spyOn(AbortSignal, 'timeout');
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ data: { reply: 'Halo' } }) });
    await expect(
      backendRequest('/chat', {
        method: 'POST',
        timeoutMs: 100_000,
        token: 'test-token',
        body: '{"message":"Halo"}',
      }),
    ).resolves.toEqual({ reply: 'Halo' });
    expect(timeout).toHaveBeenCalledWith(100_000);
    expect(fetchMock).toHaveBeenCalledWith(
      'https://backend.example.test/api/chat',
      expect.objectContaining({
        signal: expect.any(AbortSignal),
        cache: 'no-store',
        headers: expect.objectContaining({ authorization: 'Bearer test-token' }),
      }),
    );
    expect(fetchMock.mock.calls[0][1]).not.toHaveProperty('timeoutMs');
    timeout.mockClear();
    await backendRequest('/services');
    expect(timeout).not.toHaveBeenCalled();
    expect(fetchMock.mock.calls[1][1].signal).toBeUndefined();
  });

  it('membatalkan fetch yang menggantung saat deadline tercapai', async () => {
    const { backendRequest } = await import('./backend');
    fetchMock.mockImplementationOnce(
      (_url, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () => reject(init.signal?.reason), { once: true });
        }),
    );
    await expect(backendRequest('/chat', { timeoutMs: 10 })).rejects.toMatchObject({ status: 504 });
  });

  it('menggabungkan pembatalan caller dengan deadline', async () => {
    const { backendRequest } = await import('./backend');
    const controller = new AbortController();
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ data: [] }) });
    await backendRequest('/chat', { timeoutMs: 100_000, signal: controller.signal });
    const signal = fetchMock.mock.calls[0][1].signal as AbortSignal;
    controller.abort();
    expect(signal.aborted).toBe(true);
  });

  it.each(['AbortError', 'TimeoutError'])('mengubah %s menjadi ApiError 504', async (name) => {
    const { ApiError, backendRequest } = await import('./backend');
    fetchMock.mockRejectedValueOnce(new DOMException('expired', name));
    const result = backendRequest('/chat', { timeoutMs: 100_000 });
    await expect(result).rejects.toBeInstanceOf(ApiError);
    await expect(result).rejects.toMatchObject({ status: 504 });
  });

  it('tidak menelan deadline saat membaca response body', async () => {
    const { backendRequest } = await import('./backend');
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => {
        throw new DOMException('expired', 'AbortError');
      },
    });
    await expect(backendRequest('/chat', { timeoutMs: 100_000 })).rejects.toMatchObject({
      status: 504,
    });
  });

  it('mempertahankan status dan detail upstream serta tidak menyamarkan error jaringan sebagai timeout', async () => {
    const { backendRequest } = await import('./backend');
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 429,
      json: async () => ({ title: 'Terlalu sering', detail: 'Coba nanti.' }),
    });
    await expect(backendRequest('/chat')).rejects.toMatchObject({
      status: 429,
      detail: 'Coba nanti.',
    });
    fetchMock.mockRejectedValueOnce(new TypeError('offline'));
    await expect(backendRequest('/chat')).rejects.toBeInstanceOf(TypeError);
  });
});

describe('routeError', () => {
  it('menghasilkan Problem Details untuk error biasa dan timeout', async () => {
    const { problem, routeError } = await import('./backend');
    const response = routeError(problem(503, 'Fitur belum tersedia', 'Gunakan chat teks.'));
    expect(response.status).toBe(503);
    expect(response.headers.get('content-type')).toBe('application/problem+json');
    expect(await response.json()).toEqual({
      type: 'about:blank#503',
      status: 503,
      title: 'Fitur belum tersedia',
      detail: 'Gunakan chat teks.',
    });
    expect(routeError(new DOMException('expired', 'TimeoutError')).status).toBe(504);
    const internal = routeError(new Error('private failure'));
    expect(internal.status).toBe(500);
    expect(internal.headers.get('content-type')).toBe('application/problem+json');
    expect(await internal.text()).not.toContain('private failure');
  });
});
