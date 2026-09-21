import type { Request, Response } from 'express';
import { aiAgent } from '../services/aiClient';
import { ok } from '../utils/response';

/**
 * Admin agent chat — meneruskan ke FastAPI /ai/agent.
 * RBAC sudah ditegakkan di layer route (requireAuth + securityEnforce).
 */
export async function agent(req: Request, res: Response): Promise<void> {
  const result = await aiAgent(req.body, req.auth);
  ok(res, result);
}
