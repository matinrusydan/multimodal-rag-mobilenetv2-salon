import type { RequestHandler } from 'express';
import type { ZodTypeAny } from 'zod';

interface ValidateTargets {
  body?: ZodTypeAny;
  params?: ZodTypeAny;
  query?: ZodTypeAny;
}

export function validate(targets: ValidateTargets): RequestHandler {
  return (req, _res, next) => {
    try {
      if (targets.body) req.body = targets.body.parse(req.body);
      if (targets.params) req.params = targets.params.parse(req.params);
      if (targets.query) {
        const parsed = targets.query.parse(req.query);
        try {
          req.query = parsed;
        } catch {
          Object.defineProperty(req, 'query', {
            value: parsed,
            writable: true,
            enumerable: true,
            configurable: true,
          });
        }
      }
      next();
    } catch (err) {
      next(err);
    }
  };
}
