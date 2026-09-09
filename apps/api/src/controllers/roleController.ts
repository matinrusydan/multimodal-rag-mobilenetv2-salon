import type { Request, Response } from 'express';
import { roleService } from '../services/RoleService';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await roleService.list());
}

export async function detail(req: Request, res: Response): Promise<void> {
  ok(res, await roleService.get(Number(req.params.id)));
}

export async function create(req: Request, res: Response): Promise<void> {
  ok(res, await roleService.create(req.body), 201);
}

export async function update(req: Request, res: Response): Promise<void> {
  ok(res, await roleService.update(Number(req.params.id), req.body));
}

export async function remove(req: Request, res: Response): Promise<void> {
  await roleService.remove(Number(req.params.id));
  ok(res, { status: 'deleted' });
}

export async function assignPermissions(req: Request, res: Response): Promise<void> {
  ok(res, await roleService.assignPermissions(Number(req.params.id), req.body.permissionIds));
}
