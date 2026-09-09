import type { Request, Response } from 'express';
import { pingDb } from '../config/db';
import { logger } from '../config/logger';
import { ok } from '../utils/response';

export async function health(_req: Request, res: Response): Promise<void> {
  const dbUp = await pingDb();
  if (!dbUp) {
    logger.warn('Health check: database down');
  }
  ok(res, {
    status: 'ok',
    uptime: process.uptime(),
    db: dbUp ? 'up' : 'down',
    timestamp: new Date().toISOString(),
  });
}
