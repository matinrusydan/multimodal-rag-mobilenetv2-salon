import type { Request, Response } from 'express';
import { permissionService } from '../services/PermissionService';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await permissionService.list());
}

export async function detail(req: Request, res: Response): Promise<void> {
  ok(res, await permissionService.get(Number(req.params.id)));
}

export async function create(req: Request, res: Response): Promise<void> {
  ok(res, await permissionService.create(req.body), 201);
}

export async function update(req: Request, res: Response): Promise<void> {
  ok(res, await permissionService.update(Number(req.params.id), req.body));
}

export async function remove(req: Request, res: Response): Promise<void> {
  await permissionService.remove(Number(req.params.id));
  ok(res, { status: 'deleted' });
}
