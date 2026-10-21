import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('dotenv', () => ({ config: vi.fn() }));

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv('NODE_ENV', 'test');
  vi.stubEnv('DATABASE_URL', 'postgresql://fixture:fixture@127.0.0.1:1/never_connect');
  vi.stubEnv('JWT_SECRET', 'test-jwt-secret-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
  vi.stubEnv('AI_INTERNAL_TOKEN', 'test-internal-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');
  vi.stubEnv('TRUST_PROXY', 'false');
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

describe('isolated production environment validation', () => {
  it('accepts sufficiently long production secrets without connecting to DB', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    const { env } = await import('../src/config/env');
    expect(env.NODE_ENV).toBe('production');
    expect(env.TRUST_PROXY).toBe(false);
  });

  it.each(['JWT_SECRET', 'AI_INTERNAL_TOKEN'] as const)(
    'rejects short %s without exposing values in errors or diagnostics',
    async (key) => {
      vi.stubEnv('NODE_ENV', 'production');
      vi.stubEnv(key, 'private-short-fixture');
      const error = vi.spyOn(console, 'error').mockImplementation(() => undefined);
      await expect(import('../src/config/env')).rejects.toThrow('Validasi environment gagal');
      expect(JSON.stringify(error.mock.calls)).not.toContain('private-short-fixture');
      expect(JSON.stringify(error.mock.calls)).toContain(key);
    },
  );

  it.each(['JWT_SECRET', 'AI_INTERNAL_TOKEN'] as const)(
    'rejects known example/development values for %s even when padded',
    async (key) => {
      vi.stubEnv('NODE_ENV', 'production');
      vi.stubEnv(key, key === 'JWT_SECRET'
        ? 'change-me-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        : 'dev-internal-token-change-me-xxxxxxxxxxxx');
      vi.spyOn(console, 'error').mockImplementation(() => undefined);
      await expect(import('../src/config/env')).rejects.toThrow('Validasi environment gagal');
    },
  );

  it('rejects production defaults and preserves development compatibility', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('JWT_SECRET', 'change-me');
    delete process.env.AI_INTERNAL_TOKEN;
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(import('../src/config/env')).rejects.toThrow();
    vi.resetModules();
    vi.stubEnv('NODE_ENV', 'development');
    const { env } = await import('../src/config/env');
    expect(env.JWT_SECRET).toBe('change-me');
    expect(env.AI_INTERNAL_TOKEN).toBe('dev-internal-token-change-me');
  });

  it('defaults to no trusted proxies', async () => {
    delete process.env.TRUST_PROXY;
    expect((await import('../src/config/env')).env.TRUST_PROXY).toBe(false);
  });

  it.each(['1', '2', '3', '4', '5'])('accepts bounded proxy hop count %s', async (value) => {
    vi.stubEnv('TRUST_PROXY', value);
    expect((await import('../src/config/env')).env.TRUST_PROXY).toBe(Number(value));
  });

  it.each(['true', '0', '6', '-1', '1.5', 'loopback', '*', ''])('rejects unsafe/invalid proxy setting %s', async (value) => {
    vi.stubEnv('TRUST_PROXY', value);
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(import('../src/config/env')).rejects.toThrow('Validasi environment gagal');
  });
});
