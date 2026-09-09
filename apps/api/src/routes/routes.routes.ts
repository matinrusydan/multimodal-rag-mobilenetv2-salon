import { Router } from 'express';
import { create, detail, list, remove, update } from '../controllers/routeController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import { createRouteSchema, routeParamsSchema, updateRouteSchema } from '../schemas/route.schema';

const router = Router();

router.get('/', requireAuth, securityEnforce('routes.read'), list);
router.get(
  '/:id',
  requireAuth,
  securityEnforce('routes.read'),
  validate(routeParamsSchema),
  detail,
);
router.post('/', requireAuth, securityEnforce('routes.write'), validate(createRouteSchema), create);
router.put(
  '/:id',
  requireAuth,
  securityEnforce('routes.write'),
  validate(routeParamsSchema),
  validate(updateRouteSchema),
  update,
);
router.delete(
  '/:id',
  requireAuth,
  securityEnforce('routes.delete'),
  validate(routeParamsSchema),
  remove,
);

export default router;
