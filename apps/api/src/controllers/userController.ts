import type { Request, Response } from 'express';
import { userService } from '../services/UserService';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await userService.list());
}

export async function detail(req: Request, res: Response): Promise<void> {
  ok(res, await userService.get(Number(req.params.id)));
}

export async function create(req: Request, res: Response): Promise<void> {
  ok(res, await userService.create(req.body), 201);
}

export async function update(req: Request, res: Response): Promise<void> {
  ok(res, await userService.update(Number(req.params.id), req.body));
}

export async function remove(req: Request, res: Response): Promise<void> {
  await userService.remove(Number(req.params.id));
  ok(res, { status: 'deleted' });
}

export async function assignRoles(req: Request, res: Response): Promise<void> {
  ok(res, await userService.assignRoles(Number(req.params.id), req.body.roleIds));
}
