import { Router } from 'express';
import { postingLimiter } from '../config/rateLimit';
import { chat } from '../controllers/chatController';
import { validate } from '../middleware/requestValidator';
import { chatSchema } from '../schemas/chat.schema';

const router = Router();

router.post('/', postingLimiter, validate(chatSchema), chat);

export default router;
