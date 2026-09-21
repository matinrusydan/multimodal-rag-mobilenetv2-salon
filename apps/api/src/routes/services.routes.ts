import { Router } from 'express';
import { detail, list, summary } from '../controllers/serviceController';
import { validate } from '../middleware/requestValidator';
import { slugParamSchema } from '../schemas/service.schema';

const router = Router();

router.get('/', list);
router.get('/summary', summary);
router.get('/:slug', validate({ params: slugParamSchema }), detail);

export default router;
