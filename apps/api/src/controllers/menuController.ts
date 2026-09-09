import type { Request, Response } from 'express';
import { menuService } from '../services/MenuService';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await menuService.list());
}

export async function detail(req: Request, res: Response): Promise<void> {
  ok(res, await menuService.get(Number(req.params.id)));
}

export async function create(req: Request, res: Response): Promise<void> {
  ok(res, await menuService.create(req.body), 201);
}

export async function update(req: Request, res: Response): Promise<void> {
  ok(res, await menuService.update(Number(req.params.id), req.body));
}

export async function remove(req: Request, res: Response): Promise<void> {
  await menuService.remove(Number(req.params.id));
  ok(res, { status: 'deleted' });
}

export async function assignRoles(req: Request, res: Response): Promise<void> {
  ok(res, await menuService.assignRoles(Number(req.params.id), req.body.roleIds));
}
