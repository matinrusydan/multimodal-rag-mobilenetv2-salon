import type { Request, Response } from 'express';
import { reservationService } from '../services/ReservationService';
import { ok } from '../utils/response';

export async function create(req: Request, res: Response): Promise<void> {
  const reservation = await reservationService.create(req.auth.userId, req.body);
  ok(res, reservation, 201);
}

export async function list(req: Request, res: Response): Promise<void> {
  ok(res, await reservationService.list(req.auth));
}

export async function detail(req: Request, res: Response): Promise<void> {
  const { code } = req.params;
  ok(res, await reservationService.byCode(req.auth, String(code)));
}

export async function cancel(req: Request, res: Response): Promise<void> {
  const { code } = req.params;
  ok(res, await reservationService.cancel(req.auth, String(code)));
}

export async function stats(req: Request, res: Response): Promise<void> {
  const days = Number(req.query.days ?? 7) || 7;
  ok(res, await reservationService.stats(days));
}

export async function updateStatus(req: Request, res: Response): Promise<void> {
  const { code } = req.params;
  ok(res, await reservationService.updateStatus(String(code), String(req.body.status)));
}
