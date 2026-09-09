import { Router } from 'express';
import { login, logout, register, session } from '../controllers/authController';
import { validate } from '../middleware/requestValidator';
import { requireAuth } from '../middleware/requireAuth';
import { loginSchema, registerSchema } from '../schemas/auth.schema';

const router = Router();

router.post('/register', validate(registerSchema), register);
router.post('/login', validate(loginSchema), login);
router.post('/logout', requireAuth, logout);
router.get('/session', requireAuth, session);

export default router;
