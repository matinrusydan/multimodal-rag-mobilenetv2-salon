import type { Request, Response } from 'express';
import { routeService } from '../services/RouteService';
import { pagedOrArray } from '../utils/pagination';
import { ok } from '../utils/response';

export async function list(req: Request, res: Response): Promise<void> {
  const all = await routeService.list();
  ok(res, pagedOrArray(req, all));
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

export async function assignRoles(req: Request, res: Response): Promise<void> {
  ok(res, await routeService.assignRoles(Number(req.params.id), req.body.roleIds));
}

