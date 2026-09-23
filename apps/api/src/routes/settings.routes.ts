import { Router } from 'express';
import {
  geminiKey,
  internalGet,
  listAdmin,
  publicSettings,
  update,
} from '../controllers/settingsController';
import { requireAuth } from '../middleware/requireAuth';
import { internalAuth } from '../middleware/internalAuth';
import { securityEnforce } from '../middleware/securityEnforce';

const router = Router();

// Publik: settings untuk landing.
router.get('/public', publicSettings);
// Internal: ambil gemini key mentah untuk apps/ai.
router.get('/gemini-key', internalAuth, geminiKey);
// Internal: nilai mentah setting apapun (apps/ai).
router.get('/internal/:key', internalAuth, internalGet);
// Admin.
router.get('/', requireAuth, securityEnforce('settings.read'), listAdmin);
router.put('/', requireAuth, securityEnforce('settings.write'), update);

export default router;
