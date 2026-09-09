import type { Request, Response } from 'express';
import { serviceService } from '../services/ServiceService';
import { ok } from '../utils/response';

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await serviceService.list());
}

export async function detail(req: Request, res: Response): Promise<void> {
  const { slug } = req.params;
  ok(res, await serviceService.detail(String(slug)));
}
