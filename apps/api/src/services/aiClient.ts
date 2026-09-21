/**
 * AiClient — proxy service to forward /api/analyze and /api/chat to
 * FastAPI brain engine (apps/ai, port 5000).
 *
 * Rate-limit and validation stay in Express; this module just forwards
 * valid requests and surfaces errors as HTTPError / Problem Details.
 */

import { env } from '../config/env';
import { logger } from '../config/logger';
import { HttpError } from '../utils/problemDetails';

const AI_BASE_URL = env.AI_URL;

/** Forward multipart image to FastAPI /ai/analyze. */
export async function aiAnalyze(buffer: Buffer, mimetype: string): Promise<object> {
  const form = new FormData();
  form.append('image', new Blob([buffer], { type: mimetype }), 'hair.jpg');

  const t0 = Date.now();
  const res = await fetch(`${AI_BASE_URL}/ai/analyze`, {
    method: 'POST',
    body: form,
    signal: AbortSignal.timeout(15_000),
  });

  const elapsed = Date.now() - t0;

  if (!res.ok) {
    const body = await res.text().catch(() => '(no body)');
    logger.warn({ status: res.status, body, elapsed }, 'aiAnalyze: FastAPI error');
    throw new HttpError(res.status, `Brain engine gagal: ${body.slice(0, 300)}`);
  }

  const json = (await res.json()) as { data?: object };
  if (!json.data) {
    throw new HttpError(502, 'Brain engine mengembalikan respons tanpa data');
  }
  return json.data;
}

/** Forward chat JSON to FastAPI /ai/chat. */
export async function aiChat(body: Record<string, unknown>): Promise<object> {
  const t0 = Date.now();
  const res = await fetch(`${AI_BASE_URL}/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });

  const elapsed = Date.now() - t0;

  if (!res.ok) {
    const text = await res.text().catch(() => '(no body)');
    logger.warn({ status: res.status, body: text, elapsed }, 'aiChat: FastAPI error');
    throw new HttpError(res.status, `Brain engine gagal: ${text.slice(0, 300)}`);
  }

  const json = (await res.json()) as { data?: object };
  if (!json.data) {
    throw new HttpError(502, 'Brain engine mengembalikan respons tanpa data');
  }
  return json.data;
}

/**
 * Forward admin-agent chat to FastAPI /ai/agent.
 * Menyertakan token internal agar FastAPI boleh memanggil API Express (tool-call data live).
 */
export async function aiAgent(
  body: Record<string, unknown>,
  auth: { userId: number; name: string; permissions: string[]; type: number },
): Promise<object> {
  const t0 = Date.now();
  const res = await fetch(`${AI_BASE_URL}/ai/agent`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Token': env.AI_INTERNAL_TOKEN,
    },
    body: JSON.stringify({
      ...body,
      // Konteks RBAC diteruskan agar tool-call menghormati hak akses.
      auth: { userId: auth.userId, name: auth.name, permissions: auth.permissions, type: auth.type },
    }),
    signal: AbortSignal.timeout(60_000),
  });

  const elapsed = Date.now() - t0;

  if (!res.ok) {
    const text = await res.text().catch(() => '(no body)');
    logger.warn({ status: res.status, body: text, elapsed }, 'aiAgent: FastAPI error');
    throw new HttpError(res.status, `Brain engine gagal: ${text.slice(0, 300)}`);
  }

  const json = (await res.json()) as { data?: object };
  if (!json.data) {
    throw new HttpError(502, 'Brain engine mengembalikan respons tanpa data');
  }
  return json.data;
}
