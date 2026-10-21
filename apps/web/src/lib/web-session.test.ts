// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest';

const { getIronSession, cookies } = vi.hoisted(() => ({
  getIronSession: vi.fn(),
  cookies: vi.fn(async () => 'test-cookie-store'),
}));
vi.mock('iron-session', () => ({ getIronSession }));
vi.mock('next/headers', () => ({ cookies }));

import { getSession, sessionPassword, setSession } from './web-session';

afterEach(() => {
  vi.unstubAllEnvs();
  vi.clearAllMocks();
});

describe('sessionPassword', () => {
  it.each([
    undefined,
    '',
    'short',
    ' '.repeat(40),
    'change-me-session-secret',
    'development-only-session-secret-change-me',
    'dev-only-session-secret-that-is-long-enough',
    'example-session-secret-that-is-long-enough',
    'your-session-secret-that-is-long-enough',
    'CHANGE_ME-session-secret-that-is-long-enough',
    'tien-salon-dev-session-secret-2026-32chars-min',
    ' tien-salon-dev-session-secret-2026-32chars-min ',
  ])('menolak secret produksi tidak aman tanpa membocorkan nilainya', (secret) => {
    expect(() => sessionPassword(secret, 'production')).toThrow(/SESSION_SECRET/);
  });

  it('memakai secret produksi yang stabil minimal 32 karakter tanpa mengubahnya', () => {
    const secret = 'test-only-production-session-key-at-least-32';
    expect(sessionPassword(secret, 'production')).toBe(secret);
    expect(sessionPassword(secret, 'production')).toBe(secret);
    expect(sessionPassword('a'.repeat(32), 'production')).toHaveLength(32);
  });

  it('mempertahankan fallback hanya di luar produksi', () => {
    expect(sessionPassword(undefined, 'development')).toBe(
      'tien-salon-dev-session-secret-2026-32chars-min',
    );
    expect(sessionPassword('custom-dev', 'development')).toBe('custom-dev');
  });
});

describe('session integration', () => {
  it('menggunakan secret yang sama dan secure cookie untuk baca/tulis produksi', async () => {
    const secret = 'test-only-production-session-key-at-least-32';
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('SESSION_SECRET', secret);
    const save = vi.fn();
    const user = {
      id: 1,
      name: 'Test',
      email: 'test@example.test',
      type: 1,
      roles: [],
      permissions: [],
    };
    getIronSession.mockResolvedValue({ token: 'token', user, save });
    expect(await getSession()).toEqual({ token: 'token', user });
    await setSession({ token: 'token', user });
    expect(save).toHaveBeenCalledOnce();
    expect(getIronSession).toHaveBeenCalledTimes(2);
    for (const [, options] of getIronSession.mock.calls) {
      expect(options).toMatchObject({
        password: secret,
        cookieOptions: { secure: true, httpOnly: true },
      });
    }
  });

  it('menolak penggunaan session produksi tanpa secret sebelum membuka iron-session', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('SESSION_SECRET', '');
    await expect(getSession()).rejects.toThrow(/SESSION_SECRET/);
    expect(getIronSession).not.toHaveBeenCalled();
  });
});
