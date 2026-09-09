import { Router } from 'express';
import {
  assignPermissions,
  create,
  detail,
  list,
  remove,
  update,
} from '../controllers/roleController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import {
  assignRolePermissionsSchema,
  createRoleSchema,
  roleParamsSchema,
  updateRoleSchema,
} from '../schemas/role.schema';

const router = Router();

router.get('/', requireAuth, securityEnforce('roles.read'), list);
router.get('/:id', requireAuth, securityEnforce('roles.read'), validate(roleParamsSchema), detail);
router.post('/', requireAuth, securityEnforce('roles.write'), validate(createRoleSchema), create);
router.put(
  '/:id',
  requireAuth,
  securityEnforce('roles.write'),
  validate(roleParamsSchema),
  validate(updateRoleSchema),
  update,
);
router.delete(
  '/:id',
  requireAuth,
  securityEnforce('roles.delete'),
  validate(roleParamsSchema),
  remove,
);
router.put(
  '/:id/permissions',
  requireAuth,
  securityEnforce('roles.manage'),
  validate(roleParamsSchema),
  validate(assignRolePermissionsSchema),
  assignPermissions,
);

export default router;
