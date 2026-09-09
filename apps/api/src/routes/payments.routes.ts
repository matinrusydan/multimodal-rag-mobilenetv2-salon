import { Router } from 'express';
import { simulate, status } from '../controllers/paymentController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
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
router.get(
  '/:id',
  requireAuth,
  securityEnforce('payments.read'),
  validate(paymentIdSchema),
  status,
);

export default router;
