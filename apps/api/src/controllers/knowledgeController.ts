import type { Request, Response } from 'express';
import { env } from '../config/env';
import { logger } from '../config/logger';
import { HttpError } from '../utils/problemDetails';
import { ok } from '../utils/response';

const AI_BASE_URL = env.AI_URL;

async function proxy(path: string, method: string, body?: unknown): Promise<object> {
  const res = await fetch(`${AI_BASE_URL}/ai${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Token': env.AI_INTERNAL_TOKEN,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(60_000),
  });
  const json = (await res.json().catch(() => null)) as { data?: object; detail?: string } | null;
  if (!res.ok) {
    logger.warn({ status: res.status, path }, 'knowledge proxy error');
    throw new HttpError(res.status, json?.detail ?? 'Brain engine gagal');
  }
  return (json?.data ?? {}) as object;
}

export async function list(_req: Request, res: Response): Promise<void> {
  ok(res, await proxy('/knowledge', 'GET'));
}

export async function get(req: Request, res: Response): Promise<void> {
  ok(res, await proxy(`/knowledge/${encodeURIComponent(String(req.params.name))}`, 'GET'));
}

export async function save(req: Request, res: Response): Promise<void> {
  ok(
    res,
    await proxy(`/knowledge/${encodeURIComponent(String(req.params.name))}`, 'PUT', {
      content: req.body?.content ?? '',
    }),
  );
}

export async function remove(req: Request, res: Response): Promise<void> {
  ok(res, await proxy(`/knowledge/${encodeURIComponent(String(req.params.name))}`, 'DELETE'));
}

export async function reingest(_req: Request, res: Response): Promise<void> {
  ok(res, await proxy('/rag/reingest', 'POST'));
}
