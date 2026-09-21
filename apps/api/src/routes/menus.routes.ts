import { Router } from 'express';
import {
  assignRoles,
  create,
  detail,
  list,
  mine,
  remove,
  update,
} from '../controllers/menuController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import {
  assignMenuRolesSchema,
  createMenuSchema,
  menuParamsSchema,
  updateMenuSchema,
} from '../schemas/menu.schema';

const router = Router();

router.get('/', requireAuth, securityEnforce('menus.read'), list);
// Menu milik user (sidebar). Cukup login — tidak butuh menus.read.
router.get('/me', requireAuth, mine);
router.get('/:id', requireAuth, securityEnforce('menus.read'), validate(menuParamsSchema), detail);
router.post('/', requireAuth, securityEnforce('menus.write'), validate(createMenuSchema), create);
router.put(
  '/:id',
  requireAuth,
  securityEnforce('menus.write'),
  validate(menuParamsSchema),
  validate(updateMenuSchema),
  update,
);
router.delete(
  '/:id',
  requireAuth,
  securityEnforce('menus.delete'),
  validate(menuParamsSchema),
  remove,
);
router.put(
  '/:id/roles',
  requireAuth,
  securityEnforce('menus.manage'),
  validate(menuParamsSchema),
  validate(assignMenuRolesSchema),
  assignRoles,
);

export default router;
