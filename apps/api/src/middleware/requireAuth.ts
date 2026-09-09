import type { RequestHandler } from 'express';
import { verifyToken } from '../config/jwt';
import { userRepository } from '../repositories/UserRepository';
import { permissionCache } from '../services/PermissionCache';
import { HttpError } from '../utils/problemDetails';

export const requireAuth: RequestHandler = async (req, _res, next) => {
  try {
    const header = req.headers.authorization;
    const token = header?.startsWith('Bearer ') ? header.slice('Bearer '.length) : undefined;
    if (!token) {
      next(new HttpError(401, 'Silakan masuk terlebih dahulu'));
      return;
    }

    let userId: number;
    try {
      ({ userId } = verifyToken(token));
    } catch {
      next(new HttpError(401, 'Sesi tidak valid atau kedaluwarsa'));
      return;
    }

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
    next(err);
  }
};
