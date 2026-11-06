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

export async function listAdmin(req: Request, res: Response): Promise<void> {
  const page = Number(req.query.page ?? 1) || 1;
  const pageSize = req.query.pageSize ? Number(req.query.pageSize) : undefined;
  const limit = req.query.limit ? Number(req.query.limit) : undefined;
  const status = typeof req.query.status === 'string' ? req.query.status : undefined;
  const search = typeof req.query.search === 'string' ? req.query.search : undefined;

  const result = await paymentService.listAdmin(req.auth, {
    page,
    pageSize,
    limit,
    status,
    search,
  });
  ok(res, result);
}

export async function detailAdmin(req: Request, res: Response): Promise<void> {
  const id = Number(req.params.id);
  const result = await paymentService.detailAdmin(req.auth, id);
  ok(res, result);
}
