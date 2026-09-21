import { Router } from 'express';
import { simulate, status, summary } from '../controllers/paymentController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { requireAuthOrInternal } from '../middleware/internalAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import { paymentIdSchema, simulateSchema } from '../schemas/payment.schema';

const router = Router();

router.post(
  '/simulate',
  requireAuth,
  securityEnforce('payments.write'),
  validate(simulateSchema),
  simulate,
);
// Summary: bisa diakses admin ber-JWT (Bearer) ATAU brain engine (X-Internal-Token).
router.get('/summary', requireAuthOrInternal, securityEnforce('payments.read'), summary);
router.get(
  '/:id',
  requireAuth,
  securityEnforce('payments.read'),
  validate(paymentIdSchema),
  status,
);

export default router;
