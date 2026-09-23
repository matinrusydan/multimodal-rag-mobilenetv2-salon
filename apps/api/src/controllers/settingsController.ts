import type { Request, Response } from 'express';
import { settingsService } from '../services/SettingsService';
import { ok } from '../utils/response';

export async function publicSettings(_req: Request, res: Response): Promise<void> {
  ok(res, await settingsService.publicSettings());
}

export async function listAdmin(_req: Request, res: Response): Promise<void> {
  ok(res, await settingsService.listForAdmin());
}

export async function update(req: Request, res: Response): Promise<void> {
  const entries = Array.isArray(req.body?.entries) ? req.body.entries : [];
  await settingsService.update(entries);
  ok(res, { status: 'saved' });
}

export async function geminiKey(req: Request, res: Response): Promise<void> {
  // Dipakai apps/ai (internal). Return nilai mentah.
  ok(res, { key: await settingsService.geminiKey() });
}

export async function internalGet(req: Request, res: Response): Promise<void> {
  // Nilai mentah setting apapun (untuk apps/ai).
  const key = String(req.params.key);
  ok(res, { value: await settingsService.rawGet(key) });
}
