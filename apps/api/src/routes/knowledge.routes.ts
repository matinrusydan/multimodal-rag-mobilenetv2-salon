import { Router } from 'express';
import { crawl, get, list, reingest, remove, save } from '../controllers/knowledgeController';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';

const router = Router();

router.get('/', requireAuth, securityEnforce('knowledge.read'), list);
router.post('/reingest', requireAuth, securityEnforce('knowledge.write'), reingest);
router.post('/crawl', requireAuth, securityEnforce('knowledge.write'), crawl);
router.get('/:name', requireAuth, securityEnforce('knowledge.read'), get);
router.put('/:name', requireAuth, securityEnforce('knowledge.write'), save);
router.delete('/:name', requireAuth, securityEnforce('knowledge.delete'), remove);

export default router;
