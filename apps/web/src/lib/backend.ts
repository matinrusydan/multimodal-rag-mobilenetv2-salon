import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:4000';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function problem(status: number, title: string, detail?: string) {
  return new ApiError(status, title, detail);
}

type BackendInit = RequestInit & { token?: string; timeoutMs?: number };

function normalizeTimeout(error: unknown): unknown {
  if (
    error &&
    typeof error === 'object' &&
    'name' in error &&
    (error.name === 'AbortError' || error.name === 'TimeoutError')
  ) {
    return problem(504, 'Waktu tunggu habis', 'Layanan terlalu lama merespons. Silakan coba lagi.');
  }
  return error;
}

export async function backendRequest<T>(path: string, init: BackendInit = {}): Promise<T> {
  const { token, timeoutMs, ...requestInit } = init;
  const timeoutSignal = timeoutMs === undefined ? undefined : AbortSignal.timeout(timeoutMs);
  const signal =
    timeoutSignal && requestInit.signal
      ? AbortSignal.any([requestInit.signal, timeoutSignal])
      : (timeoutSignal ?? requestInit.signal);
  const headers: Record<string, string> = {
    ...(requestInit.headers as Record<string, string> | undefined),
    accept: 'application/json',
  };
  if (requestInit.body !== undefined && requestInit.body !== null) {
    headers['content-type'] = 'application/json';
  }
  if (token) {
    headers.authorization = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api${path}`, {
      ...requestInit,
      signal,
      headers,
      cache: 'no-store',
    });

    const body = (await res.json().catch((error: unknown) => {
      const normalized = normalizeTimeout(error);
      if (normalized instanceof ApiError) throw normalized;
      return null;
    })) as {
      ok: boolean;
      data?: T;
      title?: string;
      detail?: string;
    } | null;

    if (!res.ok) {
      throw new ApiError(res.status, body?.title ?? 'Terjadi kesalahan', body?.detail);
    }

    return body?.data as T;
  } catch (error) {
    throw normalizeTimeout(error);
  }
}

export function routeError(error: unknown) {
  error = normalizeTimeout(error);
  if (error instanceof ApiError) {
    return NextResponse.json(
      {
        type: `about:blank#${error.status}`,
        title: error.message,
        status: error.status,
        detail: error.detail,
      },
      { status: error.status, headers: { 'content-type': 'application/problem+json' } },
    );
  }
  return NextResponse.json(
    {
      type: 'about:blank#500',
      title: 'Kesalahan server',
      status: 500,
      detail: 'Terjadi kesalahan internal',
    },
    { status: 500, headers: { 'content-type': 'application/problem+json' } },
  );
}

export function routeOk(data: unknown, status = 200) {
  return NextResponse.json({ ok: true, data }, { status });
}
