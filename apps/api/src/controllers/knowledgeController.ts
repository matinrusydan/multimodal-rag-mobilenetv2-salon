import type { Request, Response } from 'express';
import { env } from '../config/env';
import { requestAi } from '../services/aiProxy';
import { ok } from '../utils/response';

async function proxy(path: string, method: string, body?: unknown): Promise<object> {
  return requestAi(
    path,
    {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Token': env.AI_INTERNAL_TOKEN,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    },
    60_000,
  );
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

export async function crawl(req: Request, res: Response): Promise<void> {
  ok(
    res,
    await proxy('/crawl', 'POST', {
      targets: Array.isArray(req.body?.targets) ? req.body.targets : [],
      reingest: req.body?.reingest !== false,
    }),
  );
}
