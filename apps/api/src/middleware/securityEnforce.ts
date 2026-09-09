import { hasPermission } from '@rag-salon/shared-utils';
import type { RequestHandler } from 'express';
import { env } from '../config/env';
import { HttpError } from '../utils/problemDetails';

const SUPERADMIN_ROLES = ['SUPER_ADMIN', 'SUPERADMIN'];

/**
 * RBAC middleware. Memeriksa permission `<resource>.<action>`,
 * mendukung wildcard `resource.*`/`resource.manage`, kepemilikan `resource.action.own`
 * (via opsi `own`), dan superadmin bypass.
 */
export function securityEnforce(permission: string, options?: { own?: boolean }): RequestHandler {
  return (req, _res, next) => {
    if (!env.SECURITY_ENFORCE_ENABLED) {
      next();
      return;
    }

    const auth = req.auth;
    if (!auth) {
      next(new HttpError(401, 'Silakan masuk terlebih dahulu'));
      return;
    }

    const isSuperadmin =
      auth.type === 0 ||
      auth.permissions.includes('*') ||
      auth.roles.some((role) => SUPERADMIN_ROLES.includes(role));

    if (isSuperadmin) {
      next();
      return;
    }

    if (!hasPermission(auth.permissions, permission, options?.own)) {
      next(new HttpError(403, 'Anda tidak memiliki izin untuk aksi ini'));
      return;
    }

    next();
  };
}
