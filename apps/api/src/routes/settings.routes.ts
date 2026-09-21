import { Router } from 'express';
import {
  geminiKey,
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
// Admin.
router.get('/', requireAuth, securityEnforce('settings.read'), listAdmin);
router.put('/', requireAuth, securityEnforce('settings.write'), update);

export default router;
