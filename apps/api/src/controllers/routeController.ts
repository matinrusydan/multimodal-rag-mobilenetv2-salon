import type { Request, Response } from 'express';
import { routeService } from '../services/RouteService';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await routeService.list());
}

export async function detail(req: Request, res: Response): Promise<void> {
  ok(res, await routeService.get(Number(req.params.id)));
}

export async function create(req: Request, res: Response): Promise<void> {
  ok(res, await routeService.create(req.body), 201);
}

export async function update(req: Request, res: Response): Promise<void> {
  ok(res, await routeService.update(Number(req.params.id), req.body));
}

export async function remove(req: Request, res: Response): Promise<void> {
  await routeService.remove(Number(req.params.id));
  ok(res, { status: 'deleted' });
}
