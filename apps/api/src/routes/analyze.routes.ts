import { Router } from 'express';
import { postingLimiter } from '../config/rateLimit';
import { sendProblem } from '../utils/problemDetails';

const router = Router();

router.post('/', postingLimiter, (_req, res) => {
  sendProblem(
    res,
    {
      title: 'Fitur belum tersedia',
      detail: 'Analisis foto belum tersedia. Konsultasi melalui chat tetap dapat digunakan.',
    },
    503,
  );
});

export default router;
