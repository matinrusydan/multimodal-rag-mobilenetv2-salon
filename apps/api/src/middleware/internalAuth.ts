import type { RequestHandler } from 'express';
import { env } from '../config/env';
import { HttpError } from '../utils/problemDetails';

/**
 * Authenticate internal service calls (dari apps/ai brain engine) via header
 * `X-Internal-Token`. Bila cocok, set `req.auth` sebagai konteks superadmin
 * internal agar boleh mengakses endpoint ringkasan data untuk agent admin.
 *
 * Dipakai HANYA untuk endpoint baca (summary) yang dipanggil tool agent.
 * Token dicek terhadap env.AI_INTERNAL_TOKEN (shared secret dengan apps/ai).
 */
export const internalAuth: RequestHandler = (req, _res, next) => {
  const token = req.headers['x-internal-token'];
  if (typeof token === 'string' && token && token === env.AI_INTERNAL_TOKEN) {
    req.auth = {
      userId: 0,
      name: 'internal-brain-engine',
      email: 'internal@local',
      type: 0, // superadmin internal
      permissions: ['*'],
      roles: ['INTERNAL'],
    };
    next();
    return;
  }
  next(new HttpError(401, 'Token internal tidak valid'));
};

/**
 * Guard: izinkan bila sudah lolos `requireAuth` (req.auth terisi) ATAU memakai
 * token internal yang valid. Dipakai untuk endpoint yang bisa diakses user auth
 * maupun brain engine internal.
 */
export const requireAuthOrInternal: RequestHandler = (req, _res, next) => {
  if (req.auth) {
    next();
    return;
  }
  internalAuth(req, _res, next);
};
