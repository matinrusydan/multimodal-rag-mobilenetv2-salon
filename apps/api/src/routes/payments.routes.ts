import { Router } from 'express';
import {
  detailAdmin,
  listAdmin,
  simulate,
  status,
  summary,
} from '../controllers/paymentController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { requireAuthOrInternal } from '../middleware/internalAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import {
  adminPaymentParamsSchema,
  adminPaymentsQuerySchema,
  paymentIdSchema,
  simulateSchema,
} from '../schemas/payment.schema';

const router = Router();

router.post(
  '/simulate',
  requireAuth,
  securityEnforce('payments.write'),
  validate(simulateSchema),
  simulate,
);
router.get(
  '/',
  requireAuth,
  securityEnforce('payments.read'),
  validate(adminPaymentsQuerySchema),
  listAdmin,
);
// Summary: bisa diakses admin ber-JWT (Bearer) ATAU brain engine (X-Internal-Token).
router.get('/summary', requireAuthOrInternal, securityEnforce('payments.read'), summary);
router.get(
  '/admin/:id',
  requireAuth,
  securityEnforce('payments.read'),
  validate(adminPaymentParamsSchema),
  detailAdmin,
);
router.get(
  '/:id',
  requireAuth,
  securityEnforce('payments.read'),
  validate(paymentIdSchema),
  status,
);

export default router;
