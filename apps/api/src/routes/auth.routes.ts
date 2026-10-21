import { Router } from 'express';
import { loginLimiter, registerLimiter } from '../config/rateLimit';
import { login, logout, register, session } from '../controllers/authController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { loginSchema, registerSchema } from '../schemas/auth.schema';

const router = Router();

router.post('/register', registerLimiter, validate(registerSchema), register);
router.post('/login', loginLimiter, validate(loginSchema), login);
router.post('/logout', requireAuth, logout);
router.get('/session', requireAuth, session);

export default router;
