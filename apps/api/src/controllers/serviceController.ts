import type { Request, Response } from 'express';
import { serviceService } from '../services/ServiceService';
import { pagedOrArray } from '../utils/pagination';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await serviceService.list());
}

export async function detail(req: Request, res: Response): Promise<void> {
  const { slug } = req.params;
  ok(res, await serviceService.detail(String(slug)));
}

export async function summary(_req: Request, res: Response): Promise<void> {
  ok(res, await serviceService.summary());
}

export async function listAdmin(req: Request, res: Response): Promise<void> {
  const all = await serviceService.listAdmin();
  ok(res, pagedOrArray(req, all));
}

export async function create(req: Request, res: Response): Promise<void> {
  ok(res, await serviceService.create(req.body), 201);
}

export async function update(req: Request, res: Response): Promise<void> {
  ok(res, await serviceService.update(Number(req.params.id), req.body));
}

export async function remove(req: Request, res: Response): Promise<void> {
  await serviceService.remove(Number(req.params.id));
  ok(res, { status: 'deleted' });
}

