import type { Request, Response } from 'express';
import { chatService } from '../services/ChatService';
import { ok } from '../utils/response';

export async function chat(req: Request, res: Response): Promise<void> {
  const result = await chatService.chat(req.body);
  ok(res, result);
}
