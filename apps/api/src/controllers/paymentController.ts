import type { Request, Response } from 'express';
import { paymentService } from '../services/PaymentService';
import { ok } from '../utils/response';

export async function simulate(req: Request, res: Response): Promise<void> {
  const result = await paymentService.simulate(req.auth, req.body);
  ok(res, result);
}

export async function status(req: Request, res: Response): Promise<void> {
  const { id } = req.params;
  ok(res, await paymentService.status(String(id)));
}

export async function summary(req: Request, res: Response): Promise<void> {
  const from = typeof req.query.from === 'string' ? req.query.from : undefined;
  const to = typeof req.query.to === 'string' ? req.query.to : undefined;
  ok(res, await paymentService.summary(from, to));
}
