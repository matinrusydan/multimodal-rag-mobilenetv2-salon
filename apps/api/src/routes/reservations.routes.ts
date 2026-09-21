import { Router } from 'express';
import {
  cancel,
  create,
  detail,
  list,
  stats,
  updateStatus,
} from '../controllers/reservationController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { requireAuthOrInternal } from '../middleware/internalAuth';
import { securityEnforce } from '../middleware/securityEnforce';
import { createReservationSchema, reservationCodeSchema } from '../schemas/reservation.schema';

const router = Router();

router.post(
  '/',
  requireAuth,
  securityEnforce('reservations.create'),
  validate(createReservationSchema),
  create,
);
router.get('/', requireAuth, securityEnforce('reservations.read', { own: true }), list);
// Stats: admin ber-JWT ATAU brain engine (X-Internal-Token).
router.get(
  '/stats',
  requireAuthOrInternal,
  securityEnforce('reservations.read', { own: true }),
  stats,
);
router.get(
  '/:code',
  requireAuth,
  securityEnforce('reservations.read', { own: true }),
  validate(reservationCodeSchema),
  detail,
);
router.put(
  '/:code/cancel',
  requireAuth,
  securityEnforce('reservations.write'),
  validate(reservationCodeSchema),
  cancel,
);
router.put(
  '/:code/status',
  requireAuth,
  securityEnforce('reservations.write'),
  validate(reservationCodeSchema),
  updateStatus,
);

export default router;
