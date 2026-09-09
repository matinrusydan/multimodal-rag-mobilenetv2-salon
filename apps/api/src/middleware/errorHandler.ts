import type { ErrorRequestHandler } from 'express';
import { ZodError } from 'zod';
import { logger } from '../config/logger';
import { HttpError, sendProblem } from '../utils/problemDetails';

interface PgError extends Error {
  code?: string;
}

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

  const pgErr = err as PgError;
  if (pgErr.code === '23505') {
    sendProblem(
      res,
      { title: 'Data sudah ada', detail: 'Data dengan nilai unik tersebut sudah digunakan' },
      409,
    );
    return;
  }

  logger.error(err);
  sendProblem(res, { title: 'Kesalahan server', detail: 'Terjadi kesalahan internal' }, 500);
};
