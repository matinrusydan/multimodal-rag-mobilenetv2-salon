import { Router } from 'express';
import { create, detail, list, remove, update } from '../controllers/permissionController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import {
  createPermissionSchema,
  permissionParamsSchema,
  updatePermissionSchema,
} from '../schemas/permission.schema';

const router = Router();

router.get('/', requireAuth, securityEnforce('permissions.read'), list);
router.get(
  '/:id',
  requireAuth,
  securityEnforce('permissions.read'),
  validate(permissionParamsSchema),
  detail,
);
router.post(
  '/',
  requireAuth,
  securityEnforce('permissions.write'),
  validate(createPermissionSchema),
  create,
);
router.put(
  '/:id',
  requireAuth,
  securityEnforce('permissions.write'),
  validate(permissionParamsSchema),
  validate(updatePermissionSchema),
  update,
);
router.delete(
  '/:id',
  requireAuth,
  securityEnforce('permissions.delete'),
  validate(permissionParamsSchema),
  remove,
);

export default router;
