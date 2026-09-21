import type { Request, Response } from 'express';
import { menuService } from '../services/MenuService';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await menuService.list());
}

/** Menu milik user yang login (sidebar dinamis). */
export async function mine(req: Request, res: Response): Promise<void> {
  const auth = req.auth;
  const isSuper = auth.type === 0 || auth.roles.some((r) => r === 'SUPER_ADMIN' || r === 'SUPERADMIN');
  ok(res, await menuService.listForRoles(auth.roles, isSuper));
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
