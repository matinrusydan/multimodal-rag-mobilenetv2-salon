import type { Request, Response } from 'express';
import { pingDb } from '../config/db';
import { logger } from '../config/logger';
import { sendProblem } from '../utils/problemDetails';
import { ok } from '../utils/response';

/** Liveness is independent of the database and AI provider. */
export async function health(_req: Request, res: Response): Promise<void> {
  res.setHeader('Cache-Control', 'no-store');
  ok(res, {
    status: 'ok',
    uptime: process.uptime(),
    db: 'not_checked',
    timestamp: new Date().toISOString(),
  });
}

/** Readiness checks only the required database, never paid AI calls. */
export async function ready(_req: Request, res: Response): Promise<void> {
  res.setHeader('Cache-Control', 'no-store');
  if (!await pingDb()) {
    logger.warn('Readiness check: database down');
    sendProblem(res, {
      title: 'Layanan belum siap',
      detail: 'Koneksi database belum tersedia. Silakan coba lagi.',
    }, 503);
    return;
  }
  ok(res, {
    status: 'ready',
    db: 'up',
    timestamp: new Date().toISOString(),
  });
}
