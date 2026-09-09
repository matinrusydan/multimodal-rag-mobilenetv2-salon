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
