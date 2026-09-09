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
