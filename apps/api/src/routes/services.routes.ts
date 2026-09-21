import { Router } from 'express';
import {
  create,
  detail,
  list,
  listAdmin,
  remove,
  summary,
  update,
} from '../controllers/serviceController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import {
  createServiceSchema,
  serviceIdParamSchema,
  slugParamSchema,
  updateServiceSchema,
} from '../schemas/service.schema';

const router = Router();

// Publik
router.get('/', list);
router.get('/summary', summary);

// Admin (RBAC)
router.get('/admin/all', requireAuth, securityEnforce('services.read'), listAdmin);
router.post('/', requireAuth, securityEnforce('services.write'), validate(createServiceSchema), create);
router.put(
  '/id/:id',
  requireAuth,
  securityEnforce('services.write'),
  validate(serviceIdParamSchema),
  validate(updateServiceSchema),
  update,
);
router.delete(
  '/id/:id',
  requireAuth,
  securityEnforce('services.delete'),
  validate(serviceIdParamSchema),
  remove,
);

// Detail by slug (letakkan paling bawah agar tidak menutupi /summary, /admin/all)
router.get('/:slug', validate({ params: slugParamSchema }), detail);

export default router;
