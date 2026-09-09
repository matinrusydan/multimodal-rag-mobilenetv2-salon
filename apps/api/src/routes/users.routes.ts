import { Router } from 'express';
import { assignRoles, create, detail, list, remove, update } from '../controllers/userController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import {
  assignUserRolesSchema,
  createUserSchema,
  updateUserSchema,
  userParamsSchema,
} from '../schemas/user.schema';

const router = Router();

router.get('/', requireAuth, securityEnforce('users.read'), list);
router.get('/:id', requireAuth, securityEnforce('users.read'), validate(userParamsSchema), detail);
router.post('/', requireAuth, securityEnforce('users.write'), validate(createUserSchema), create);
router.put(
  '/:id',
  requireAuth,
  securityEnforce('users.write'),
  validate(userParamsSchema),
  validate(updateUserSchema),
  update,
);
router.delete(
  '/:id',
  requireAuth,
  securityEnforce('users.delete'),
  validate(userParamsSchema),
  remove,
);
router.put(
  '/:id/roles',
  requireAuth,
  securityEnforce('users.manage'),
  validate(userParamsSchema),
  validate(assignUserRolesSchema),
  assignRoles,
);

export default router;
