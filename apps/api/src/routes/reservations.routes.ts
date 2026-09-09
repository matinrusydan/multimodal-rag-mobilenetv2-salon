import { Router } from 'express';
import { cancel, create, detail, list } from '../controllers/reservationController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
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

export default router;
