import { Router } from 'express';
import { get, list, reingest, remove, save } from '../controllers/knowledgeController';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';

const router = Router();

router.get('/', requireAuth, securityEnforce('knowledge.read'), list);
router.post('/reingest', requireAuth, securityEnforce('knowledge.write'), reingest);
router.get('/:name', requireAuth, securityEnforce('knowledge.read'), get);
router.put('/:name', requireAuth, securityEnforce('knowledge.write'), save);
router.delete('/:name', requireAuth, securityEnforce('knowledge.delete'), remove);

export default router;
