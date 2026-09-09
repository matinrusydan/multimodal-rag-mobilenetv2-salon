import rateLimit from 'express-rate-limit';

export const postingLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 30,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: {
    type: 'about:blank#429',
    title: 'Terlalu banyak permintaan',
    status: 429,
    detail: 'Terlalu banyak permintaan, coba lagi beberapa saat lagi',
  },
});
