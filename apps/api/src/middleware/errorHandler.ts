import type { ErrorRequestHandler } from 'express';
import { ZodError } from 'zod';
import { logger } from '../config/logger';
import { HttpError, sendProblem } from '../utils/problemDetails';

export const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  if (err instanceof ZodError) {
    const detail = err.issues
      .map((issue) => `${issue.path.join('.')}: ${issue.message}`)
      .join(', ');
    sendProblem(res, { title: 'Validasi gagal', detail }, 400);
    return;
  }

  if (err instanceof HttpError) {
    sendProblem(res, { title: err.message, detail: err.message }, err.status);
    return;
  }

  if (err instanceof SyntaxError && 'body' in err) {
    sendProblem(res, { title: 'JSON tidak valid', detail: err.message }, 400);
    return;
  }

  logger.error(err);
  sendProblem(res, { title: 'Kesalahan server', detail: 'Terjadi kesalahan internal' }, 500);
};
