import { Router } from 'express';
import multer from 'multer';
import { postingLimiter } from '../config/rateLimit';
import { analyze } from '../controllers/analyzeController';

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });

const router = Router();

router.post('/', postingLimiter, upload.single('image'), analyze);

export default router;
