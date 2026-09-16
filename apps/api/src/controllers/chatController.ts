import type { Request, Response } from 'express';
import { aiChat } from '../services/aiClient';
import { ok } from '../utils/response';

export async function chat(req: Request, res: Response): Promise<void> {
  const result = await aiChat(req.body);
  ok(res, result);
}
