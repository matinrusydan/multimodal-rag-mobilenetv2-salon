// @vitest-environment node
import { NextRequest } from 'next/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { getSession } = vi.hoisted(() => ({ getSession: vi.fn() }));
vi.mock('@/lib/web-session', () => ({ getSession }));

const fetchMock = vi.fn();

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv('BACKEND_URL', 'https://backend.example.test');
  vi.stubGlobal('fetch', fetchMock.mockReset());
  getSession.mockReset().mockResolvedValue({ token: 'test-token' });
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('/api/analyze', () => {
  it('mengembalikan 503 tanpa membaca body atau menghubungi layanan', async () => {
    const { POST } = await import('./analyze/route');
    const request = {
      formData: vi.fn(() => {
        throw new Error('must not parse');
      }),
      json: vi.fn(() => {
        throw new Error('must not parse');
      }),
      text: vi.fn(() => {
        throw new Error('must not parse');
      }),
    };
    const response = await Reflect.apply(POST, undefined, [request]);
    expect(response.status).toBe(503);
    expect(response.headers.get('content-type')).toBe('application/problem+json');
    expect(await response.json()).toEqual({
      type: 'about:blank#503',
      status: 503,
      title: 'Fitur belum tersedia',
      detail: 'Analisis foto belum tersedia. Silakan gunakan konsultasi teks.',
    });
    expect(request.formData).not.toHaveBeenCalled();
    expect(request.json).not.toHaveBeenCalled();
    expect(request.text).not.toHaveBeenCalled();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(getSession).not.toHaveBeenCalled();
  });
});

describe('/api/chat', () => {
  it('meneruskan chat dan contextId dengan deadline di atas 90 detik', async () => {
    const { POST, maxDuration } = await import('./chat/route');
    const timeout = vi.spyOn(AbortSignal, 'timeout');
    const data = { reply: 'Halo', contextId: 'next-context', sources: [{ file: 'care.md' }] };
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ data }) });
    const request = new NextRequest('https://web.example.test/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message: 'Halo', contextId: 'old-context' }),
    });
    const response = await POST(request);
    expect(await response.json()).toEqual({ ok: true, data });
    expect(timeout).toHaveBeenCalledWith(100_000);
    expect(maxDuration).toBe(120);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      message: 'Halo',
      contextId: 'old-context',
    });
    expect(fetchMock.mock.calls[0][0]).toBe('https://backend.example.test/api/chat');
  });

  it('mempertahankan validasi pesan kosong dan status upstream', async () => {
    const { POST } = await import('./chat/route');
    const empty = await POST(
      new NextRequest('https://web.example.test/api/chat', {
        method: 'POST',
        body: '{}',
      }),
    );
    expect(empty.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 429,
      json: async () => ({ title: 'Terlalu sering', detail: 'Coba nanti.' }),
    });
    const limited = await POST(
      new NextRequest('https://web.example.test/api/chat', {
        method: 'POST',
        body: '{"message":"Halo"}',
      }),
    );
    expect(limited.status).toBe(429);
    expect(await limited.json()).toMatchObject({ detail: 'Coba nanti.' });
  });

  it('mengembalikan 504 Problem Details pada timeout', async () => {
    const { POST } = await import('./chat/route');
    fetchMock.mockRejectedValueOnce(new DOMException('expired', 'TimeoutError'));
    const response = await POST(
      new NextRequest('https://web.example.test/api/chat', {
        method: 'POST',
        body: '{"message":"Halo"}',
      }),
    );
    expect(response.status).toBe(504);
    expect(response.headers.get('content-type')).toBe('application/problem+json');
  });
});

describe('/api/admin/agent', () => {
  it('memakai deadline agent saja dan mempertahankan auth, body, serta query', async () => {
    const { POST, GET, maxDuration } = await import('./admin/[...path]/route');
    const timeout = vi.spyOn(AbortSignal, 'timeout');
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ data: { reply: 'Halo admin' } }),
    });
    const request = new NextRequest('https://web.example.test/api/admin/agent?mode=test', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{"message":"Halo"}',
    });
    const response = await POST(request, { params: Promise.resolve({ path: ['agent'] }) });
    expect(response.status).toBe(200);
    expect(maxDuration).toBe(120);
    expect(timeout).toHaveBeenCalledWith(100_000);
    expect(fetchMock).toHaveBeenCalledWith(
      'https://backend.example.test/api/agent?mode=test',
      expect.objectContaining({
        body: '{"message":"Halo"}',
        signal: expect.any(AbortSignal),
        headers: expect.objectContaining({ authorization: 'Bearer test-token' }),
      }),
    );
    timeout.mockClear();
    await GET(new NextRequest('https://web.example.test/api/admin/users'), {
      params: Promise.resolve({ path: ['users'] }),
    });
    expect(timeout).not.toHaveBeenCalled();
    expect(fetchMock.mock.calls[1][1].signal).toBeUndefined();
  });

  it('tidak menghubungi backend tanpa session', async () => {
    const { POST } = await import('./admin/[...path]/route');
    getSession.mockResolvedValueOnce(null);
    const response = await POST(new NextRequest('https://web.example.test/api/admin/agent'), {
      params: Promise.resolve({ path: ['agent'] }),
    });
    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('mempertahankan error upstream dan timeout saat membaca body agent', async () => {
    const { POST } = await import('./admin/[...path]/route');
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({ title: 'Akses ditolak', detail: 'Izin diperlukan.' }),
    });
    const denied = await POST(new NextRequest('https://web.example.test/api/admin/agent'), {
      params: Promise.resolve({ path: ['agent'] }),
    });
    expect(denied.status).toBe(403);
    expect(await denied.json()).toMatchObject({ detail: 'Izin diperlukan.' });

    const controller = new AbortController();
    vi.spyOn(AbortSignal, 'timeout').mockReturnValueOnce(controller.signal);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => {
        controller.abort(new DOMException('expired', 'TimeoutError'));
        throw controller.signal.reason;
      },
    });
    const timedOut = await POST(new NextRequest('https://web.example.test/api/admin/agent'), {
      params: Promise.resolve({ path: ['agent'] }),
    });
    expect(timedOut.status).toBe(504);
  });

  it.each(['AbortError', 'TimeoutError'])('mengembalikan 504 untuk %s', async (name) => {
    const { POST } = await import('./admin/[...path]/route');
    fetchMock.mockRejectedValueOnce(new DOMException('expired', name));
    const response = await POST(new NextRequest('https://web.example.test/api/admin/agent'), {
      params: Promise.resolve({ path: ['agent'] }),
    });
    expect(response.status).toBe(504);
    expect(response.headers.get('content-type')).toBe('application/problem+json');
  });
});
