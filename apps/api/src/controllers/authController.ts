import type { Request, Response } from 'express';
import { authService } from '../services/AuthService';
import { ok } from '../utils/response';

export async function register(req: Request, res: Response): Promise<void> {
  const result = await authService.register(req.body);
  ok(res, result, 201);
}

export async function login(req: Request, res: Response): Promise<void> {
  const result = await authService.login(req.body);
  ok(res, result);
}

export async function logout(_req: Request, res: Response): Promise<void> {
  ok(res, authService.logout());
}

export async function session(req: Request, res: Response): Promise<void> {
  const user = await authService.session(req.auth.userId);
  ok(res, user);
}
