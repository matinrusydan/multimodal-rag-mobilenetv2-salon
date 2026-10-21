import express from 'express';
import request from 'supertest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({ warn: vi.fn(), error: vi.fn() }));
vi.mock('dotenv', () => ({ config: vi.fn() }));
vi.mock('../src/config/logger', () => ({ logger: mocks }));

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
  vi.stubEnv('NODE_ENV', 'test');
  vi.stubEnv('DATABASE_URL', 'postgresql://fixture:fixture@127.0.0.1:1/never_connect');
  vi.stubEnv('JWT_SECRET', 'test-jwt-secret-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
  vi.stubEnv('AI_INTERNAL_TOKEN', 'test-internal-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
  vi.stubEnv('AI_URL', 'http://127.0.0.1:1');
  vi.stubEnv('TRUST_PROXY', 'false');
  vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

async function proxyApp() {
  const { aiChat, aiAgent } = await import('../src/services/aiClient');
  const knowledge = await import('../src/controllers/knowledgeController');
  const { errorHandler } = await import('../src/middleware/errorHandler');
  const app = express();
  app.use(express.json());
  app.post('/chat', async (req, res) => res.json(await aiChat(req.body)));
  app.post('/agent', async (req, res) => res.json(await aiAgent(req.body, {
    userId: 42, name: 'Fixture', permissions: ['services.read'], type: 1,
  })));
  app.get('/knowledge', knowledge.list);
  app.get('/knowledge/:name', knowledge.get);
  app.use(errorHandler);
  return app;
}

const secretBody = 'PRIVATE_UPSTREAM_TOKEN postgres://credentials internal traceback';

describe('isolated safe AI proxies', () => {
  it('preserves chat data, agent RBAC context, and internal-only token forwarding', async () => {
    vi.mocked(fetch).mockImplementation(async () => Response.json({ data: { answer: 'Jawaban' } }));
    const app = await proxyApp();
    expect((await request(app).post('/chat').send({ message: 'Halo' })).body).toEqual({ answer: 'Jawaban' });
    const chat = vi.mocked(fetch).mock.calls[0];
    expect(chat[0]).toBe('http://127.0.0.1:1/ai/chat');
    expect(chat[1]?.headers).not.toHaveProperty('X-Internal-Token');
    expect(chat[1]?.signal).toBeInstanceOf(AbortSignal);

    const agent = await request(app).post('/agent').send({ message: 'Layanan', auth: { userId: 999, type: 0 } });
    expect(agent.status).toBe(200);
    const agentOptions = vi.mocked(fetch).mock.calls[1][1];
    expect(agentOptions?.headers).toHaveProperty('X-Internal-Token', process.env.AI_INTERNAL_TOKEN);
    expect(agentOptions?.redirect).toBe('error');
    expect(JSON.parse(String(agentOptions?.body)).auth).toEqual({
      userId: 42, name: 'Fixture', permissions: ['services.read'], type: 1,
    });
    expect((await request(app).get('/knowledge')).body).toEqual({ ok: true, data: { answer: 'Jawaban' } });
    expect(vi.mocked(fetch).mock.calls[2][1]?.headers).toHaveProperty('X-Internal-Token');
  });

  it.each([400, 401, 403, 404, 422, 429, 500, 503, 504])(
    'sanitizes upstream status %s without logging its body',
    async (status) => {
      vi.mocked(fetch).mockImplementation(async () => new Response(secretBody, { status }));
      const app = await proxyApp();
      for (const pending of [
        request(app).post('/chat').send({ message: 'Halo' }),
        request(app).post('/agent').send({ message: 'Halo' }),
        request(app).get('/knowledge'),
      ]) {
        const res = await pending;
        expect(res.status).toBe(status === 504 ? 504 : status >= 500 ? 502 : status);
        expect(res.body.status).toBe(res.status);
        expect(JSON.stringify(res.body)).not.toContain(secretBody);
        expect(res.body.detail).toContain('Layanan AI');
      }
      expect(mocks.warn).toHaveBeenCalledTimes(3);
      expect(JSON.stringify(mocks.warn.mock.calls)).not.toContain(secretBody);
      expect(JSON.stringify(mocks.warn.mock.calls)).not.toContain(process.env.AI_INTERNAL_TOKEN);
      expect(mocks.warn.mock.calls[0][0]).toMatchObject({ status, outcome: 'upstream' });
    },
  );

  it.each(['TimeoutError', 'AbortError', 'TypeError'])(
    'handles %s on all proxies without exposing network details',
    async (name) => {
      vi.mocked(fetch).mockRejectedValue(Object.assign(new Error(secretBody), { name }));
      const app = await proxyApp();
      for (const pending of [
        request(app).post('/chat').send({}),
        request(app).post('/agent').send({}),
        request(app).get('/knowledge'),
      ]) {
        const res = await pending;
        expect(res.status).toBe(name === 'TypeError' ? 502 : 504);
        expect(JSON.stringify(res.body)).not.toContain(secretBody);
      }
      expect(JSON.stringify(mocks.warn.mock.calls)).not.toContain(secretBody);
    },
  );

  it.each(['not-json', '{}', '{"data":null}', '{"data":"private-invalid-data"}'])(
    'rejects invalid success payload %s as sanitized 502',
    async (body) => {
      vi.mocked(fetch).mockImplementation(async () => new Response(body));
      const app = await proxyApp();
      const res = await request(app).post('/chat').send({});
      expect(res.status).toBe(502);
      expect(res.body.detail).toBe('Layanan AI mengembalikan respons tidak valid.');
      expect(JSON.stringify(mocks.warn.mock.calls)).not.toContain(body);
    },
  );

  it('handles timeouts while reading the success body', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true, status: 200,
      json: () => Promise.reject(Object.assign(new Error(secretBody), { name: 'TimeoutError' })),
    } as unknown as Response);
    const res = await request(await proxyApp()).get('/knowledge');
    expect(res.status).toBe(504);
    expect(JSON.stringify(mocks.warn.mock.calls)).not.toContain(secretBody);
  });

  it('uses bounded per-operation timeouts, including body reads', async () => {
    const timeout = vi.spyOn(AbortSignal, 'timeout');
    vi.mocked(fetch).mockImplementation(async () => Response.json({ data: {} }));
    const app = await proxyApp();
    await request(app).post('/chat').send({});
    await request(app).post('/agent').send({});
    await request(app).get('/knowledge');
    expect(timeout.mock.calls.map(([ms]) => ms)).toEqual([90_000, 60_000, 60_000]);
  });
});
