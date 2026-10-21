import type { NextFunction, Request, Response } from 'express';
import request from 'supertest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  pingDb: vi.fn(),
  login: vi.fn((_req: Request, res: Response) => res.status(401).json({ status: 401 })),
  register: vi.fn((_req: Request, res: Response) => res.status(201).json({ ok: true })),
}));

vi.mock('dotenv', () => ({ config: vi.fn() }));
vi.mock('../src/config/db', () => ({ pingDb: mocks.pingDb }));
vi.mock('../src/controllers/authController', () => ({
  login: mocks.login,
  register: mocks.register,
  logout: (_req: Request, res: Response) => res.sendStatus(204),
  session: (_req: Request, res: Response) => res.json({ ok: true }),
}));
vi.mock('../src/middleware/requireAuth', () => ({
  requireAuth: (_req: Request, _res: Response, next: NextFunction) => next(),
}));
// Load only the routes under test; no repositories, DB pool, seeds, or test helpers.
async function routesUnderTest() {
  const { Router } = await import('express');
  const router = Router();
  router.use('/api', (await import('../src/routes/health.routes')).default);
  router.use('/api/analyze', (await import('../src/routes/analyze.routes')).default);
  router.use('/api/auth', (await import('../src/routes/auth.routes')).default);
  router.get('/api/test-ip', (req, res) => res.json({ ip: req.ip }));
  return { default: router };
}

beforeEach(() => {
  vi.resetModules();
  vi.doMock('../src/routes', routesUnderTest);
  vi.clearAllMocks();
  vi.stubEnv('NODE_ENV', 'test');
  vi.stubEnv('DATABASE_URL', 'postgresql://fixture:fixture@127.0.0.1:1/never_connect');
  vi.stubEnv('JWT_SECRET', 'test-jwt-secret-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
  vi.stubEnv('AI_INTERNAL_TOKEN', 'test-internal-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
  vi.stubEnv('TRUST_PROXY', 'false');
  vi.stubEnv('CORS_ORIGIN', ' https://salon.example , , https://admin.example ');
  mocks.pingDb.mockResolvedValue(true);
  mocks.login.mockImplementation((_req, res) => res.status(401).json({ status: 401 }));
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('AI must not be called'); }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

async function createApp() {
  return (await import('../src/app')).createApp();
}

describe('isolated deployment routes', () => {
  it('returns immediate analyze 503 for no file, invalid multipart, or arbitrary image data', async () => {
    const app = await createApp();
    for (const pending of [
      request(app).post('/api/analyze'),
      request(app).post('/api/analyze').set('Content-Type', 'multipart/form-data; boundary=bad').send('not multipart'),
      request(app).post('/api/analyze').attach('image', Buffer.from('not an image'), 'hair.jpg'),
    ]) {
      const res = await pending;
      expect(res.status).toBe(503);
      expect(res.body).toMatchObject({ status: 503, title: 'Fitur belum tersedia' });
      expect(res.body.detail).toContain('chat');
    }
    expect(fetch).not.toHaveBeenCalled();
  });

  it('preserves the analyze posting limiter', async () => {
    const app = await createApp();
    for (let i = 0; i < 30; i++) {
      expect((await request(app).post('/api/analyze')).status).toBe(503);
    }
    const res = await request(app).post('/api/analyze');
    expect(res.status).toBe(429);
    expect(res.body.status).toBe(429);
    expect(res.headers['ratelimit-policy']).toBe('30;w=900');
  });

  it('keeps liveness successful even when DB is unavailable and never calls AI or DB', async () => {
    mocks.pingDb.mockResolvedValue(false);
    const res = await request(await createApp()).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ ok: true, data: { status: 'ok' } });
    expect(res.body.data.db).toBe('not_checked');
    expect(mocks.pingDb).not.toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('reports readiness from a real DB probe contract, not AI availability', async () => {
    const app = await createApp();
    const ready = await request(app).get('/api/ready');
    expect(ready.status).toBe(200);
    expect(ready.body.data).toMatchObject({ status: 'ready', db: 'up' });
    mocks.pingDb.mockResolvedValue(false);
    const down = await request(app).get('/api/ready');
    expect(down.status).toBe(503);
    expect(down.body).toMatchObject({ status: 503, title: 'Layanan belum siap' });
    expect(down.headers['cache-control']).toBe('no-store');
    expect(mocks.pingDb).toHaveBeenCalledTimes(2);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('trims CORS origins and does not trust spoofed forwarding headers by default', async () => {
    const app = await createApp();
    expect(app.get('trust proxy')).toBe(false);
    const res = await request(app).get('/api/test-ip')
      .set('Origin', 'https://admin.example').set('X-Forwarded-For', '203.0.113.50');
    expect(res.headers['access-control-allow-origin']).toBe('https://admin.example');
    expect(res.body.ip).not.toBe('203.0.113.50');
    const denied = await request(app).get('/api/health').set('Origin', 'https://untrusted.example');
    expect(denied.headers['access-control-allow-origin']).toBeUndefined();
  });

  it('applies only an explicitly configured bounded proxy hop count', async () => {
    vi.stubEnv('TRUST_PROXY', '1');
    const app = await createApp();
    expect(app.get('trust proxy')).toBe(1);
    const res = await request(app).get('/api/test-ip').set('X-Forwarded-For', '203.0.113.50');
    expect(res.body.ip).toBe('203.0.113.50');
  });

  it('limits failed logins and registration independently before the controllers', async () => {
    const app = await createApp();
    const credentials = { email: 'fixture@example.com', password: 'fixture-password' };
    for (let i = 0; i < 10; i++) {
      expect((await request(app).post('/api/auth/login').send(credentials)).status).toBe(401);
    }
    expect((await request(app).post('/api/auth/login').send(credentials)).status).toBe(429);
    expect(mocks.login).toHaveBeenCalledTimes(10);
    for (let i = 0; i < 5; i++) {
      expect((await request(app).post('/api/auth/register').send({ name: 'Fixture', ...credentials })).status).toBe(201);
    }
    expect((await request(app).post('/api/auth/register').send({ name: 'Fixture', ...credentials })).status).toBe(429);
    expect(mocks.register).toHaveBeenCalledTimes(5);
    expect((await request(app).post('/api/auth/logout')).status).toBe(204);
    expect((await request(app).get('/api/auth/session')).status).toBe(200);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('counts invalid login bodies too, but does not penalize successful logins', async () => {
    const app = await createApp();
    mocks.login.mockImplementation((_req, res) => res.status(200).json({ ok: true }));
    for (let i = 0; i < 12; i++) {
      expect((await request(app).post('/api/auth/login')
        .send({ email: 'fixture@example.com', password: 'fixture-password' })).status).toBe(200);
    }
    for (let i = 0; i < 10; i++) {
      expect((await request(app).post('/api/auth/login').send({})).status).toBe(400);
    }
    expect((await request(app).post('/api/auth/login').send({})).status).toBe(429);
    expect(mocks.login).toHaveBeenCalledTimes(12);
  });
});
