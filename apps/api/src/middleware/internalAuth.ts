import type { RequestHandler } from 'express';
import { env } from '../config/env';
import { verifyToken } from '../config/jwt';
import { userRepository } from '../repositories/UserRepository';
import { permissionCache } from '../services/PermissionCache';
import { HttpError } from '../utils/problemDetails';

/**
 * Authenticate internal service calls (dari apps/ai brain engine) via header
 * `X-Internal-Token`. Bila cocok, set `req.auth` sebagai konteks superadmin
 * internal agar boleh mengakses endpoint ringkasan data untuk agent admin.
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
 * Guard: izinkan bila (1) user login via JWT Bearer yang valid, ATAU (2) memakai
 * X-Internal-Token yang valid (brain engine). Dipakai untuk endpoint ringkasan
 * yang bisa diakses admin ber-JWT maupun agent internal.
 */
export const requireAuthOrInternal: RequestHandler = async (req, _res, next) => {
  const header = req.headers.authorization;

  // Tanpa Bearer -> coba token internal (brain engine).
  if (!header?.startsWith('Bearer ')) {
    internalAuth(req, _res, next);
    return;
  }

  // Dengan Bearer -> autentikasi user seperti requireAuth.
  try {
    const token = header.slice('Bearer '.length);
    const { userId } = verifyToken(token);
    const user = await userRepository.findById(userId);
    if (!user || user.status !== 'active') {
      next(new HttpError(401, 'Akun tidak ditemukan atau nonaktif'));
      return;
    }
    let permissions = permissionCache.get(userId);
    if (!permissions) {
      permissions = await userRepository.findPermissions(userId);
      permissionCache.set(userId, permissions);
    }
    const roles = await userRepository.findRoles(userId);
    req.auth = {
      userId: user.id,
      name: user.name,
      email: user.email,
      type: user.type,
      permissions,
      roles: roles.map((r) => r.code),
    };
    next();
  } catch (err) {
    next(new HttpError(401, 'Sesi tidak valid atau kedaluwarsa'));
  }
};
