import rateLimit from 'express-rate-limit';

// In-memory limits are per API process. Only trust forwarding from a controlled ingress.
export const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 10,
  skipSuccessfulRequests: true,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: {
    type: 'about:blank#429',
    title: 'Terlalu banyak percobaan masuk',
    status: 429,
    detail: 'Terlalu banyak percobaan masuk, coba lagi beberapa saat lagi',
  },
});

export const registerLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  limit: 5,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: {
    type: 'about:blank#429',
    title: 'Terlalu banyak pendaftaran',
    status: 429,
    detail: 'Terlalu banyak permintaan pendaftaran, coba lagi beberapa saat lagi',
  },
});

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
