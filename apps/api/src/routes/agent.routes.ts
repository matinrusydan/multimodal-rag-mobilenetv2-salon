import { Router } from 'express';
import { postingLimiter } from '../config/rateLimit';
import { agent } from '../controllers/agentController';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import { validate } from '../middleware/requestValidator';
import { agentChatSchema } from '../schemas/agent.schema';

const router = Router();

/**
 * POST /api/admin/agent — chat dengan agent admin (RAG + tool-call data live).
 * Wajib login; dibatasi rate-limit. Hanya untuk user dengan permission dashboard.
 */
router.post(
  '/',
  requireAuth,
  securityEnforce('payments.read'),
  postingLimiter,
  validate(agentChatSchema),
  agent,
);

export default router;
